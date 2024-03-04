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
read -p "Select version of ROKIT Locator to operate on (default 1.8|1.6): " locator_version
# If locator_version is unset or empty, the statement assigns it the value 1.8.
locator_version=${locator_version:-1.8}
if [[ ${locator_version} =~ \D*1\.8(\.\d+)? ]]; then
    locator_version=1.8
elif [[ ${locator_version} =~ \D*1\.6(\.\d+)? ]]; then
    locator_version=1.6
else
    echo "Warn: not valid/supported version"
    exit 1
fi
echo "ROKIT Locator ${locator_version}"

dir_prefix=""
update_global_variables() {
    dir_recordings="/var/lib/docker/volumes/BoschRexrothLocalizationClientWorkdir/_data/${locator_version}/client/slam/recordings"
    dir_sketches="/var/lib/docker/volumes/BoschRexrothLocalizationClientWorkdir/_data/${locator_version}/client/slam/maps"
    dir_client_loc_maps="/var/lib/docker/volumes/BoschRexrothLocalizationClientWorkdir/_data/${locator_version}/client/loc/maps"
    dir_server_maps="/var/lib/docker/volumes/BoschRexrothLocalizationServerWorkdir/_data/${locator_version}/server/mus/maps"
    dir_backup="/home/${original_user}/rokit/backup"
}
update_global_variables
dir_client_recovery="/var/lib/docker/volumes/BoschRexrothLocalizationClientRecoveryDir/_data"
dir_server_recovery="/var/lib/docker/volumes/BoschRexrothLocalizationServerRecoveryDir/_data"
mkdir -p $dir_backup
chown ${original_user}:${original_user} $dir_backup
backup_maps() {
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

restore_maps() {
    :
    # 恢复备份文件的时候，修改文件权限和所有者
    # sudo chmod 644 *
    # sudo chown 9421:9421 *
}

copy_server_map() {
    # copy_server_map src_locator_version dst_locator_version map_name_without_extension
    # dir_server_maps="${dir_server_maps/1.8/1.6}"

    # dir_server_maps=$(echo "$dir_server_maps" | sed "s/\d+\.\d+/$1/")
    # dir_src_server_map=${dir_server_maps}/$3.spm
    # echo $dir_src_server_map
    # dir_server_maps=$(echo "$dir_server_maps" | sed "s/\d+\.\d+/$2/")
    # dir_dst_server_map=${dir_server_maps}/$3.spm
    # echo $dir_dst_server_map

    dir_src_server_map="/var/lib/docker/volumes/BoschRexrothLocalizationServerWorkdir/_data/$1/server/mus/maps"
    dir_dst_server_map="/var/lib/docker/volumes/BoschRexrothLocalizationServerWorkdir/_data/$2/server/mus/maps"

    if [ ! -d "$dir_dst_server_map" ]; then
        mkdir -p "$dir_dst_server_map"
    fi
    # rsync -anv $dir_src_server_map/$3.spm $dir_dst_server_map
    cp -p $dir_src_server_map/$3.spm $dir_dst_server_map
    # chown 9421:9421 ${dir_dst_server_map}/$3.spm
    # chmod 644 ${dir_dst_server_map}/$3.spm

    echo "Restart docker container BoschRexrothLocalizationServer to make it recognize the new map."
    read -p "Restart it now? (default Yes | No): " choice
    choice=${choice:-Yes}
    if [[ ${choice} =~ [yY] ]]; then
        docker restart BoschRexrothLocalizationServer
    else
        echo "Run this statement later by yourself."
        echo "$ docker restart BoschRexrothLocalizationServer"
    fi
}

list_dir() {
    echo
    echo $1
    echo -e "Permissions\tLinks\tOwner\tGroup\tSize\tDate\tFilename"
    ls -lh $1
}

export_recovery() {
    if [[ $1 == *server* ]]; then
        cp ${dir_server_recovery}/$1 ${dir_backup}
    elif [[ $1 == *client* ]]; then
        cp ${dir_client_recovery}/$1 ${dir_backup}
    else
        echo "Warn: wrong file name"
        # TODO not exist
    fi
    chown ${original_user}:${original_user} $dir_backup/$1
}

import_recovery() {
    if [[ $1 == *server* ]]; then
        cp ${dir_backup}/$1 ${dir_server_recovery}
        chown 9421:9421 ${dir_server_recovery}/$1
        chmod 644 ${dir_server_recovery}/$1
    elif [[ $1 == *client* ]]; then
        cp ${dir_backup}/$1 ${dir_client_recovery}
        chown 9421:9421 ${dir_client_recovery}/$1
        chmod 644 ${dir_client_recovery}/$1
    else
        echo "Warn: wrong file name"
        # TODO not exist
    fi
}

if ! which tree >&/dev/null; then
    apt install tree -y
fi

# ANSI escape codes for colors
RED='\033[0;31m'
COLOR="\033[43;42m"
GREEN_B="\e[42m" # https://gist.github.com/Prakasaka/219fe5695beeb4d6311583e79933a009
YELLOW_F='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

start_menu() {
    # clear
    echo
    printf "${COLOR}====================================${NC}\n"
    printf "${COLOR}%-36s${NC}\n" $0
    printf "${COLOR}%-36s${NC}\n" "ROKIT Locator ${locator_version}"
    # printf "${COLOR}%-10s%-26s${NC}\n" "Script" $0
    # printf "${COLOR}%-10s%-26s${NC}\n" "Author" "TAN Hongkui"
    printf "${GREEN_B}====================================${NC}\n"
    echo
    printf "${YELLOW_F} 0. change locator version ${NC}\n"
    printf "${YELLOW_F} 1. list recordings${NC}\n"
    printf "${YELLOW_F} 2. list sketches${NC}\n"
    printf "${YELLOW_F} 3. list client localization maps${NC}\n"
    printf "${YELLOW_F} 4. list server maps${NC}\n"
    printf "${YELLOW_F} 5. export all recordings, sketches and maps${NC}\n"
    printf "${YELLOW_F} 6. import ... (not working) ${NC}\n"
    printf "${YELLOW_F} 7. tree dir backup${NC}\n"
    printf "${YELLOW_F} 8. copy a server map from 1.6 to 1.8${NC}\n"
    printf "${YELLOW_F} 9. copy a server map from 1.8 to 1.6 ${NC}\n"
    echo
    printf "${YELLOW_F} 21. list client recovery points${NC}\n"
    printf "${YELLOW_F} 22. list server recovery points${NC}\n"
    printf "${YELLOW_F} 23. export a recovery point${NC}\n"
    printf "${YELLOW_F} 24. import a recovery point${NC}\n"
    echo
    printf "${RED} 99. ctrl+c to exit ${NC}\n"
    echo

    read -p "Enter number: " num
    case "$num" in
    99)
        exit 1
        ;;
    0)
        read -p "Change Locator version to (1.6 or 1.8): " locator_version
        echo "ROKIT Locator ${locator_version}"
        update_global_variables
        ;;
    1)
        list_dir $dir_recordings
        ;;
    2)
        list_dir $dir_sketches
        ;;
    3)
        list_dir $dir_client_loc_maps
        ;;
    4)
        list_dir $dir_server_maps
        ;;
    5)
        backup_maps
        ;;
    6)
        restore_maps
        ;;
    7)
        tree -h $dir_backup
        ;;
    8)
        read -p "Enter file name without extension (.spm) of server map: " server_map
        # If locator_version is unset or empty, the statement assigns it the value 1.8.
        server_map=${server_map:-map}
        copy_server_map 1.6 1.8 $server_map
        ;;
    9)
        read -p "Enter file name without extension (.spm) of server map: " server_map
        # If locator_version is unset or empty, the statement assigns it the value 1.8.
        server_map=${server_map:-map}
        copy_server_map 1.8 1.6 $server_map
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
    if [ $? -ne 0 ]; then
        break
    fi
done
