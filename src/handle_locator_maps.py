#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created On: 2024-01-10
# SPDX-FileCopyrightText: Copyright (c) 2024 Shanghai Bosch Rexroth Hydraulics & Automation Ltd.
# SPDX-License-Identifier: MIT
#

import os
import re
import subprocess
from prompt_toolkit import PromptSession
from prompt_toolkit.completion.filesystem import ExecutableCompleter, PathCompleter
from rokit.talk_to_rokit_locator import *

completer = PathCompleter()
session = PromptSession()


def get_original_user():
    original_user = os.environ.get("SUDO_USER")

    if not original_user:
        print("Warn: This script should be run with sudo.")
        print(f"  sudo python {os.path.basename(__file__)}")
        exit(1)

    return original_user


def validate_locator_version(locator_version):
    # Match version patterns like "1.8", "1.6", or "1.8.3"
    pattern = r"^\s*1\.(8|6)(\.\d*)?\s*$"
    if re.match(pattern, locator_version):
        return float(
            locator_version.split(".")[0] + "." + locator_version.split(".")[1]
        )
    else:
        print("Warn: Not a valid/supported version.")
        exit(1)


def backup_maps(original_user):
    os.makedirs(dir_backup, exist_ok=True)

    for directory in [
        dir_recordings,
        dir_sketches,
        dir_client_loc_maps,
        dir_server_maps,
    ]:
        subprocess.run(["rsync", "-av", "--relative", directory, dir_backup])

    subprocess.run(["chown", f"{original_user}:{original_user}", dir_backup, "-R"])


# def copy_dir(dir_sr, dir_dst):
#     os.makedirs(dir_dst, exist_ok=True)

#     print("\n" + dir_backup)
#     subprocess.run(["ls", "-lh", dir_backup])


def restore_maps():
    pass  # Implement the restore functionality here


def list_dir(directory):
    print("\n" + directory)
    subprocess.run(["ls", "-lh", directory])


def install_tree():
    subprocess.run(["apt", "install", "-y", "tree"], check=True)


def start_menu(original_user, locator_version):
    RED = "\033[0;31m"
    COLOR = "\033[43;42m"
    GREEN_B = "\033[42m"
    YELLOW_F = "\033[0;33m"
    BLUE = "\033[0;34m"
    NC = "\033[0m"

    def clear_screen():
        subprocess.run("clear" if os.name != "nt" else "cls")

    # clear_screen()
    print(f"{COLOR}===================================={NC}")
    print(f"{COLOR}{os.path.basename(__file__):<36}{NC}")
    print(f"{COLOR}{('ROKIT Locator '+str(locator_version)):<36}{NC}")
    # print(f"{os.path.basename(__file__)}")
    # print(f"ROKIT Locator {locator_version}")
    print(f"{GREEN_B}===================================={NC}\n")

    os.makedirs(dir_backup, exist_ok=True)
    while True:
        print(f"{YELLOW_F} 1. Backup maps{NC}")
        print(f"{YELLOW_F} 2. Restore maps{NC}")
        print(f"{YELLOW_F} 3. List recordings{NC}")
        print(f"{YELLOW_F} 4. List sketches{NC}")
        print(f"{YELLOW_F} 5. List client localization maps{NC}")
        print(f"{YELLOW_F} 6. List server maps{NC}")
        print(f"{YELLOW_F} 7. List maps backup{NC}")
        print("--------------------------------------")
        print(f"{YELLOW_F} 11. supportRecoveryList{NC}")
        print(f"{YELLOW_F} 12. supportRecoveryCreate{NC}")
        print(f"{YELLOW_F} 13. supportRecoveryDelete{NC}")
        print(f"{YELLOW_F} 14. supportRecoveryFactoryReset{NC}")
        print(f"{YELLOW_F} 15. supportRecoveryFrom{NC}")
        print(f"{YELLOW_F} 16. list all recovery points{NC}")
        print(f"{YELLOW_F} 17. export recovery point{NC}")
        print(f"{YELLOW_F} 18. import recovery point{NC}")
        # print(f"{YELLOW_F} 19. {NC}")
        print(" 0. Exit\n")

        num = session.prompt("Enter number: ", completer=completer)

        if num == "0":
            break
        elif num == "1":
            backup_maps(original_user, locator_version)
        elif num == "2":
            restore_maps()
        elif num == "3":
            list_dir(dir_recordings)
        elif num == "4":
            list_dir(dir_sketches)
        elif num == "5":
            list_dir(dir_client_loc_maps)
        elif num == "6":
            list_dir(dir_server_maps)
        elif num == "7":
            subprocess.run(["tree", "-h", dir_backup])
        elif num == "16":
            subprocess.run(["echo", dir_client_recovery])
            subprocess.run(["ls", "-lh", dir_client_recovery])
            subprocess.run(["echo", dir_server_recovery])
            subprocess.run(["ls", "-lh", dir_server_recovery])
        elif num == "17":
            # export recovery point
            recovery_point = session.prompt(
                "Enter name of recovery point: ", completer=completer
            )
            pattern_client_recovery = r".*client.*.tar.bz2"
            pattern_server_recovery = r".*server.*.tar.bz2"

            if re.match(pattern_client_recovery, recovery_point):
                subprocess.run(
                    [
                        "cp",
                        os.path.join(dir_client_recovery, recovery_point),
                        dir_backup,
                    ]
                )
            elif re.match(pattern_server_recovery, recovery_point):
                subprocess.run(
                    [
                        "cp",
                        os.path.join(dir_server_recovery, recovery_point),
                        dir_backup,
                    ]
                )
            else:
                print("Name of recovery point is not valid.")
                continue
            print(os.path.join(dir_backup, recovery_point))
        elif num == "18":
            # import recovery point
            subprocess.run(["tree", "-h", dir_backup])
        else:
            clear_screen()
            print("Please enter a correct number.")
            continue


# Main part of the script
original_user = get_original_user()
# original_user = os.environ.get("USER")
locator_version = session.prompt(
    "Select version of ROKIT Locator (default 1.8|1.6): ", completer=completer
)
locator_version = locator_version.strip() or "1.8"
locator_version = validate_locator_version(locator_version)

dir_prefix = ""
dir_recordings = f"/var/lib/docker/volumes/BoschRexrothLocalizationClientWorkdir/_data/{locator_version}/client/slam/recordings"
dir_sketches = f"/var/lib/docker/volumes/BoschRexrothLocalizationClientWorkdir/_data/{locator_version}/client/slam/maps"
dir_client_loc_maps = f"/var/lib/docker/volumes/BoschRexrothLocalizationClientWorkdir/_data/{locator_version}/client/loc/maps"
dir_server_maps = f"/var/lib/docker/volumes/BoschRexrothLocalizationServerWorkdir/_data/{locator_version}/server/mus/maps"
dir_backup = f"/home/{original_user}/rokit/backup"
dir_client_recovery = (
    "/var/lib/docker/volumes/BoschRexrothLocalizationClientRecoveryDir/_data"
)
dir_server_recovery = (
    "/var/lib/docker/volumes/BoschRexrothLocalizationServerRecoveryDir/_data"
)

if not os.access("/usr/bin/tree", os.X_OK):
    install_tree()

start_menu(original_user, locator_version)
