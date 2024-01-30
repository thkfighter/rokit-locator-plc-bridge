#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created On: 2023-03-27
# SPDX-FileCopyrightText: Copyright (c) 2023 Shanghai Bosch Rexroth Hydraulics & Automation Ltd.
# SPDX-License-Identifier: MIT
#

import socket
import sys
import struct
import argparse
from datetime import datetime
import time
import logging
import requests
import snap7
import json

# logger = logging.getLogger(__name__)

now = datetime.now()
date_time = now.strftime("%d-%m-%Y-%H-%M-%S")

config = {
    "user_name": "admin",
    "password": "admin",
    "locator_host": "127.0.0.1",
    "locator_pose_port": 9011,
    "locator_json_rpc_port": 8080,
    "plc_host": "192.168.8.71",
    "plc_port": 102,
    "plc_rack": 0,
    "plc_slot": 1,
    "seed_count": 8,
    "db_number": 10000,
    "row_size": 26,
    "pose_size": 24,
    "layout": """
0       x               LREAL
8       y               LREAL
16      yaw             LREAL
24.0    enforceSeed     BOOL
24.1    uncertainSeed   BOOL
24.2    recordSeed      BOOL
24.3    setSeed         BOOL
""",
    "debug": 0,
}


# ClientLocalizationPoseDatagram data structure (see API manual)
UNPACKER = struct.Struct("<ddQiQQddddddddddddddQddd")
id = 0
sessionId = ""  # ROKIT Locator JSON RPC session ID


def readCurrentPoseFromLocator() -> dict:
    # Creating a TCP/IP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Connecting to the server
    server_address = (config["locator_host"], config["locator_pose_port"])

    logging.info("connecting to Locator %s : %s ..." % (server_address))
    try:
        sock.connect(server_address)
        logging.info("Connected.")
    except socket.error as e:
        logging.error(str(e.message))
        logging.error("Connection to Locator failed...")
        return

    # read the socket
    data = sock.recv(UNPACKER.size)
    # upack the data (= interpret the datagram)
    unpacked_data = UNPACKER.unpack(data)
    logging.debug(unpacked_data)

    # create a json row
    jsonRow = {
        "timestamp": datetime.fromtimestamp(unpacked_data[1]).strftime(
            "%d-%m-%Y-%H-%M-%S"
        ),
        "x": unpacked_data[6],
        "y": unpacked_data[7],
        # 'yaw': math.degrees(unpacked_data[8]),
        "yaw": unpacked_data[8],
        "localization_state": unpacked_data[3],
    }
    sock.close()
    logging.debug(jsonRow)
    return jsonRow


def clientLocalizationSetSeed(
    sessionId: str,
    x: float,
    y: float,
    a: float,
    enforceSeed: bool = False,
    uncertainSeed: bool = False,
):
    global id
    payload = {
        "id": id,
        "jsonrpc": "2.0",
        "method": "clientLocalizationSetSeed",
        "params": {
            "query": {
                "sessionId": sessionId,
                "enforceSeed": enforceSeed,
                "uncertainSeed": uncertainSeed,
                "seedPose": {"x": x, "y": y, "a": a},
            }
        },
    }
    id = id + 1
    logging.debug(payload)

    logging.info(f"x={x}, y={y}, a={a}")
    response = requests.post(url=url, json=payload)
    logging.debug(response.json())


def sessionLogin() -> str:
    global id
    headers = {
        "Content-Type": "application/json; charset=utf-8",
    }
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
                "userName": config["user_name"],
                "password": config["password"],
            }
        },
    }
    id = id + 1
    logging.debug(payload)

    response = requests.post(url=url, json=payload, headers=headers)
    logging.debug(response.json())
    sessionId = response.json()["result"]["response"]["sessionId"]

    return sessionId


def sessionLogout(sessionId: str = None):
    global id
    payload = {
        "id": id,
        "jsonrpc": "2.0",
        "method": "sessionLogout",
        "params": {"query": {"sessionId": sessionId}},
    }
    id = id + 1

    response = requests.post(url=url, json=payload)
    logging.debug(response.json())


def run():
    client = snap7.client.Client()
    client.connect(
        config["plc_host"], config["plc_rack"], config["plc_slot"], config["plc_port"]
    )
    all_data = client.upload(config["db_number"])
    db = snap7.util.DB(
        db_number=config["db_number"],
        bytearray_=all_data,
        specification=config["layout"],
        row_size=config["row_size"],
        size=config["seed_count"],
    )
    seed_a = db.export()  # snapshot of the DB

    while True:
        time.sleep(0.5)
        seed_b = db.export()  # snapshot of the DB
        for i in range(config["seed_count"]):
            if not seed_a[i]["recordSeed"] and seed_b[i]["recordSeed"]:
                # read current pose from Locator and write it to pose i in the data block
                pose = readCurrentPoseFromLocator()
                assert pose["localization_state"] >= 2, "NOT_LOCALIZED"
                logging.info("LOCALIZED")
                logging.info(pose)
                db[i]["x"] = pose["x"]
                db[i]["y"] = pose["y"]
                db[i]["yaw"] = pose["yaw"]
                db[i]["recordSeed"] = False
                db[i].write()
                logging.info(f"Seed {i} recorded.")
                break
            if not seed_a[i]["setSeed"] and seed_b[i]["setSeed"]:
                setSeed(
                    x=seed_b[i]["x"],
                    y=seed_b[i]["y"],
                    a=seed_b[i]["a"],
                    enforceSeed=seed_b[i]["enforceSeed"],
                    uncertainSeed=seed_b[i]["uncertainSeed"],
                )
                logging.info(f"Seed {i} set.")
                db[i]["setSeed"] = False
                db[i].write()
                break
        seed_a = seed_b


def setSeed(x, y, a, enforceSeed, uncertainSeed):
    sessionId = sessionLogin()
    logging.info(sessionId)
    clientLocalizationSetSeed(
        sessionId=sessionId,
        x=x,
        y=y,
        a=a,
        enforceSeed=enforceSeed,
        uncertainSeed=uncertainSeed,
    )
    sessionLogout(sessionId)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="works as a protocol converter between Siemens S7-1200 and ROKIT Locator",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-c",
        "--config",
        type=str,
        help="Configuration file with path",
    )
    parser.print_help()
    args = parser.parse_args()
    if args.config:
        with open(args.config, "r") as f:
            config.update(json.load(f))
    else:
        config.update(vars(args))

    config_str = json.dumps(config, indent=4)
    print(config_str)
    url = (
        "http://" + config["locator_host"] + ":" + str(config["locator_json_rpc_port"])
    )
    format = "%(asctime)s - %(levelname)s - %(message)s"
    logging.basicConfig(format=format, level=logging.INFO, datefmt="%Y-%m-%d %H:%M:%S")

    while True:
        try:
            time.sleep(0.5)  # give 0.5s for the KeyboardInterrupt to be caught
            run()
        except KeyboardInterrupt:
            # press ctrl+c to stop the program
            sys.exit("The program exits as you press ctrl+c.")
        except Exception as e:
            logging.error(sys.exc_info())
            logging.exception(e)
            logging.error("Some exceptions arise. Restart run()...")
