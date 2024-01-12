#!/bin/bash
# -*- coding: utf-8 -*-
#
# Created On: 2024-01-05
# SPDX-FileCopyrightText: Copyright (c) 2024 Shanghai Bosch Rexroth Hydraulics & Automation Ltd.
# SPDX-License-Identifier: MIT
#

# sudo bash script.sh
# Get the username of the original user who ran the sudo command
original_user=${SUDO_USER}

if [ -z ${original_user} ]; then
    # If not run with sudo or no SUDO_USER is set, fallback to current USER
    original_user="$USER"
    echo "Warn: This script should be run with sudo."
    echo "  sudo bash $0"
    exit 1
fi

echo "Original user: $original_user"

# Enter version of Locator which does not include the minor version number
read -p "Select version of ROKIT Locator (default 1.8|1.6): " locator_version
locator_version=${locator_version:-1.8}
if [[ ${locator_version} =~ ^\s*1\.8(\.\d*)?\s*$ ]] # TODO cannot recognise 1.8.3
then
    locator_version=1.8
elif [[ ${locator_version} =~ ^\s*1\.6(\.\d*)?\s*$ ]]
then
    locator_version=1.6
else
    echo "Warn: not valid/supported version"
    exit 1
fi
echo "ROKIT Locator ${locator_version}"

dir_prefix=""
dir_recordings="/var/lib/docker/volumes/BoschRexrothLocalizationClientWorkdir/_data/${locator_version}/client/slam/recordings"
dir_sketches="/var/lib/docker/volumes/BoschRexrothLocalizationClientWorkdir/_data/${locator_version}/client/slam/maps"
dir_client_loc_maps="/var/lib/docker/volumes/BoschRexrothLocalizationClientWorkdir/_data/${locator_version}/client/loc/maps"
dir_server_maps="/var/lib/docker/volumes/BoschRexrothLocalizationServerWorkdir/_data/${locator_version}/server/mus/maps"
dir_client_recovery="/var/lib/docker/volumes/BoschRexrothLocalizationClientRecoveryDir/_data"
dir_server_recovery="/var/lib/docker/volumes/BoschRexrothLocalizationServerRecoveryDir/_data"
dir_backup="/home/${original_user}/rokit/backup"
mkdir -p $dir_backup
chown ${original_user}:${original_user} $dir_backup
backup_maps(){
    # backup locator
    pushd $dir_backup
    # recordings 激光记录
    rsync -av --relative ${dir_recordings} $dir_backup
    # sketches 草图
    rsync -av --relative ${dir_sketches} $dir_backup
    # client localization maps 客户端定位用地图
    rsync -av --relative $dir_client_loc_maps $dir_backup
    # server maps and updates 服务器地图和更新
    rsync -av --relative $dir_server_maps $dir_backup
    popd
    chown $original_user:$original_user $dir_backup -R
    
}

restore_maps(){
    :
    # 恢复备份文件的时候，修改文件权限和所有者
    # sudo chmod 644 *
    # sudo chown 9421:9421 *
}

list_dir(){
    echo
    echo $1
    ls -lh $1
}

export_recovery(){
    if [[ $1 == *server* ]]
    then
        cp ${dir_server_recovery}/$1 ${dir_backup}
    elif [[ $1 == *client* ]]
    then
        cp ${dir_client_recovery}/$1 ${dir_backup}
    else
        echo "Warn: wrong file name"
        # TODO not exist
    fi
    chown ${original_user}:${original_user} $dir_backup/$1
}

import_recovery(){
    if [[ $1 == *server* ]]
    then
        cp ${dir_backup}/$1 ${dir_server_recovery}
        chown 9421:9421 ${dir_server_recovery}/$1
        chmod 644 ${dir_server_recovery}/$1
    elif [[ $1 == *client* ]]
    then
        cp ${dir_backup}/$1 ${dir_client_recovery}
        chown 9421:9421 ${dir_client_recovery}/$1
        chmod 644 ${dir_client_recovery}/$1
    else
        echo "Warn: wrong file name"
        # TODO not exist
    fi
}

if ! which tree >& /dev/null
then
    apt install tree -y
fi

# ANSI escape codes for colors
RED='\033[0;31m'
COLOR="\033[43;42m"
GREEN_B="\e[42m" # https://gist.github.com/Prakasaka/219fe5695beeb4d6311583e79933a009
YELLOW_F='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

start_menu(){
    # clear
    echo
    printf "${COLOR}====================================${NC}\n"
    printf "${COLOR}%-36s${NC}\n" $0
    printf "${COLOR}%-36s${NC}\n" "ROKIT Locator ${locator_version}"
    # printf "${COLOR}%-10s%-26s${NC}\n" "Script" $0
    # printf "${COLOR}%-10s%-26s${NC}\n" "Author" "TAN Hongkui"
    printf "${GREEN_B}====================================${NC}\n"
    echo
    printf "${YELLOW_F} 3. list recordings${NC}\n"
    printf "${YELLOW_F} 4. list sketches${NC}\n"
    printf "${YELLOW_F} 5. list client localization maps${NC}\n"
    printf "${YELLOW_F} 6. list server maps${NC}\n"
    printf "${YELLOW_F} 1. export all recordings, sketches and maps${NC}\n"
    printf "${YELLOW_F} 2. import ...${NC}\n"
    printf "${YELLOW_F} 7. tree dir backup${NC}\n"
    echo
    printf "${YELLOW_F} 21. list client recovery points${NC}\n"
    printf "${YELLOW_F} 22. list server recovery points${NC}\n"
    printf "${YELLOW_F} 23. export a recovery point${NC}\n"
    printf "${YELLOW_F} 24. import a recovery point${NC}\n"
    printf " 0. ctrl+c to exit\n"
    echo
    
    read -p "enter number: " num
    case "$num" in
        0)
            exit 1
        ;;
        3)
            list_dir $dir_recordings
        ;;
        4)
            list_dir $dir_sketches
        ;;
        5)
            list_dir $dir_client_loc_maps
        ;;
        6)
            list_dir $dir_server_maps
        ;;
        1)
            backup_maps
        ;;
        2)
            restore_maps
        ;;
        7)
            tree -h $dir_backup
        ;;
        21)
            list_dir $dir_client_recovery
        ;;
        22)
            list_dir $dir_server_recovery
        ;;
        23)
            read -p "Enter file name: " file_name
            export_recovery ${file_name}
        ;;
        24)
            list_dir ${dir_backup}
            read -p "Enter file name: " file_name
            import_recovery ${file_name}
        ;;
        *)
            # clear
            echo -e "Please enter correct numbers"
            sleep 2s
            start_menu
        ;;
    esac
}

while true; do
    start_menu
    sleep 2s
    if [ $? -ne 0 ]
    then
        break
    fi
done