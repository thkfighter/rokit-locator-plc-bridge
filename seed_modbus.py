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
# import sqlite3
import json
import math
import concurrent.futures
from pymodbus.client import ModbusTcpClient
from pymodbus.constants import Endian
from pymodbus.exceptions import ParameterException, ConnectionException
from pymodbus.payload import BinaryPayloadDecoder, BinaryPayloadBuilder
import bitstring
from bitstring import BitArray

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
    while True:
        try:
            # Creating a TCP/IP socket
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.settimeout(5)
            client.connect((host, port))
            logging.info(f"Connected to {host}:{port}")
            logging.info(f"Local address: {client.getsockname}")
            logging.info(f"Remote address: {client.getpeername}")
            # if the connection is successful, break out of the loop
            break
        except OSError:
            print("Failed to connect. Retrying in 5 seconds...")
            time.sleep(5)

    while True:
        try:
            # read the socket
            data = client.recv(unpacker.size)
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
        except OSError:
            # if there is a socket error, close the socket and start the loop again to try to reconnect
            client.close()
            print("Socket error. Reconnecting...")
            while True:
                try:
                    # create a new socket and try to reconnect
                    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    client.settimeout(5)
                    client.connect((host, port))
                    break
                except OSError:
                    print("Failed to reconnect. Retrying in 5 seconds...")
                    time.sleep(3)


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

    while True:
        try:
            # Set up the Modbus client
            client = ModbusTcpClient(host, port)
            # Connect to the PLC
            client.connect()
            break
        except ConnectionException:
            # if there is a socket error, wait for 5 seconds before trying again
            print("Failed to connect to modbus slave. Retrying in 5 seconds...")
            time.sleep(5)

    while True:
        try:
            # initialize seed 0 if pose has a localization status greater than 1
            while True:
                if "localization_state" in pose and pose["localization_state"] >= 2:
                    pose_a = pose
                    mb_set_pose(client, address, pose_a)
                    logging.info(
                        f"seed 0 updated to {pose_a['x']}, {pose_a['y']}, {pose_a['yaw']}"
                    )
                    break
                else:
                    time.sleep(0.5)
                    continue
            # loop to update seed 0 if poses change more than specified values
            while True:
                time.sleep(0.5)
                if "localization_state" in pose and pose["localization_state"] >= 2:
                    pose_b = pose
                    # units: meter and radian, 0.0087 radians = 0.5 degrees
                    if (
                        abs(pose_b["x"] - pose_a["x"]) > 0.005
                        or abs(pose_b["y"] - pose_a["y"]) > 0.005
                        or abs(pose_b["yaw"] - pose_a["yaw"]) > 0.0087
                    ):
                        mb_set_pose(client, address, pose_b)
                        logging.info(
                            f"seed 0 updated to {pose_b['x']}, {pose_b['y']}, {pose_b['yaw']}"
                        )

                        pose_a = pose_b
        except ConnectionException:
            # logging.exception(e)
            client.close()
            while True:
                try:
                    # Set up the Modbus client
                    client = ModbusTcpClient(host, port)
                    # Connect to the PLC
                    client.connect()
                    break
                except ConnectionException:
                    # if there is a socket error, wait for 5 seconds before trying again
                    print("Failed to connect to modbus slave. Retrying in 5 seconds...")
                    time.sleep(3)


def teach_or_set_seed(host, port, bits_starting_addr, poses_starting_addr, seed_num):
    global pose
    bits_a = []
    bits_b = []

    while True:
        try:
            # Set up the Modbus client
            client = ModbusTcpClient(host, port, timeout=5)
            client.connect()
            break
        except:
            # if there is a socket error, wait for 5 seconds before trying again
            print("Failed to connect to modbus slave. Retrying in 5 seconds...")
            time.sleep(5)

    while True:
        try:
            # Retrieve the data
            bits_a = mb_get_bits(bits_starting_addr, seed_num, client)

            while True:
                time.sleep(0.5)
                bits_b = mb_get_bits(bits_starting_addr, seed_num, client)
                if bits_b == bits_a:
                    continue
                logging.debug(f"bits_a, length={len(bits_a)}: {bits_a}")
                logging.debug(f"bits_b, length={len(bits_b)}: {bits_b}")
                for i in range(len(bits_b)):
                    # teach seed
                    if (not bits_a[i][2] and bits_b[i][2]):
                        # read current pose from Locator and write it to pose i in the data block
                        pose_current = pose
                        assert pose_current["localization_state"] >= 2, "NOT_LOCALIZED"
                        mb_set_pose(client, poses_starting_addr +
                                    i*6, pose_current)
                        logging.info(
                            f"Seed {i} taught, {pose_current['x']}, {pose_current['y']}, {pose_current['yaw']}"
                        )
                        bits_a = bits_b
                        # reset bit teachSeed in modbus data block
                        bits_b[i][2] = False
                        mb_set_bits(client, bits_starting_addr, bits_b)
                        break

                    # set seed
                    if (not bits_a[i][3] and bits_b[i][3]):
                        session_id = sessionLogin()
                        pose_x, pose_y, pose_yaw = mb_get_pose(
                            poses_starting_addr, i, client)
                        clientLocalizationSetSeed(
                            sessionId=session_id,
                            x=pose_x,
                            y=pose_y,
                            a=pose_yaw,
                            enforceSeed=bits_b[i][0],
                            uncertainSeed=bits_b[i][1],
                        )
                        # TODO if setting seed fails
                        sessionLogout(session_id)
                        logging.info(
                            f"Seed {i} set, x={pose_x}, y={pose_y}, yaw={pose_yaw}"
                        )
                        bits_a = bits_b
                        # reset bit setSeed in modbus data block
                        bits_b[i][3] = False
                        mb_set_bits(client, bits_starting_addr, bits_b)
                        break
                # bits_b != bits_a, but no changing from False to True
                bits_a = bits_b
        except ConnectionException:
            # logging.exception(e)
            client.close()
            while True:
                try:
                    # Set up the Modbus client
                    client = ModbusTcpClient(host, port)
                    # Connect to the PLC
                    client.connect()
                    break
                except ConnectionException:
                    # if there is a socket error, wait for 5 seconds before trying again
                    print("Failed to connect to modbus slave. Retrying in 5 seconds...")
                    time.sleep(3)


def mb_get_pose(poses_starting_addr, i, client):
    result = client.read_holding_registers(
        poses_starting_addr+i*6, 6)
    decoder = BinaryPayloadDecoder.fromRegisters(
        result.registers, byteorder=Endian.Little, wordorder=Endian.Little
    )
    pose_x = decoder.decode_32bit_float()
    pose_y = decoder.decode_32bit_float()
    pose_yaw = decoder.decode_32bit_float()
    return pose_x, pose_y, pose_yaw


def mb_set_pose(client, address, pose):
    builder = BinaryPayloadBuilder(
        byteorder=Endian.Little, wordorder=Endian.Little)
    builder.add_32bit_float(pose["x"])
    builder.add_32bit_float(pose["y"])
    builder.add_32bit_float(pose["yaw"])
    registers = builder.to_registers()
    client.write_registers(address, registers)


def mb_get_bits(bits_starting_addr, seed_num, client):
    bits_list = []
    bits = BitArray()
    bits_register_count = math.ceil(seed_num*4/16)
    result = client.read_holding_registers(
        bits_starting_addr, bits_register_count
    )
    # decoder = BinaryPayloadDecoder.fromRegisters(
    #     result.registers, byteorder=Endian.Little, wordorder=Endian.Little
    # )
    for register in result.registers:
        bit_16 = BitArray(uint=register, length=16)
        bit_16.reverse()
        bits.append(bit_16)
    for bit_4 in bits.cut(4):
        bit_4_list = [bit == '1' for bit in bit_4.bin]
        bits_list.append(bit_4_list)
    logging.debug(bits_list)
    # for i in range(math.ceil(seed_num*4/8)):
    #     t = decoder.decode_bits()
    #     # make a list of [enforceSeed, uncertainSeed, teachSeed, setSeed]
    #     bits.append(t[:4])
    #     bits.append(t[4:])
    return bits_list


def mb_set_bits(client, bits_starting_addr, bits_list):
    """_summary_

    Args:
        bits_starting_addr (uint): _description_
        bits_list (list): a two-dimentional array
        client (ModbusTcpClient): _description_
    """
    bool_list = [item for sublist in bits_list for item in sublist]
    bits = BitArray()
    for bool_val in bool_list:
        bits.append('0b1' if bool_val else '0b0')
    builder = BinaryPayloadBuilder(
        byteorder=Endian.Little, wordorder=Endian.Little)
    for bits_16 in bits.cut(16):
        bits_16.reverse()
        builder.add_16bit_uint(bits_16.uint)
    registers = builder.to_registers()
    client.write_registers(bits_starting_addr, registers)


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
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("Main thread received KeyboardInterrupt")
            executor.shutdown(wait=True)
            print("All threads completed")
