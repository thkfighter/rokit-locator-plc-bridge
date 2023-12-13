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
    "row_size": 28,
    "pose_size": 24,
    "layout": """
0.0     enforceSeed     BOOL
0.1     uncertainSeed   BOOL
2       x               LREAL
10      y               LREAL
18      a               LREAL
26.0    recordSeed      BOOL
26.1    setSeed         BOOL
""",
    "debug": 0,
}


# Locator

# ClientLocalizationPoseDatagram data structure (see API manual)
UNPACKER = struct.Struct("<ddQiQQddddddddddddddQddd")
id = 0
# pose = {}
sessionId = ""  # ROKIT Locator JSON RPC session ID

# Siemens S7-1200
# number of seeds stored in DB
# Siemens S7 data block number
# bytes that a row/seed resides
# bytes that Pose2D resides in a row/seed
# row/seed specification in a data block


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
    response = requests.post(url=url, json=payload, headers=headers)
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
                    "valid": True,
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

    response = requests.post(url=url, json=payload, headers=headers)
    logging.debug(response.json())


def run():
    client = snap7.client.Client()
    client.connect(
        config["plc_host"], config["plc_rack"], config["plc_slot"], config["plc_port"]
    )
    all_data_a = client.db_read(1, 0, config["row_size"] * config["seed_count"])
    db1_a = snap7.util.DB(
        db_number=config["db_number"],
        bytearray_=all_data_a,
        specification=config["layout"],
        row_size=config["row_size"],
        size=config["seed_count"],
    )
    seed_a = db1_a.export()

    while True:
        time.sleep(0.5)

        all_data_b = client.db_read(1, 0, config["row_size"] * config["seed_count"])
        db1_b = snap7.util.DB(
            db_number=config["db_number"],
            bytearray_=all_data_b,
            specification=config["layout"],
            row_size=config["row_size"],
            size=config["seed_count"],
        )
        seed_b = db1_b.export()
        for i in range(config["seed_count"]):
            if not seed_a[i]["recordSeed"] and seed_b[i]["recordSeed"]:
                # # pose 0 in DB stores current pose
                # # write pose 0 to pose i in the data block
                # client.db_write(
                #     db_number=1,
                #     start=i*config["row_size"]+2,
                #     data=all_data_b[2:2+config["pose_size"]]  # Pose2D in the data block
                # )

                # read current pose from Locator and write it to pose i in the data block
                pose = readCurrentPoseFromLocator()
                assert pose["localization_state"] >= 2, "NOT_LOCALIZED"
                logging.info("LOCALIZED")
                logging.info(pose)

                pose_ba = struct.pack(">ddd", pose["x"], pose["y"], pose["yaw"])
                client.db_write(
                    db_number=config["db_number"],
                    start=i * config["row_size"] + 2,
                    # data=pose_ba+bytearray([0b00000000])
                    data=pose_ba,
                )

                # reset recordSeed
                client.db_write(
                    db_number=config["db_number"],
                    start=i * config["row_size"] + 2 + config["pose_size"],
                    data=bytearray([0b00000000]),
                )
                # client.wait_as_completion(5000)
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

                client.db_write(
                    db_number=config["db_number"],
                    start=i * config["row_size"] + 2 + config["pose_size"],
                    data=bytearray([0b00000000]),
                )
                break
        seed_a = seed_b


def cancel(received_signal):
    """
    Callback method for signal handler
    :param received_signal:     Interrupt Signal number
    :param frame:               Stack frame object
    """


def recordSeed(station: int):
    pass


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
    # parser.add_argument(
    #     "--seed_count", type=int, default=config["seed_count"], help="number of seeds"
    # )
    # parser.add_argument(
    #     "--plc_address", type=str, default=config["plc_host"], help="IP address of PLC"
    # )
    # parser.add_argument(
    #     "--plc_port", type=int, default=config["plc_port"], help="port of PLC"
    # )
    # parser.add_argument(
    #     "--locator_host",
    #     type=str,
    #     default=config["locator_host"],
    #     help="address of Locator",
    # )
    # parser.add_argument(
    #     "--locator_binary_port",
    #     type=int,
    #     default=config["locator_pose_port"],
    #     help="binary port of Locator",
    # )
    # parser.add_argument(
    #     "--locator_json_rpc_port",
    #     type=int,
    #     default=config["locator_json_rpc_port"],
    #     help="JSON RPC port of Locator",
    # )
    # parser.add_argument(
    #     "--locator_user",
    #     type=str,
    #     default=config["user_name"],
    #     help="Locator user name",
    # )
    # parser.add_argument(
    #     "--locator_password",
    #     type=str,
    #     default=config["password"],
    #     help="Locator user password",
    # )
    parser.print_help()

    args = parser.parse_args()
    # if args.seed_count:
    #     config["seed_count"] = args.seed_count
    # if args.plc_address:
    #     config["plc_host"] = args.plc_address
    # if args.plc_port:
    #     r = range(1, 65535)
    #     if args.plc_port not in r:
    #         raise argparse.ArgumentTypeError("Value has to be between 1 and 65535")
    #     config["plc_port"] = args.plc_port
    # if args.locator_user:
    #     config["user_name"] = args.locator_user
    # if args.locator_password:
    #     password = args.locator_password
    # logging.info("PLC address: " + config["plc_host"])
    # logging.info("PLC port: " + str(config["plc_port"]))
    # logging.info("Locator host address: " + config["locator_host"])
    # logging.info("Locator bianry port: " + str(config["locator_pose_port"]))
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
        # finally:
