#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created On: 2023-06-18
# SPDX-FileCopyrightText: Copyright (c) 2023 Shanghai Bosch Rexroth Hydraulics & Automation Ltd.
# SPDX-License-Identifier: MIT
#
# https://realpython.com/intro-to-python-threading/#producer-consumer-using-lock

import socket
import struct
import argparse
from datetime import datetime
import time
import logging
import requests

import json
import math
from pymodbus.client import ModbusTcpClient

# from pymodbus.constants import Endian
from pymodbus.exceptions import ModbusException, ConnectionException
from pymodbus.pdu import ExceptionResponse
from pymodbus.payload import BinaryPayloadDecoder, BinaryPayloadBuilder
from bitstring import BitArray
import sys
import threading


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
    "byte_order": ">",
    "word_order": "<",
    "debug": 0,
}

# ClientLocalizationPoseDatagram data structure (see API manual)
unpacker = struct.Struct("<ddQiQQddddddddddddddQddd")
# print(datetime.now())

id = 0
pose = {}


def get_client_localization_pose(host, port):
    """Receive localization poses from ROKIT Locator and save them to a global variable, pose"""
    global pose

    def connect_socket():
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

    client = connect_socket()
    while True:
        try:
            data = client.recv(unpacker.size)
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
        # except TimeoutError as e:
        #     logging.warning(e)
        except struct.error as e:
            logging.exception(e)
        # except OSError as e:
        except (TimeoutError, OSError) as e:
            logging.exception(e)
            if client:
                client.close()
            time.sleep(5)
            client = connect_socket()


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

    logging.debug(f"x={x}, y={y}, a={a}")
    response = requests.post(url=url, json=payload)
    logging.debug(response.json())
    if response.json()["result"]["response"]["responseCode"] == 0:
        return True
    else:
        return False


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
    return sessionId  # an empty string in case of a sessionLogin failure


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
    if response.json()["result"]["response"]["responseCode"] == 0:
        return True
    else:
        return False


def update_seed_0(host, port, address, byte_order, word_order):
    """Update the first seed in table seeds of locator.db"""
    global pose
    # Set up the Modbus client
    client = ModbusTcpClient(host, port)
    pose_a = {}
    while True:
        try:
            if "localization_state" in pose and pose["localization_state"] >= 2:
                pose_b = pose
                # units: meter and radian, 0.0087 radians = 0.5 degrees
                if (
                    pose_a == {}
                    or abs(pose_b["x"] - pose_a["x"]) > 0.005
                    or abs(pose_b["y"] - pose_a["y"]) > 0.005
                    or abs(pose_b["yaw"] - pose_a["yaw"]) > 0.0087
                ):
                    assert client.connect(), "Modbus connection failed."
                    assert mb_set_pose(
                        client, address, pose_b, byte_order, word_order
                    ), "Could not update pose of seed 0."
                    logging.debug(
                        f"seed 0 updated, x={pose_b['x']}, y={pose_b['y']}, yaw={pose_b['yaw']}"
                    )
                    pose_a = pose_b
            time.sleep(0.5)
        except (AssertionError, ConnectionException) as e:
            logging.warning(e)
            time.sleep(3)


def teach_or_set_seed(
    host,
    port,
    bits_starting_addr,
    poses_starting_addr,
    seed_num,
    byte_order,
    word_order,
):
    global pose
    bits_a = []
    bits_b = []
    # Set up the Modbus client
    client = ModbusTcpClient(host, port)

    bits_a = {}
    while True:
        try:
            assert client.connect(), "Modbus connection failed."
            if bits_a == {}:
                bits_a = mb_get_bits(
                    bits_starting_addr, seed_num, client, byte_order, word_order
                )
                assert bits_a, "Could not get seed bits_a."
            time.sleep(0.5)
            bits_b = mb_get_bits(
                bits_starting_addr, seed_num, client, byte_order, word_order
            )
            assert bits_b, "Could not get seed bits_b."
            if bits_b == bits_a:
                continue
            logging.debug(f"bits_a, length={len(bits_a)}: {bits_a}")
            logging.debug(f"bits_b, length={len(bits_b)}: {bits_b}")
            for i in range(len(bits_b)):
                # teach seed
                if not bits_a[i][2] and bits_b[i][2]:
                    # read current pose from Locator and write it to pose i in the data block
                    pose_current = pose
                    assert pose_current["localization_state"] >= 2, "NOT_LOCALIZED"
                    assert mb_set_pose(
                        client,
                        poses_starting_addr + i * 6,
                        pose_current,
                        byte_order,
                        word_order,
                    ), f"Could not set pose of seed {i}."
                    logging.info(
                        f"seed {i} taught, x={pose_current['x']}, y={pose_current['y']}, yaw={pose_current['yaw']}"
                    )
                    # reset bit teachSeed in modbus data block
                    bits_b[i][2] = False
                    logging.debug(f"bits_b, length={len(bits_b)}: {bits_b}")
                    assert mb_set_bits(
                        client,
                        bits_starting_addr,
                        bits_b,
                        byte_order,
                        word_order,
                    ), "Could not set bits."
                    break

                # set seed
                if not bits_a[i][3] and bits_b[i][3]:
                    seed_pose = mb_get_pose(
                        poses_starting_addr, i, client, byte_order, word_order
                    )
                    assert seed_pose, "Could not get pose of seed {i}."
                    session_id = sessionLogin()
                    assert session_id, "Locator client session login failed."
                    assert clientLocalizationSetSeed(
                        sessionId=session_id,
                        x=seed_pose[0],
                        y=seed_pose[1],
                        a=seed_pose[2],
                        enforceSeed=bits_b[i][0],
                        uncertainSeed=bits_b[i][1],
                    ), "Setting seed failed."
                    assert sessionLogout(
                        session_id
                    ), "Locator client session logout failed."
                    logging.info(
                        f"seed {i} set, x={seed_pose[0]}, y={seed_pose[1]}, yaw={seed_pose[2]}"
                    )
                    # reset bit setSeed in modbus data block
                    bits_b[i][3] = False
                    assert mb_set_bits(
                        client,
                        bits_starting_addr,
                        bits_b,
                        byte_order,
                        word_order,
                    ), "Could not set bits."
                    break
            # bits_b != bits_a, but no changing from False to True
            bits_a = bits_b
        except (AssertionError, ConnectionException) as e:
            logging.warning(e)
            time.sleep(3)


def mb_get_pose(poses_starting_addr, i, client, byte_order, word_order):
    try:
        rr = client.read_holding_registers(poses_starting_addr + i * 6, 6)
    except ModbusException as exc:
        print(f"Received ModbusException({exc}) from library")
        return False
    if rr.isError():  # pragma no cover
        print(f"Received Modbus library error({rr})")
        return False
    if isinstance(rr, ExceptionResponse):  # pragma no cover
        print(f"Received Modbus library exception ({rr})")
        # THIS IS NOT A PYTHON EXCEPTION, but a valid modbus message
        return False
    decoder = BinaryPayloadDecoder.fromRegisters(
        rr.registers, byteorder=byte_order, wordorder=word_order
    )
    pose_x = decoder.decode_32bit_float()
    pose_y = decoder.decode_32bit_float()
    pose_yaw = decoder.decode_32bit_float()
    return [pose_x, pose_y, pose_yaw]


def mb_set_pose(client, address, pose, byte_order, word_order):
    builder = BinaryPayloadBuilder(byteorder=byte_order, wordorder=word_order)
    builder.add_32bit_float(pose["x"])
    builder.add_32bit_float(pose["y"])
    builder.add_32bit_float(pose["yaw"])
    registers = builder.to_registers()
    try:
        rr = client.write_registers(address, registers)
    except ModbusException as exc:
        print(f"Received ModbusException({exc}) from library")
        return False
    if rr.isError():  # pragma no cover
        print(f"Received Modbus library error({rr})")
        return False
    if isinstance(rr, ExceptionResponse):  # pragma no cover
        print(f"Received Modbus library exception ({rr})")
        # THIS IS NOT A PYTHON EXCEPTION, but a valid modbus message
        return False
    return True


def mb_get_bits(bits_starting_addr, seed_num, client, byte_order, word_order):
    bits_list = []
    bits = BitArray()
    bits_register_count = math.ceil(seed_num * 4 / 16)
    try:
        rr = client.read_holding_registers(bits_starting_addr, bits_register_count)
    except ModbusException as exc:
        print(f"Received ModbusException({exc}) from library")
        return False
    if rr.isError():  # pragma no cover
        print(f"Received Modbus library error({rr})")
        return False
    if isinstance(rr, ExceptionResponse):  # pragma no cover
        print(f"Received Modbus library exception ({rr})")
        # THIS IS NOT A PYTHON EXCEPTION, but a valid modbus message
        return False

    # decoder = BinaryPayloadDecoder.fromRegisters(
    #     result.registers, byteorder=byte_order, wordorder=word_order
    # )
    for register in rr.registers:
        bit_16 = BitArray(uint=register, length=16)
        bit_16.reverse()
        bits.append(bit_16)
    for bit_4 in bits.cut(4):
        bit_4_list = [bit == "1" for bit in bit_4.bin]
        bits_list.append(bit_4_list)
    # logging.debug(bits_list)
    # for i in range(math.ceil(seed_num*4/8)):
    #     t = decoder.decode_bits()
    #     # make a list of [enforceSeed, uncertainSeed, teachSeed, setSeed]
    #     bits.append(t[:4])
    #     bits.append(t[4:])
    return bits_list


def mb_set_bits(client, bits_starting_addr, bits_list, byte_order, word_order):
    """_summary_

    Args:
        bits_starting_addr (uint): _description_
        bits_list (list): a two-dimentional array
        client (ModbusTcpClient): _description_
    """
    bool_list = [item for sublist in bits_list for item in sublist]
    bits = BitArray()
    for bool_val in bool_list:
        bits.append("0b1" if bool_val else "0b0")
    builder = BinaryPayloadBuilder(byteorder=byte_order, wordorder=word_order)
    for bits_16 in bits.cut(16):
        bits_16.reverse()
        builder.add_16bit_uint(bits_16.uint)
    registers = builder.to_registers()
    try:
        # TODO any return?
        rr = client.write_registers(bits_starting_addr, registers)
    except ModbusException as exc:
        print(f"Received ModbusException({exc}) from library")
        # client.close()
        return False
    if rr.isError():  # pragma no cover
        print(f"Received Modbus library error({rr})")
        # client.close()
        return False
    if isinstance(rr, ExceptionResponse):  # pragma no cover
        print(f"Received Modbus library exception ({rr})")
        # THIS IS NOT A PYTHON EXCEPTION, but a valid modbus message
        # client.close()
        return False
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="a program to teach and set seeds for ROKIT Locator",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "-c",
        "--config",
        type=str,
        help="Configuration file with path",
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
    parser.add_argument(
        "--byte_order",
        type=str,
        default=config["byte_order"],
        help="< Endian.Little, > Endian.Big",
    )
    parser.add_argument(
        "--word_order",
        type=str,
        default=config["word_order"],
        help="< Endian.Little, > Endian.Big",
    )
    parser.add_argument(
        "--debug",
        type=int,
        default=config["debug"],
        help="0: logging.INFO, 1: logging.DEBUG",
    )
    parser.print_help()

    args = parser.parse_args()
    # config.json has the highest priority and it will overide other command-line arguments
    if args.config:
        with open(args.config, "r") as f:
            config.update(json.load(f))
    else:
        config.update(vars(args))

    print(config)

    url = (
        "http://" + config["locator_host"] + ":" + str(config["locator_json_rpc_port"])
    )

    # format = "%(asctime)s [%(levelname)s] %(threadName)s %(message)s"
    format = "%(asctime)s [%(levelname)s] %(funcName)s(), %(message)s"
    logging.basicConfig(
        format=format,
        level=logging.DEBUG if config["debug"] else logging.INFO,
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    x1 = threading.Thread(
        target=get_client_localization_pose,
        args=(
            config["locator_host"],
            config["locator_pose_port"],
        ),
    )
    x2 = threading.Thread(
        target=update_seed_0,
        args=(
            config["plc_host"],
            config["plc_port"],
            config["poses_starting_addr"],
            config["byte_order"],
            config["word_order"],
        ),
    )
    x3 = threading.Thread(
        target=teach_or_set_seed,
        args=(
            config["plc_host"],
            config["plc_port"],
            config["bits_starting_addr"],
            config["poses_starting_addr"],
            config["seed_num"],
            config["byte_order"],
            config["word_order"],
        ),
    )
    x1.start()
    x2.start()
    x3.start()
    x1.join()
    x2.join()
    x3.join()
