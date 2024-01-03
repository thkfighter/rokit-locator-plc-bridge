#!/bin/bash
# -*- coding: utf-8 -*-
#
# Created On: 2024-01-02
# SPDX-FileCopyrightText: Copyright (c) 2024 Shanghai Bosch Rexroth Hydraulics & Automation Ltd.
# SPDX-License-Identifier: MIT
#

# Define variables
GITEE_REPO_OWNER="thkfighter"
GITEE_REPO_NAME="locator_plc_bridge"
EXECUTABLE_VERSION="v1.0.4"
seed_s7="seed_s7"
codename=$(lsb_release -c)
arch=$(uname -m)
if echo $codename | grep -qF "jammy"; then
    os="ubuntu22.04";
    elif echo $codename | grep -qF "focal"; then
    os="ubuntu20.04";
    elif echo $codename | grep -qF "bionic"; then
    os="ubuntu18.04";
fi
if [ "$arch"="x86_64" ]; then
    arch="amd64";
    # elif [ "$arch"="aarch64" ]; then
    # ;
fi
seed_s7_download="${seed_s7}_${os}_${arch}"

DOWNLOAD_URL="https://gitee.com/${GITEE_REPO_OWNER}/${GITEE_REPO_NAME}/releases/download/${EXECUTABLE_VERSION}/${seed_s7_download}"
# https://gitee.com/thkfighter/locator_plc_bridge/releases/download/v1.0.4/seed_s7_ubuntu22.04_amd64
config_url="https://gitee.com/${GITEE_REPO_OWNER}/${GITEE_REPO_NAME}/releases/download/${EXECUTABLE_VERSION}/${seed_s7}_config.json"

# Create a directory to store the executable (if not exists)
EXEC_DIR="/home/${USER}/rokit/service"
mkdir -p "${EXEC_DIR}"

# Download the executable
curl -L "${DOWNLOAD_URL}" --output ${EXEC_DIR}/${seed_s7}
chmod +x "${EXEC_DIR}/${seed_s7}"
curl -L "${config_url}" --output ${EXEC_DIR}/${seed_s7}_config.json

# Create the systemd service file
SERVICE_FILE="/etc/systemd/system/${seed_s7}.service"
cat > ${SERVICE_FILE}<<-EOF
[Unit]
Description=ROKIT Locator pose initialization, using protocol s7 to communicate with Siemens S7-1200
After=network.target

[Service]
ExecStart=/home/$USER/rokit/service/$seed_s7 --config /home/$USER/rokit/service/${seed_s7}_config.json
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
systemctl enable "${seed_s7}.service"

# Start the service
systemctl start "${seed_s7}.service"

echo "Successfully set up ${seed_s7} as a systemd service."