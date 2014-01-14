#! /usr/bin/env python
# -*- coding: utf-8 -*-

import os
import shutil
import getpass
from tempfile import mkstemp
from subprocess import check_call, CalledProcessError

# input/output parameters
input_file_path = "./iphpr.csv"
csv_splitter = ";"
hostname_col = 5
status_col = 12
call_timeout = 5

# mounting parameters
mnt_point = "./mnt/"
remote_share = "C$/"

# local_dir holds the files to copy
# remote_base must exist remotely
# remote_dir would be created remotely and then the files will be copied there
local_dir_A = "./Nombre Equipo/"
remote_base_A = "Archivos de programa/"
remote_dir_A = remote_base_A + "Nombre Equipo/"

local_dir_B = "./Escritorio/"
remote_base_B = "Documents and Settings/All Users/"
remote_dir_B = remote_base_B + "Escritorio/"

# other parameters
overwrite_files = True


class SimpleError(Exception):

    def __init__(self, message):
        self.message = message

    def __str__(self):
        return repr(self.message)


# copy from local to remote
def local_to_remote(local_dir, remote_dir, remote_base, overwrite_files):

    # remote_base must exist
    if not os.path.isdir(mnt_point + remote_base):
        raise SimpleError("NOT FOUND: " + remote_base)

    # create remote directory if not exist
    try:
        os.makedirs(mnt_point + remote_dir)
    except OSError:
        pass
    except:
        raise SimpleError("ERROR CREATING: " + remote_dir)

    # copy files if not exist
    try:
        for f in os.listdir(local_dir):  # for each local file
            if os.path.isfile(mnt_point + remote_dir + f) and not overwrite_files:
                continue
            else:  # otherwise copy it!
                shutil.copyfile(local_dir + f, mnt_point + remote_dir + f)
    except:
        raise SimpleError("ERROR COPYING: " + local_dir)


# mount and copy calling local_to_remote
def samba_copy(hostname):

    with open(os.devnull, "w") as dev_null:  # discard the output
        try:
            # unmount the remote share
            check_call(["timeout", str(call_timeout), "umount", mnt_point],
                       stdout=dev_null, stderr=dev_null)
        except:
            pass
        try:
            # mount the remote share
            check_call(["timeout", str(call_timeout), "mount", "-t", "cifs",
                        "//" + hostname + "/" + remote_share,
                        mnt_point, "-o",
                        "user=" + user + ",password=" + passwd + ",ntlm=sec"],
                       stdout=dev_null, stderr=dev_null)
        except CalledProcessError:
            message = "MOUNT FAIL: " + "//" + hostname + "/" + remote_share
            raise SimpleError(message)
        except:
            message = "MOUNT FAIL: " + "//" + hostname + "/" + remote_share
            raise SimpleError(message)

    # copy!
    local_to_remote(local_dir_A, remote_dir_A, remote_base_A, overwrite_files)
    local_to_remote(local_dir_B, remote_dir_B, remote_base_B, overwrite_files)

    check_call(["sleep", "2"])  # wait before unmount to avoid busy state error


# open and process the input, call samba_copy and update status
def main_process(user, passwd):

    # open input
    try:
        input_file = open(input_file_path, "r")
    except IOError:
        print "No se pudo abrir el archivo:", input_file_path
        return

    # make temps
    fh, abs_path = mkstemp()
    new_file = open(abs_path, 'w')

    # processing the input
    header = input_file.readline()
    new_file.write(header)

    for line in input_file:
        line = line.rstrip('\r\n')
        words = line.split(csv_splitter)
        for _ in range(status_col + 1)[len(words):]:  # append columns
            words.append("")

        # based on the status call samba_copy
        hostname = words[hostname_col]
        status = words[status_col]
        if status == "OK":
            pass
        elif status not in ["OK"]:
            try:
                samba_copy(hostname)
                new_status = "OK"
            except SimpleError as e:
                new_status = e.message
            words[status_col] = new_status  # update status
        print hostname + ": " + words[status_col]
        line = csv_splitter.join(words)
        line += '\r\n'
        new_file.write(line)

    # close and overwrite files
    new_file.close()
    os.close(fh)
    input_file.close()
    os.remove(input_file_path)
    shutil.move(abs_path, input_file_path)

    # final umount to left things clean
    with open(os.devnull, "w") as dev_null:  # discard the output
        try:
            # unmount the remote share
            check_call(["timeout", str(call_timeout), "umount", mnt_point],
                       stdout=dev_null, stderr=dev_null)
        except:
            pass

    return


# the main program - get user and passwd from stdin
user = raw_input("Username: ")
passwd = getpass.getpass()
if user and passwd:
    main_process(user, passwd)
else:
    print "Debe ingresar un nombre de usuario y contraseña."
