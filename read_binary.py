#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created On: 2023-12-08
# SPDX-FileCopyrightText: Copyright (c) 2023 Shanghai Bosch Rexroth Hydraulics & Automation Ltd.
# SPDX-License-Identifier: MIT


import socket
import struct
import argparse
from datetime import datetime
import time
import logging
import json

import requests


# ClientLocalizationPoseDatagram data structure (see API manual)
# ClientLocalizationPoseDatagram = struct.Struct("<ddQiQQddddddddddddddQddd")
# https://docs.python.org/3/library/struct.html
# print(datetime.now())

id = 0

format = "%(asctime)s [%(levelname)s] %(funcName)s(), %(message)s"
logging.basicConfig(
    format=format,
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)

# JSON-RPC


def sessionLogin(url, user_name, password) -> str:
    global id
    payload = {
        "id": id,
        "jsonrpc": "2.0",
        "method": "sessionLogin",
        "params": {
            "query": {
                "timeout": {  # timeout, not timestamp
                    "valid": False,
                    "time": 60,  # Integer64
                    "resolution": 1,  # real_time = time / resolution
                },
                "userName": user_name,
                "password": password,
            }
        },
    }
    id = id + 1
    logging.debug(payload)
    response = requests.post(url=url, json=payload)
    logging.debug(response.json())
    sessionId = response.json()["result"]["response"]["sessionId"]
    return sessionId  # an empty string in case of a sessionLogin failure


def sessionLogout(url, sessionId: str = None) -> bool:
    global id
    # headers = {
    #     "Content-Type": "application/json; charset=utf-8",
    # }

    payload = {
        "id": id,
        "jsonrpc": "2.0",
        "method": "sessionLogout",
        "params": {"query": {"sessionId": sessionId}},
    }
    id = id + 1

    response = requests.post(url=url, json=payload)
    logging.debug(response.json())
    if response.json()["result"]["response"]["responseCode"] == 0:
        return True
    else:
        return False


# Binary Interfaces


def connect_socket(host, port):
    while True:
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.settimeout(5)  # set a timeout on blocking socket operations
            client.connect((host, port))
            logging.info(
                f"Local address: {client.getsockname()} <-connected-> Remote address: {client.getpeername()}"
            )
            return client
        except (TimeoutError, ConnectionRefusedError, OSError) as e:
            if client:
                client.close()
            # logging.warning(f"Errno: {e.errno}")
            logging.warning(e)
            time.sleep(5)


def get_client_control_mode(host, port):
    unpacker = struct.Struct("<I")
    client = connect_socket(host, port)
    while True:
        try:
            data = client.recv(unpacker.size)
            # print(data)
            if not data:
                continue
            unpacked_data = (unpacker.unpack(data))[0]

            # 2-0   LASEROUTPUT
            # 5-3   ALIGN
            # 8-6   REC
            # 11-9  LOC
            # 14-12 MAP
            # 17-15 VISUALRECORDING
            # 20-18 EXPANDMAP
            # 31-21 Unused

            cm = oct(unpacked_data)
            logging.info("Client Control Mode")
            print(f"LASEROUTPUT: {cm[-1]}")
            print(f"ALIGN: {cm[-2]}")
            print(f"REC: {cm[-3]}")
            print(f"LOC: {cm[-4]}")
            print(f"MAP: {cm[-5]}")
            print(f"VISUALRECORDING: {cm[-6]}")
            print(f"EXPANDMAP: {cm[-7]}")

        except struct.error as e:
            logging.exception(e)
        # except OSError as e:
        except (TimeoutError, OSError) as e:
            # logging.exception(e)
            time.sleep(1)
            if client:
                continue
            client = connect_socket(host, port)


def get_client_localization_pose(host, port):
    """Receive localization poses from ROKIT Locator and save them to a global variable, pose"""
    unpacker = struct.Struct("<ddQiQQddddddddddddddQddd")
    keys = [
        "age",
        "timestamp",
        "uniqueId",
        "state",
        "errorFlags",
        "infoFlags",
        "poseX",
        "poseY",
        "poseYaw",
        "covariance_1_1",
        "covariance_1_2",
        "covariance_1_3",
        "covariance_2_2",
        "covariance_2_3",
        "covariance_3_3",
        "poseZ",
        "quaternion_w",
        "quaternion_x",
        "quaternion_y",
        "quaternion_z",
        "epoch",
        "lidarOdoPoseX",
        "lidarOdoPoseY",
        "lidarOdoPoseYaw",
    ]

    client = connect_socket(host, port)
    while True:
        try:
            data = client.recv(unpacker.size)
            if not data:
                continue
            values = unpacker.unpack(data)

            ClientLocalizationPoseDatagram = dict(zip(keys, values))
            json_str = json.dumps(ClientLocalizationPoseDatagram)
            print(json_str)

            # create a json row
            pose = {
                "timestamp": datetime.fromtimestamp(values[1]).strftime(
                    "%d-%m-%Y-%H-%M-%S"
                ),
                "x": values[6],
                "y": values[7],
                # 'yaw': math.degrees(values[8]),
                "yaw": values[8],
                "localization_state": values[3],
            }
            logging.info(pose)
        # except TimeoutError as e:
        #     logging.warning(e)
        except struct.error as e:
            logging.exception(e)
        # except OSError as e:
        except (TimeoutError, OSError) as e:
            # logging.exception(e)
            time.sleep(1)
            if client:
                continue
            client = connect_socket(host, port)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="a program to parse binary data",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="IP of ROKIT Locator client",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=9004,
        help="Port of binary ClientControlMode",
    )
    parser.add_argument(
        "--debug",
        type=int,
        default=0,
        help="0: logging.INFO, 1: logging.DEBUG",
    )

    parser.print_help()

    args = parser.parse_args()

    if args.host:
        host = args.host
    else:
        host = "127.0.0.1"

    if args.port:
        port = args.port
    else:
        port = 9004

    if args.debug:
        debug = args.debug
    else:
        debug = 0

    # sessionLogin("http://localhost:8080", "admin", "password")

    get_client_control_mode(host, port)
