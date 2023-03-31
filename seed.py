#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# File: seed.py
# Created On: 2023-03-27
# Copyright (c) 2023 Shanghai Bosch Rexroth Hydraulics & Automation Ltd.
#

import socket
import sys
import struct
import argparse
from datetime import datetime
import time
import requests
import snap7
from signal import signal, SIGINT
import logging
logger = logging.getLogger(__name__)

now = datetime.now()
date_time = now.strftime("%d-%m-%Y-%H-%M-%S")

# Locator
LOCATOR_ADDRESS = '127.0.0.1'
LOCATOR_BINARY_PORT = 9011

LOCATOR_JSON_RPC_PORT = 8080
URL = 'http://'+LOCATOR_ADDRESS+':' + str(LOCATOR_JSON_RPC_PORT)

# ClientLocalizationPoseDatagram data structure (see API manual)
UNPACKER = struct.Struct('<ddQiQQddddddddddddddQddd')
print(datetime.now())

sessionId = ''  # ROKIT Locator JSON RPC session ID

# Siemens S7-1200
PLC_ADDRESS = "192.168.8.21"
PLC_RACK = 0
PLC_SLOT = 1
PLC_PORT = 102
seed_num = 8 # number of seeds stored in DB
DB_NUMBER = 1 # Siemens S7 data block number
ROW_SIZE = 28 # bytes that a row/seed resides
POSE_SIZE = 24 # bytes that Pose2D resides in a row/seed
# row/seed specification in a data block
layout = """
0.0     enforceSeed         BOOL
0.1     uncertainSeed       BOOL
2       x                   LREAL
10      y                   LREAL
18      a                   LREAL
26.0    recordSeed          BOOL
26.1    setSeed             BOOL
"""


def readCurrentPoseFromLocator() -> dict:
    # Creating a TCP/IP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Connecting to the server
    server_address = (LOCATOR_ADDRESS, LOCATOR_BINARY_PORT)

    print('connecting to Locator %s : %s ...' % (server_address))
    try:
        sock.connect(server_address)
        print('Connected.')
    except socket.error as e:
        print(str(e.message))
        print('Connection to Locator failed...')
        return

    # read the socket
    data = sock.recv(UNPACKER.size)
    # upack the data (= interpret the datagram)
    unpacked_data = UNPACKER.unpack(data)
    # print(unpacked_data)

    # create a json row
    jsonRow = {
        'timestamp': datetime.fromtimestamp(unpacked_data[1]).strftime("%d-%m-%Y-%H-%M-%S"), 
        'x': unpacked_data[6], 
        'y': unpacked_data[7],
        # 'yaw': math.degrees(unpacked_data[8]), 
        'yaw': unpacked_data[8], 
        'localization_state': unpacked_data[3]
        }
    sock.close()
    # print(jsonRow)
    return jsonRow


def setSeedJsonRpc(sessionId: str, x: float, y: float, a: float, enforceSeed: bool = False, uncertainSeed: bool = False):
    headers = {
        'Content-Type': 'application/json; charset=utf-8',
    }

    payload = {
        "id": 111,
        "jsonrpc": "2.0",
        "method": "clientLocalizationSetSeed",
        "params": {
            "query": {
                "sessionId": sessionId,
                "enforceSeed": enforceSeed,
                "uncertainSeed": uncertainSeed,
                "seedPose": {
                    "x": x,
                    "y": y,
                    "a": a
                }
            }
        }
    }

    print(f"x={x}, y={y}, a={a}")
    response = requests.post(url=URL, json=payload, headers=headers)
    # print(response.json())


def sessionLogin() -> str:
    headers = {
        'Content-Type': 'application/json; charset=utf-8',
    }

    payload = {
        "id": 101,
        "jsonrpc": "2.0",
        "method": "sessionLogin",
        "params": {
            "query": {
                "timeout": { # timeout, not timestamp
                    "valid": True,
                    "time": 60, # Integer64
                    "resolution": 1 # real_time = time / resolution
                },
                "userName": "admin",
                "password": "bbZGs3wFsB35"
            }
        }
    }
    # print(payload)

    response = requests.post(url=URL, json=payload, headers=headers)
    # print(response.json())
    sessionId = response.json()['result']['response']['sessionId']

    return sessionId


def sessionLogout(sessionId: str = None):
    headers = {
        'Content-Type': 'application/json; charset=utf-8',
    }

    payload = {
        "id": 103,
        "jsonrpc": "2.0",
        "method": "sessionLogout",
        "params": {
            "query": {
                "sessionId": sessionId
            }
        }
    }

    response = requests.post(url=URL, json=payload, headers=headers)
    # print(response.json())


def run():
    client = snap7.client.Client()
    client.connect(PLC_ADDRESS, PLC_RACK, PLC_SLOT, PLC_PORT)
    all_data_a = client.db_read(1, 0, ROW_SIZE*seed_num)
    db1_a = snap7.util.DB(
        db_number=DB_NUMBER,
        bytearray_=all_data_a,
        specification=layout,
        row_size=ROW_SIZE,
        size=seed_num
    )
    seed_a = db1_a.export()

    while True:
        time.sleep(0.5)

        all_data_b = client.db_read(1, 0, ROW_SIZE*seed_num)
        db1_b = snap7.util.DB(
            db_number=DB_NUMBER,
            bytearray_=all_data_b,
            specification=layout,
            row_size=ROW_SIZE,
            size=seed_num
        )
        seed_b = db1_b.export()
        for i in range(seed_num):
            if (not seed_a[i]['recordSeed'] and seed_b[i]['recordSeed']):
                # # pose 0 in DB stores current pose
                # # write pose 0 to pose i in the data block
                # client.db_write(
                #     db_number=1,
                #     start=i*ROW_SIZE+2,
                #     data=all_data_b[2:2+POSE_SIZE]  # Pose2D in the data block
                # )

                # read current pose from Locator and write it to pose i in the data block
                pose = readCurrentPoseFromLocator()
                assert(pose["localization_state"] >= 2), "NOT_LOCALIZED"
                print("LOCALIZED")
                print(pose)
                                
                pose_ba = struct.pack('>ddd', pose['x'], pose['y'], pose['yaw'])
                client.db_write(
                    db_number=1,
                    start=i*ROW_SIZE+2,
                    # data=pose_ba+bytearray([0b00000000])
                    data=pose_ba
                )

                # reset recordSeed
                client.db_write(
                    db_number=1,
                    start=i*ROW_SIZE+2+POSE_SIZE,
                    data=bytearray([0b00000000])
                )
                # client.wait_as_completion(5000)
                print(f"Seed {i} recorded.")
                break
            if (not seed_a[i]['setSeed'] and seed_b[i]['setSeed']):
                setSeed(x=seed_b[i]['x'], 
                        y=seed_b[i]['y'], 
                        a=seed_b[i]['a'],
                        enforceSeed=seed_b[i]['enforceSeed'],
                        uncertainSeed=seed_b[i]['uncertainSeed'])
                print(f"Seed {i} set.")

                client.db_write(
                    db_number=1,
                    start=i*ROW_SIZE+2+POSE_SIZE,
                    data=bytearray([0b00000000])
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
    print(sessionId)
    setSeedJsonRpc(sessionId=sessionId, x=x, y=y, a=a, 
                   enforceSeed=enforceSeed, 
                   uncertainSeed=uncertainSeed)
    sessionLogout(sessionId)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
    description='works as a protocol converter between Siemens S7-1200 and ROKIT Locator', formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seed_num", type=int,
                        default=seed_num, help="number of seeds")
    parser.add_argument("--plc_address", type=str,
                        default=PLC_ADDRESS, help="IP address of PLC")
    parser.add_argument("--plc_port", type=int,
                        default=PLC_PORT, help="port of PLC")
    parser.add_argument("--locator_address", type=str,
                        default=LOCATOR_ADDRESS, help="address of Locator")
    parser.add_argument("--locator_binary_port", type=int,
                        default=LOCATOR_BINARY_PORT, help="binary port of Locator")
    parser.add_argument("--locator_json_rpc_port", type=int,
                    default=LOCATOR_JSON_RPC_PORT, help="JSON RPC port of Locator")

    args = parser.parse_args()
    if args.seed_num:
        seed_num = args.seed_num
    if args.plc_address:
        PLC_ADDRESS = args.plc_address
    if args.plc_port:
        r = range(1, 65535)
        if args.plc_port not in r:
            raise argparse.ArgumentTypeError('Value has to be between 1 and 65535')
        PLC_PORT = args.plc_port
    logger.info(f"PLC address: {PLC_ADDRESS}")
    logger.info(f"PLC port: {PLC_PORT}")
    print("Locator host address: " + LOCATOR_ADDRESS)
    print("Locator bianry port: " + str(LOCATOR_BINARY_PORT))
    
    while True:
        try:
            time.sleep(0.5) # give 0.5s for the KeyboardInterrupt to be caught
            run()
        except KeyboardInterrupt:
            # press ctrl+c to stop the program            
            sys.exit("The program exits as you press ctrl+c.")
        except Exception as e:
            print(sys.exc_info())
            logger.exception(e)
            print("Some exceptions arise. Restart run()...")
        # finally:
