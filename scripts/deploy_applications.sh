#!/bin/bash
# -*- coding: utf-8 -*-
#
# Created On: 2024-01-02
# SPDX-FileCopyrightText: Copyright (c) 2024 Shanghai Bosch Rexroth Hydraulics & Automation Ltd.
# SPDX-License-Identifier: MIT
#

# sudo bash script.sh
# Get the username of the original user who ran the sudo command
original_user="$SUDO_USER"

if [ -z "$original_user" ]; then
    # If not run with sudo or no SUDO_USER is set, fallback to current USER
    original_user="$USER"
    echo "This script should be run with sudo."
    echo "  sudo bash $0"
    exit 1
fi

echo "Original user: $original_user"

apt update && apt upgrade -y # 更新软件源和已安装的软件
apt install libfuse-dev

# Define variables
GITEE_REPO_OWNER="thkfighter"
GITEE_REPO_NAME="locator_plc_bridge"
EXECUTABLE_VERSION="v1.0.4"
arch=$(uname -m)
codename=$(lsb_release -cs)
case $codename in
    "jammy") os="ubuntu22.04"
    ;;
    "focal") os="ubuntu20.04"
    ;;
    "bionic") os="ubuntu18.04"
    ;;
    *) echo "not built for this OS version"
    ;;
esac

if [ "$arch"="x86_64" ]
then
    arch="amd64"
elif [ "$arch"="aarch64" ]
then
    :
fi

url_prefix="https://gitee.com/${GITEE_REPO_OWNER}/${GITEE_REPO_NAME}/releases/download/${EXECUTABLE_VERSION}/"

# https://gitee.com/thkfighter/locator_plc_bridge/releases/download/v1.0.4/seed_s7_ubuntu22.04_amd64
# https://gitee.com/thkfighter/locator_plc_bridge/releases/download/v1.0.4/seed_s7_config.json

# TODO Check whether the files have been downloaded

# Create a directory to store the executable (if not exists)
EXEC_DIR="/home/${original_user}/rokit/service"
mkdir -p "${EXEC_DIR}"

install_target()
{
    # parameters: target with_name_suffix with_config
    target=$1
    if [ $2 -eq 1 ]
    then
        target_download="${target}_${os}_${arch}"
    else
        target_download=${target}
    fi
    # Download the executable
    url_target="${url_prefix}${target_download}"
    if [ -e ${EXEC_DIR}/${target} ]
    then
        echo "${EXEC_DIR}/${target} already exists."
    elif [-e ${EXEC_DIR}/${target_download} ]
    then
        echo "${EXEC_DIR}/${target_download} already exists; rename it."
        cp ${EXEC_DIR}/${target_download} ${EXEC_DIR}/${target}
    else
        echo "downloading ${target} to ${EXEC_DIR}..."
        wget -nv -O ${EXEC_DIR}/${target} ${url_target}
    fi
    chmod +x "${EXEC_DIR}/${target}"
    
    if [ $3 -eq 1 ]
    then
        target_config="${target}_config.json"
        if [ -e ${EXEC_DIR}/${target_config} ]
        then
            echo "${EXEC_DIR}/${target_config} already exists."
        else
            echo "downloading ${target_config} to ${EXEC_DIR}..."
            wget -nv -P ${EXEC_DIR} ${url_prefix}${target_config}
        fi
        # prompt to edit the configuration file
        # TODO disable this
        read -p "Edit the configuration file now? (yes|No): " choice
        choice=${choice:-No}
        if [[ ${choice} =~ [yY] ]]
        then
            nano ${EXEC_DIR}/${target_config}
        fi
    else
        target_config=""
    fi
    
    # Create the systemd service file
    SERVICE_FILE="/etc/systemd/system/${target}.service"
    if [[ ${target} =~ "seed" ]]
    then
        cat > ${SERVICE_FILE} <<EOF
[Unit]
Description=set seed to initialize pose of ROKIT Locator client
After=network.target

[Service]
ExecStartPre=/bin/sleep 3
ExecStart=/home/${original_user}/rokit/service/${target} --config /home/${original_user}/rokit/service/${target_config}
Restart=always

[Install]
WantedBy=multi-user.target
EOF
    elif [[ ${target} =~ "relay" ]]
    then
        cat > ${SERVICE_FILE} <<EOF
[Unit]
Description=works as a relay to retransmit poses at a specific frequency
After=network.target

[Service]
ExecStartPre=/bin/sleep 3
ExecStart=/usr/bin/python3 /home/${original_user}/rokit/service/${target} --frq_divisor 3 --src_host 127.0.0.1 --src_port 9011 --dst_port 9511
Restart=always

[Install]
WantedBy=multi-user.target
EOF
    elif [[ ${target} =~ "716mini" ]]
    then
        # TODO dual lidars
        # TODO https://gitee.com/thkfighter/simple_vanjee_716mini/releases/download/v1.2/simple_vanjee_716mini_ubuntu22.04_gcc11.3.0_x86_64.AppImage
        cat > ${SERVICE_FILE} <<EOF
[Unit]
Description=Driver of LiDAR Vanjee 716mini for Rexroth ROKIT Locator
After=network.target

[Service]
ExecStartPre=/bin/sleep 3
ExecStart=/home/${original_user}/rokit/service/${target} -f 192.168.0.5 -F 2110 -T 4245
Restart=always

[Install]
WantedBy=multi-user.target
EOF
    fi
    
    echo "======${SERVICE_FILE}"
    cat "${SERVICE_FILE}"
    echo "======"
    
    # Reload systemd daemon to recognize new service file
    systemctl daemon-reload
    
    # Enable the service to start at boot
    systemctl enable "${target}.service"
    
    # Start the service
    systemctl start "${target}.service"
    
    echo "Successfully set up ${target} as a systemd service."
    
}


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
    printf "${COLOR}%-10s%-26s${NC}\n" "Script" $0
    printf "${COLOR}%-10s%-26s${NC}\n" "OS" "$(lsb_release -ds)"
    printf "${COLOR}%-10s%-26s${NC}\n" "Author" "TAN Hongkui"
    printf "${GREEN_B}====================================${NC}\n"
    echo
    echo -e "${YELLOW_F} 1. 安装seed_s7${NC}"
    echo -e "${YELLOW_F} 2. 安装relay.py${NC}"
    echo -e "${YELLOW_F} 3. 安装simple_vanjee_716mini${NC}"
    echo -e "${YELLOW_F} 4. 安装seed_modbus${NC}"
    # echo -e "${YELLOW_F} 11. stop and disable service seed_s7${NC}"
    # echo -e "${YELLOW_F} 12. stop and disable service relay.py${NC}"
    # echo -e "${YELLOW_F} 13. stop and disable service simple_vanjee_716mini${NC}"
    # echo -e "${YELLOW_F} 14. stop and disable service seed_modbus${NC}"
    echo -e " 0. ctrl+c退出脚本"
    echo
    read -p "请输入数字:" num
    case "$num" in
        1)
            install_target seed_s7 1 1
        ;;
        2)
            install_target relay.py 0 0
        ;;
        3)
            install_target simple_vanjee_716mini.AppImage 1 0
        ;;
        4)
            install_target seed_modbus 1 1
        ;;
        0)
            exit 1
        ;;
        *)
            # clear
            echo -e "请输入正确数字"
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