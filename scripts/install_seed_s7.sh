#!/bin/bash
# -*- coding: utf-8 -*-
#
# Created On: 2024-01-02
# SPDX-FileCopyrightText: Copyright (c) 2024 Shanghai Bosch Rexroth Hydraulics & Automation Ltd.
# SPDX-License-Identifier: MIT
#

# sudo -u $USER -E bash scripts/install_seed_s7.sh
# sudo -E bash scripts/install_seed_s7.sh

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
EXEC_DIR="/home/${USER}/rokit/service"
mkdir -p "${EXEC_DIR}"

install_seed_s7()
{
    target="seed_s7_${os}_${arch}"
    target_config="seed_s7_config.json"
    url_target="${url_prefix}${target}"
    # Download the executable
    wget -nv -P ${EXEC_DIR} ${url_target}
    chmod +x "${EXEC_DIR}/${target}"
    wget -nv -P ${EXEC_DIR} ${url_prefix}${target_config}
    
    # Create the systemd service file
    SERVICE_FILE="/etc/systemd/system/${target}.service"
    cat > ${SERVICE_FILE} <<-EOF
    [Unit]
    Description=ROKIT Locator pose initialization, using protocol s7 to communicate with Siemens S7-1200
    After=network.target

    [Service]
    ExecStartPre=/bin/sleep 3 # delay 3 seconds
    ExecStart=/home/${USER}/rokit/service/${target} --config /home/${USER}/rokit/service/${target}_config.json
    Restart=always

    [Install]
    WantedBy=multi-user.target
EOF
    
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


install_relay(){
    target="relay.py"
    url_target="https://gitee.com/${GITEE_REPO_OWNER}/${GITEE_REPO_NAME}/releases/download/${EXECUTABLE_VERSION}/${target}.py"
    # https://gitee.com/thkfighter/locator_plc_bridge/releases/download/v1.0.4/relay.py
    
    # Download the executable
    wget -nv -P ${EXEC_DIR} ${url_target}
    chmod +x "${EXEC_DIR}/${target}"
    
    # Create the systemd service file
    SERVICE_FILE="/etc/systemd/system/${target}.service"
    cat > ${SERVICE_FILE} <<-EOF
    [Unit]
    Description=works as a relay to retransmit poses at a specific frequency
    After=network.target

    [Service]
    ExecStartPre=/bin/sleep 3 # delay 3 seconds
    ExecStart=/usr/bin/python3 /home/${USER}/rokit/service/${target} --frq_divisor 3 --src_host 127.0.0.1 --src_port 9011 --dst_port 9511
    Restart=always

    [Install]
    WantedBy=multi-user.target
EOF
    
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
    echo -e " 0. ctrl+c退出脚本"
    echo
    read -p "请输入数字:" num
    case "$num" in
        1)
            install_seed_s7
        ;;
        2)
            install_relay
        ;;
        3)
            install_simple_vanjee_716mini
        ;;
        4)
            install_seed_modbus
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