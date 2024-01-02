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
EXECUTABLE_NAME="seed_s7_ubuntu22.04_amd64" # TODO system version
EXECUTABLE_VERSION="v1.0.4"
DOWNLOAD_URL="https://gitee.com/${GITEE_REPO_OWNER}/${GITEE_REPO_NAME}/releases/download/${EXECUTABLE_VERSION}/${EXECUTABLE_NAME}"

# https://gitee.com/thkfighter/locator_plc_bridge/releases/download/v1.0.4/seed_s7_ubuntu22.04_amd64

# Create a directory to store the executable (if not exists)
EXEC_DIR="/home/${USER}/rokit/service"
mkdir -p "${EXEC_DIR}"

# Download the executable
curl -L "${DOWNLOAD_URL}" -o "${EXEC_DIR}/${EXECUTABLE_NAME}"
chmod +x "${EXEC_DIR}/${EXECUTABLE_NAME}"

# Create the systemd service file
SERVICE_FILE="/etc/systemd/system/${EXECUTABLE_NAME}.service"
cat <<EOF > "${SERVICE_FILE}"
[Unit]
Description=My Executable Service
After=network.target

[Service]
ExecStart=${EXEC_DIR}/${EXECUTABLE_NAME}
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd daemon to recognize new service file
systemctl daemon-reload

# Enable the service to start at boot
systemctl enable "${EXECUTABLE_NAME}.service"

# Start the service
# systemctl start "${EXECUTABLE_NAME}.service"

echo "Successfully set up ${EXECUTABLE_NAME} as a systemd service."