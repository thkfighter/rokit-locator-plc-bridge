#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# File: seed.py
# Created On: 2023-06-18
# Copyright (c) 2023 Shanghai Bosch Rexroth Hydraulics & Automation Ltd.
#

import socket
import sys
import struct
import argparse
from datetime import datetime
import time
import logging
import requests
# import snap7
import sqlite3
import PySimpleGUI as sg

logger = logging.getLogger(__name__)

now = datetime.now()
date_time = now.strftime("%d-%m-%Y-%H-%M-%S")

# Locator
user_name = "admin"
password = "123456"
locator_ip = '127.0.0.1'
locator_pose_port = 9011

locator_json_rpc_port = 8080
url = 'http://'+locator_ip+':' + str(locator_json_rpc_port)

# ClientLocalizationPoseDatagram data structure (see API manual)
unpacker = struct.Struct('<ddQiQQddddddddddddddQddd')
print(datetime.now())

id = 0
session_id = ''  # ROKIT Locator JSON RPC session ID


def client_localization_pose() -> dict:
    # Creating a TCP/IP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Connecting to the server
    server_address = (locator_ip, locator_pose_port)

    print('connecting to Locator %s : %s ...' % (server_address))
    try:
        sock.connect(server_address)
        print('Connected.')
    except socket.error as e:
        print(str(e.message))
        print('Connection to Locator failed...')
        return

    # read the socket
    data = sock.recv(unpacker.size)
    # upack the data (= interpret the datagram)
    unpacked_data = unpacker.unpack(data)
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


def clientLocalizationSetSeed(id, sessionId: str, x: float, y: float, a: float, enforceSeed: bool = False, uncertainSeed: bool = False):
    headers = {
        'Content-Type': 'application/json; charset=utf-8',
    }

    payload = {
        "id": id,
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
    id = id + 1

    print(f"x={x}, y={y}, a={a}")
    response = requests.post(url=url, json=payload, headers=headers)
    # print(response.json())


def sessionLogin(id) -> str:
    headers = {
        'Content-Type': 'application/json; charset=utf-8',
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
                    "resolution": 1  # real_time = time / resolution
                },
                "userName": user_name,
                "password": password
            }
        }
    }
    id = id + 1

    response = requests.post(url=url, json=payload, headers=headers)
    # print(response.json())
    sessionId = response.json()['result']['response']['sessionId']

    return sessionId


def sessionLogout(id, sessionId: str = None):
    headers = {
        'Content-Type': 'application/json; charset=utf-8',
    }

    payload = {
        "id": id,
        "jsonrpc": "2.0",
        "method": "sessionLogout",
        "params": {
            "query": {
                "sessionId": sessionId
            }
        }
    }
    id = id + 1

    response = requests.post(url=url, json=payload, headers=headers)
    # print(response.json())


def run():
    # Connect to the database
    connection = sqlite3.connect('locator.db')

    # Create a cursor object
    cursor = connection.cursor()

    # Retrieve the data
    seed_a = cursor.execute("SELECT * FROM seed").fetchall()

    while True:
        time.sleep(0.5)

        seed_b = cursor.execute("SELECT * FROM seed").fetchall()

        for i in range(len(seed_b)):
            if (not seed_a[i]['teach'] and seed_b[i]['teach']):
                # read current pose from Locator and write it to pose i in the data block
                pose = client_localization_pose()
                assert (pose["localization_state"] >= 2), "NOT_LOCALIZED"
                print("LOCALIZED")
                print(pose)

                pose_ba = struct.pack(
                    '>ddd', pose['x'], pose['y'], pose['yaw'])
                client.db_write(
                    db_number=DB_NUMBER,
                    start=i*ROW_SIZE+2,
                    # data=pose_ba+bytearray([0b00000000])
                    data=pose_ba
                )

                # reset recordSeed
                client.db_write(
                    db_number=DB_NUMBER,
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
                    db_number=DB_NUMBER,
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
    clientLocalizationSetSeed(sessionId=sessionId, x=x, y=y, a=a,
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
                        default=locator_ip, help="address of Locator")
    parser.add_argument("--locator_binary_port", type=int,
                        default=locator_pose_port, help="binary port of Locator")
    parser.add_argument("--locator_json_rpc_port", type=int,
                        default=locator_json_rpc_port, help="JSON RPC port of Locator")

    args = parser.parse_args()
    if args.seed_num:
        seed_num = args.seed_num
    if args.plc_address:
        PLC_ADDRESS = args.plc_address
    if args.plc_port:
        r = range(1, 65535)
        if args.plc_port not in r:
            raise argparse.ArgumentTypeError(
                'Value has to be between 1 and 65535')
        PLC_PORT = args.plc_port
    logger.info(f"PLC address: {PLC_ADDRESS}")
    logger.info(f"PLC port: {PLC_PORT}")
    print("Locator host address: " + locator_ip)
    print("Locator bianry port: " + str(locator_pose_port))

    while True:
        try:

            time.sleep(0.5)  # give 0.5s for the KeyboardInterrupt to be caught
            run()
        except KeyboardInterrupt:
            # press ctrl+c to stop the program
            sys.exit("The program exits as you press ctrl+c.")
        except Exception as e:
            print(sys.exc_info())
            logger.exception(e)
            print("Some exceptions arise. Restart run()...")
        finally:
            # Close the cursor and connection
            cur.close()
            conn.close()
