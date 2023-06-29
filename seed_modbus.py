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
import math
import concurrent.futures
from pymodbus.client import ModbusTcpClient
from pymodbus.constants import Endian
from pymodbus.exceptions import ParameterException
from pymodbus.payload import BinaryPayloadDecoder, BinaryPayloadBuilder

# import threading


# Locator
config = {
    "user_name": "admin",
    "password": "admin",
    "locator_host": "127.0.0.1",
    "locator_pose_port": 9011,
    "locator_json_rpc_port": 8080,
    "plc_host": "192.168.8.71",
    "plc_port": 502,
    "bits_starting_addr": 16,
    "poses_starting_addr": 32,
    "seed_num": 16,
}

# ClientLocalizationPoseDatagram data structure (see API manual)
unpacker = struct.Struct("<ddQiQQddddddddddddddQddd")
# print(datetime.now())

id = 0
pose = {}


def get_client_localization_pose(host, port):
    """Receive localization poses from ROKIT Locator and save them to a global variable, pose"""
    global pose
    # Creating a TCP/IP socket
    client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Connect to the server
    server_address = (host, port)
    client_sock.connect(server_address)
    logging.info(f"Connected to {host}:{port}")

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
            logging.debug(pose)
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


def update_seed_0(host, port, address):
    """Update the first seed in table seeds of locator.db"""
    global pose
    # Set up the Modbus client
    client = ModbusTcpClient(host, port)
    # Connect to the PLC
    client.connect()

    builder = BinaryPayloadBuilder(
        byteorder=Endian.Little, wordorder=Endian.Little)
    try:
        while True:
            if "localization_state" in pose and pose["localization_state"] >= 2:
                pose_a = pose

                builder.add_32bit_float(pose_a["x"])
                builder.add_32bit_float(pose_a["y"])
                builder.add_32bit_float(pose_a["yaw"])
                registers = builder.to_registers()
                client.write_registers(address, registers)

                logging.info(
                    f"seed 0 updated to {pose_a['x']}, {pose_a['y']}, {pose_a['yaw']}"
                )
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
                    builder.reset()
                    builder.add_32bit_float(pose_b["x"])
                    builder.add_32bit_float(pose_b["y"])
                    builder.add_32bit_float(pose_b["yaw"])
                    registers = builder.to_registers()
                    client.write_registers(address, registers)

                    logging.info(
                        f"seed 0 updated to {pose_b['x']}, {pose_b['y']}, {pose_b['yaw']}"
                    )

                    pose_a = pose_b
    finally:
        client.close()


def teach_or_set_seed(host, port, bits_starting_addr, poses_starting_addr, seed_num):
    global pose
    bits_a = []
    bits_b = []
    # Set up the Modbus client
    client = ModbusTcpClient(host, port)
    # Connect to the PLC
    client.connect()

    # Retrieve the data
    register_count = math.ceil(seed_num*4/16)
    result = client.read_holding_registers(
        bits_starting_addr, register_count
    )
    decoder = BinaryPayloadDecoder.fromRegisters(
        result.registers, byteorder=Endian.Little, wordorder=Endian.Little
    )
    for i in range(math.ceil(seed_num*4/8)):
        # bits += decoder.decode_bits()
        t = decoder.decode_bits()
        # make a list of [enforceSeed, uncertainSeed, teachSeed, setSeed]
        bits_a.append(t[:4])
        bits_a.append(t[4:])
    logging.info(f"bits_a: {bits_a}")
    logging.info(f"length of list bits_a: {len(bits_a)}")

    builder = BinaryPayloadBuilder(
        byteorder=Endian.Little, wordorder=Endian.Little)
    try:
        while True:
            time.sleep(0.5)
            result = client.read_holding_registers(
                bits_starting_addr, register_count
            )
            for i in range(math.ceil(seed_num*4/8)):
                # bits += decoder.decode_bits()
                t = decoder.decode_bits()
                # make a list of [enforceSeed, uncertainSeed, teachSeed, setSeed]
                bits_b.append(t[:4])
                bits_b.append(t[4:])
            logging.info(f"bits_b: {bits_b}")
            logging.info(f"length of list bits_b: {len(bits_b)}")

            for i in range(len(bits_b)):
                # teach seed
                if not bits_a[i][2] and bits_b[i][2]:
                    # read current pose from Locator and write it to pose i in the data block
                    pose_current = pose
                    assert pose_current["localization_state"] >= 2, "NOT_LOCALIZED"
                    # Define the values to update and the condition
                    values = (
                        pose_current["x"], pose_current["y"], pose_current["yaw"])
                    builder.add_32bit_float(pose_current["x"])
                    builder.add_32bit_float(pose_current["y"])
                    builder.add_32bit_float(pose_current["yaw"])
                    registers = builder.to_registers()
                    client.write_registers(poses_starting_addr+i*6, registers)
                    # TODO reset bit teachSeed; what does mask do? pymodbus.register_write_message.MaskWriteRegisterResponse
                    #
                    logging.info(
                        f"Seed {i} taught, {values}"
                    )
                    break

                # set seed
                if not bits_a[i][3] and bits_b[i][3]:
                    session_id = sessionLogin()
                    result = client.read_holding_registers(
                        poses_starting_addr+i*6, 6)
                    decoder = BinaryPayloadDecoder.fromRegisters(
                        result.registers, byteorder=Endian.Little, wordorder=Endian.Little
                    )
                    clientLocalizationSetSeed(
                        sessionId=session_id,
                        x=decoder.decode,  # TODO
                        y=seeds_b[i][3],
                        a=seeds_b[i][4],
                        enforceSeed=bool(seeds_b[i][5]),
                        uncertainSeed=bool(seeds_b[i][6]),
                    )
                    sessionLogout(session_id)
                    # reset field set in DB table seeds
                    cursor.execute(
                        "UPDATE seeds SET 'set'=? WHERE id=?", (0, i + 1))

                    # Commit the changes
                    connection.commit()
                    logging.info(
                        f"Seed set, id {seeds_b[i][0]}, name {seeds_b[i][1]}, x={seeds_b[i][2]}, y={seeds_b[i][3]}, yaw={seeds_b[i][4]}"
                    )
                    break
            bits_a = bits_b
    finally:
        client.close()


# def modbus_client(host, port):
#     # Set up the Modbus client
#     client = ModbusTcpClient(host, port)

#     # Connect to the PLC
#     client.connect()

#     try:
#         while True:
#             time.sleep(1)
#             # Read the value of a register
#             result = client.read_holding_registers(address=16, count=4)
#             # Print the result
#             print(result.registers)
#     except KeyboardInterrupt as e:
#         logging.exception("modbus_client() thread received KeyboardInterrupt")
#     finally:
#         # Close the connection
#         client.close()


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
        "--locator_host",
        type=str,
        default=config["locator_host"],
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

    url = (
        "http://" + config["locator_host"] + ":" +
        str(config["locator_json_rpc_port"])
    )

    # format = "%(asctime)s [%(levelname)s] %(threadName)s %(message)s"
    format = "%(asctime)s [%(levelname)s] %(funcName)s(), %(message)s"
    logging.basicConfig(format=format, level=logging.INFO,
                        datefmt="%Y-%m-%d %H:%M:%S")

    # x = threading.Thread(target=get_client_localization_pose, daemon=True)
    # logging.info("start thread get_client_localization_pose")
    # x.start()

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        executor.submit(
            get_client_localization_pose,
            config["locator_host"],
            config["locator_pose_port"],
        )
        executor.submit(
            update_seed_0,
            config["plc_host"],
            config["plc_port"],
            config["poses_starting_addr"],
        )
        executor.submit(teach_or_set_seed, config["plc_host"], config["plc_port"],
                        config["bits_starting_addr"], config["poses_starting_addr"], config["seed_num"])
        # executor.submit(modbus_client, config["plc_host"], config["plc_port"])
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("Main thread received KeyboardInterrupt")
            executor.shutdown(wait=True)
            print("All threads completed")
