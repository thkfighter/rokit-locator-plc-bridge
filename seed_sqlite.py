#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created On: 2023-06-18
# Copyright (c) 2023 Shanghai Bosch Rexroth Hydraulics & Automation Ltd.
#
# https://realpython.com/intro-to-python-threading/#producer-consumer-using-lock

import socket
import struct
import argparse
from datetime import datetime
import time
import logging
import requests
import sqlite3
import json
import concurrent.futures

# import threading


# Locator
config = {
    "user_name": "admin",
    "password": "admin",
    "locator_ip": "127.0.0.1",
    "locator_pose_port": 9011,
    "locator_json_rpc_port": 8080,
}

url = "http://" + config["locator_ip"] + ":" + str(config["locator_json_rpc_port"])

# ClientLocalizationPoseDatagram data structure (see API manual)
unpacker = struct.Struct("<ddQiQQddddddddddddddQddd")
# print(datetime.now())

id = 0
pose = {}


def get_client_localization_pose():
    """Receive localization poses from ROKIT Locator and save them to a global variable, pose"""
    global pose
    # Creating a TCP/IP socket
    client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Connect to the server
    server_address = (config["locator_ip"], config["locator_pose_port"])
    client_sock.connect(server_address)
    logging.info(
        f"Connected to {config['locator_ip']} on port {config['locator_pose_port']}"
    )

    try:
        while True:
            # read the socket
            data = client_sock.recv(unpacker.size)
            # upack the data (= interpret the datagram)
            if not data:
                continue
            unpacked_data = unpacker.unpack(data)

            # create a json row
            pose = {
                "timestamp": datetime.fromtimestamp(unpacked_data[1]).strftime(
                    "%d-%m-%Y-%H-%M-%S"
                ),
                "x": unpacked_data[6],
                "y": unpacked_data[7],
                # 'yaw': math.degrees(unpacked_data[8]),
                "yaw": unpacked_data[8],
                "localization_state": unpacked_data[3],
            }
            # logging.debug(pose)
    finally:
        client_sock.close()


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
    # print(response.json())


def sessionLogin() -> str:
    global id
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

    response = requests.post(url=url, json=payload)
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

    response = requests.post(url=url, json=payload)
    logging.debug(response.json())


def update_seed_1():
    """Update the first seed in table seeds of locator.db"""
    global pose
    # Connect to the database
    connection = sqlite3.connect("locator.db")
    # Create a cursor object
    cursor = connection.cursor()

    try:
        while True:
            if "localization_state" in pose and pose["localization_state"] >= 2:
                pose_a = pose
                # Define the update query
                query = "UPDATE seeds SET x = ?, y=?, yaw=? WHERE id =1"
                # Define the values to update and the condition
                values = (pose_a["x"], pose_a["y"], pose_a["yaw"])
                # Execute the query
                cursor.execute(query, values)
                # Commit the changes
                connection.commit()
                logging.debug(f"last pose updated to {values}")
                break
            else:
                time.sleep(0.5)
                continue

        while True:
            time.sleep(0.5)
            if "localization_state" in pose and pose["localization_state"] >= 2:
                pose_b = pose
                # update last pose on the first row of table seeds
                # units: meter and radian, 0.0087 radians = 0.5 degrees
                if (
                    abs(pose_b["x"] - pose_a["x"]) > 0.005
                    or abs(pose_b["y"] - pose_a["y"]) > 0.005
                    or abs(pose_b["yaw"] - pose_a["yaw"]) > 0.0087
                ):
                    # Define the update query
                    query = "UPDATE seeds SET x = ?, y=?, yaw=? WHERE id =1"
                    # Define the values to update and the condition
                    values = (pose_b["x"], pose_b["y"], pose_b["yaw"])
                    # Execute the query
                    cursor.execute(query, values)
                    # Commit the changes
                    connection.commit()
                    logging.debug(f"seed 1 updated to {values}")

                    pose_a = pose_b
    finally:
        cursor.close()
        connection.close()


def teach_or_set_seed():
    global pose
    # Connect to the database
    connection = sqlite3.connect("locator.db")
    # Create a cursor object
    cursor = connection.cursor()
    # Retrieve the data
    seeds_a = cursor.execute("SELECT * FROM seeds").fetchall()

    try:
        while True:
            time.sleep(0.5)

            seeds_b = cursor.execute("SELECT * FROM seeds").fetchall()

            for i in range(len(seeds_b)):
                # teach seed
                if not seeds_a[i][7] and seeds_b[i][7]:
                    # read current pose from Locator and write it to pose i in the data block
                    # pose = get_client_localization_pose()
                    assert pose["localization_state"] >= 2, "NOT_LOCALIZED"

                    # Define the update query
                    query = "UPDATE seeds SET x = ?, y=?, yaw=?, teach=? WHERE id =?"
                    # Define the values to update and the condition
                    values = (pose["x"], pose["y"], pose["yaw"], 0, i + 1)
                    # Execute the query
                    cursor.execute(query, values)
                    # Commit the changes
                    connection.commit()

                    logging.info(
                        f"Seed taught, id {seeds_b[i][0]}, name {seeds_b[i][1]}, {values[:3]}"
                    )
                    break

                # set seed
                if not seeds_a[i][8] and seeds_b[i][8]:
                    session_id = sessionLogin()
                    clientLocalizationSetSeed(
                        sessionId=session_id,
                        x=seeds_b[i][2],
                        y=seeds_b[i][3],
                        a=seeds_b[i][4],
                        enforceSeed=bool(seeds_b[i][5]),
                        uncertainSeed=bool(seeds_b[i][6]),
                    )
                    sessionLogout(session_id)
                    # reset field set in DB table seeds
                    cursor.execute("UPDATE seeds SET 'set'=? WHERE id=?", (0, i + 1))

                    # Commit the changes
                    connection.commit()
                    logging.info(
                        f"Seed set, id {seeds_b[i][0]}, name {seeds_b[i][1]}, x={seeds_b[i][2]}, y={seeds_b[i][3]}, yaw={seeds_b[i][4]}"
                    )
                    break
            seeds_a = seeds_b
    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="a program to teach and set seeds for ROKIT Locator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "-c",
        "--config",
        type=str,
        help="The path to the configuration file",
    )
    parser.add_argument(
        "--user_name",
        type=str,
        default=config["user_name"],
        help="User name of ROKIT Locator client",
    )
    parser.add_argument(
        "--password",
        type=str,
        default=config["password"],
        help="Password of ROKIT Locator client",
    )
    parser.add_argument(
        "--locator_ip",
        type=str,
        default=config["locator_ip"],
        help="IP of ROKIT Locator client",
    )
    parser.add_argument(
        "--locator_pose_port",
        type=int,
        default=config["locator_pose_port"],
        help="Port of binary ClientLocalizationPose",
    )
    parser.add_argument(
        "--locator_json_rpc_port",
        type=int,
        default=config["locator_json_rpc_port"],
        help="Port of JSON RPC ROKIT Locator Client",
    )

    args = parser.parse_args()
    # config.json has the highest priority and it will overide other command-line arguments
    if args.config:
        with open(args.config, "r") as f:
            config.update(json.load(f))
    else:
        config.update(vars(args))
    # parser.print_help()
    print(config)

    # format = "%(asctime)s [%(levelname)s] %(threadName)s %(message)s"
    format = "%(asctime)s [%(levelname)s] %(funcName)s(), %(message)s"
    logging.basicConfig(format=format, level=logging.DEBUG, datefmt="%Y-%m-%d %H:%M:%S")

    # x = threading.Thread(target=get_client_localization_pose, daemon=True)
    # logging.info("start thread get_client_localization_pose")
    # x.start()

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        executor.submit(get_client_localization_pose)
        executor.submit(update_seed_1)
        executor.submit(teach_or_set_seed)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("Main thread received KeyboardInterrupt")
            executor.shutdown(wait=True)
            print("All threads completed")
