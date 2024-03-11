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
import os
import requests
from construct import *
from pprint import pprint


# ClientLocalizationPoseDatagram data structure (see API manual)
# ClientLocalizationPoseDatagram = struct.Struct("<ddQiQQddddddddddddddQddd")
# https://docs.python.org/3/library/struct.html
# print(datetime.now())


format = "%(asctime)s [%(levelname)s] %(funcName)s(), %(message)s"
logging.basicConfig(
    format=format,
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)

# ====== JSON-RPC ======

id = 0
payload = {
    "id": id,
    "jsonrpc": "2.0",
    "method": "supportRecoveryList",
    "params": {"query": {}},
}


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


def supportRecoveryList(url, sessionId):
    global id

    payload = {
        "id": id,
        "jsonrpc": "2.0",
        "method": "supportRecoveryList",
        "params": {"query": {"sessionId": sessionId}},
    }
    id = id + 1

    response = requests.post(url=url, json=payload)
    logging.debug(response.json())
    return response.json()
    # if response.json()["result"]["response"]["responseCode"] == 0:
    #     return True
    # else:
    #     return False


def supportRecoveryCreate(url, payload, sessionId):
    global id
    payload["id"] = id
    payload["method"] = "supportRecoveryCreate"
    payload["params"]["query"] = {"sessionId": sessionId}
    id = id + 1
    response = requests.post(url=url, json=payload)
    logging.debug(response.json())
    return response.json()


def supportRecoveryDelete(url, payload, sessionId, recoveryName):
    global id
    payload["id"] = id
    payload["method"] = "supportRecoveryDelete"
    payload["params"]["query"] = {"sessionId": sessionId, "recoveryName": recoveryName}
    id = id + 1
    response = requests.post(url=url, json=payload)
    logging.debug(response.json())
    return response.json()


def supportRecoveryFactoryReset(url, payload, sessionId):
    global id
    payload["id"] = id
    payload["method"] = "supportRecoveryFactoryReset"
    payload["params"]["query"] = {"sessionId": sessionId}
    id = id + 1
    response = requests.post(url=url, json=payload)
    logging.debug(response.json())
    return response.json()


def supportRecoveryFrom(url, payload, sessionId, recoveryName):
    global id
    payload["id"] = id
    payload["method"] = "supportRecoveryFrom"
    payload["params"]["query"] = {"sessionId": sessionId, "recoveryName": recoveryName}
    id = id + 1
    response = requests.post(url=url, json=payload)
    logging.debug(response.json())
    return response.json()


def clientSensorLaserOutputStart(url, payload, sessionId):
    global id
    payload["id"] = id
    payload["method"] = "clientSensorLaserOutputStart"
    payload["params"]["query"] = {"sessionId": sessionId}
    id = id + 1
    response = requests.post(url=url, json=payload)
    logging.debug(response.json())
    return response.json()


def clientSensorGetLaserScan(url, payload, sessionId):
    global id
    payload["id"] = id
    payload["method"] = "clientSensorGetLaserScan"
    payload["params"]["query"] = {"sessionId": sessionId, "laserIndex": 0}
    id = id + 1
    response = requests.post(url=url, json=payload)
    logging.debug(response.json())
    return response.json()


# ====== Binary Interfaces ======


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
    """ClientControlModeDatagram

    Args:
        host (str): IP address of ROKIT Locator Client host
        port (int): port
    """
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

            logging.info("Client Control Mode")
            cm = oct(unpacked_data)
            # print(cm) # 0o1112111

            # make a dict
            # values = list(cm)[::-1]
            # keys = [
            #     "LASEROUTPUT",
            #     "ALIGN",
            #     "REC",
            #     "LOC",
            #     "MAP",
            #     "VISUALRECORDING",
            #     "EXPANDMAP",
            # ]
            # print(values)
            # cm_dict = dict(zip(keys, values))
            # cm_dict_int = {key: int(value) for key, value in cm_dict.items()}
            # print(json.dumps(cm_dict_int, indent=4))

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
    """ClientLocalizationPoseDatagram

    Args:
        host (str): IP address of ROKIT Locator Client host
        port (int): port
    """
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
            json_str = json.dumps(ClientLocalizationPoseDatagram, indent=4)
            # Clear the screen
            os.system("cls" if os.name == "nt" else "clear")
            print(json_str)

            # create a json row
            # pose = {
            #     "timestamp": datetime.fromtimestamp(values[1]).strftime(
            #         "%d-%m-%Y-%H-%M-%S"
            #     ),
            #     "x": values[6],
            #     "y": values[7],
            #     # 'yaw': math.degrees(values[8]),
            #     "yaw": values[8],
            #     "localization_state": values[3],
            # }
            # logging.info(pose)
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


def get_client_sensor_laser(
    host, port, count_beams, has_intensities: bool = True, is_cyclic: bool = True
):
    ClientSensorLaserDatagram = Struct(
        "scanNum" / Int16ul,
        "time_start" / Float64l,
        "uniqueId" / Int64ul,
        "duration_beam" / Float64l,
        "duration_scan" / Float64l,
        "duration_rotate" / Float64l,
        "numBeams" / Int32ul,
        "angleStart" / Float32l,
        "angleEnd" / Float32l,
        "angleInc" / Float32l,
        "minRange" / Float32l,
        "maxRange" / Float32l,
        "rangeArraySize" / Int32ul,
        "ranges" / Array(this.rangeArraySize, Float32l),
        "hasIntensities" / Int8ul,
        "minIntensity" / Float32l,
        "maxIntensity" / Float32l,
        "intensityArraySize" / Int32ul,
        "intensities" / Array(this.intensityArraySize, Float32l),
    )
    if has_intensities:
        buffer_size = 83 + (4 + 4) * count_beams
    else:
        buffer_size = 83 + 4 * count_beams
    client = connect_socket(host, port)
    data = client.recv(1024)
    while len(data) < buffer_size:  # Continue reading while data is still available
        data += client.recv(1024)
    pprint(dict(ClientSensorLaserDatagram.parse(data)), indent=4, sort_dicts=False)

    while is_cyclic:
        try:
            data = client.recv(1024)
            # bufsize=2247 when rangeArraySize=541 and intensityArraySize=0
            if not data:
                continue
            while (
                len(data) < buffer_size
            ):  # Continue reading while data is still available
                data += client.recv(1024)
            pprint(
                dict(ClientSensorLaserDatagram.parse(data)), indent=4, sort_dicts=False
            )
        except struct.error as e:
            logging.exception(e)
        # except OSError as e:
        except (TimeoutError, OSError) as e:
            # logging.exception(e)
            time.sleep(1)
            if client:
                continue
            client = connect_socket(host, port)
        except StreamError as e:
            logging.exception(e)


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
