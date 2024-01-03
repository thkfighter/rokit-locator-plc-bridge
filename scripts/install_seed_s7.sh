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
if echo $codename | grep -qF "focal" && [ "$arch"="x86_64" ]; then
    suffix="_ubuntu20.04_amd64";
    # echo $suffix;
elif echo $codename | grep -qF "jammy" && [ "$arch"="x86_64" ]; then
    suffix="_ubuntu22.04_amd64";
fi
seed_s7_download="$seed_s7$suffix"

DOWNLOAD_URL="https://gitee.com/${GITEE_REPO_OWNER}/${GITEE_REPO_NAME}/releases/download/${EXECUTABLE_VERSION}/${seed_s7_download}"

# https://gitee.com/thkfighter/locator_plc_bridge/releases/download/v1.0.4/seed_s7_ubuntu22.04_amd64

# Create a directory to store the executable (if not exists)
EXEC_DIR="/home/${USER}/rokit/service"
mkdir -p "${EXEC_DIR}"

# Download the executable
curl -L "${DOWNLOAD_URL}" --output ${EXEC_DIR}/${seed_s7}
chmod +x "${EXEC_DIR}/${seed_s7}"

# Create the systemd service file
SERVICE_FILE="/etc/systemd/system/${seed_s7}.service"
cat > ${SERVICE_FILE}<<-EOF 
[Unit]
Description=ROKIT Locator pose initialization, using protocol s7 to communicate with Siemens S7-1200
After=network.target

[Service]
ExecStart=/home/$USER/rokit/service/$seed_s7 --config /home/$USER/rokit/service/seed_s7_config.json
Restart=always

[Install]
WantedBy=multi-user.target
EOF

cat > "${SERVICE_FILE}"

# Reload systemd daemon to recognize new service file
# systemctl daemon-reload

# Enable the service to start at boot
# systemctl enable "${EXECUTABLE_NAME}.service"

# Start the service
# systemctl start "${EXECUTABLE_NAME}.service"

echo "Successfully set up ${seed_s7} as a systemd service."