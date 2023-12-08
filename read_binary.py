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


import json
import math
from bitstring import BitArray

# from pymodbus.constants import Endian

import sys
import threading



# ClientLocalizationPoseDatagram data structure (see API manual)
# unpacker = struct.Struct("<ddQiQQddddddddddddddQddd")
unpacker =struct.Struct("<I")
# https://docs.python.org/3/library/struct.html
# print(datetime.now())


def get_client_control_mode(host, port):
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
            # unpacked_data = unpacker.unpack(data)
            
# 2-0LASEROUTPUT
# 5-3ALIGN
# 8-6REC
# 11-9LOC
# 14-12MAP
# 17-15VISUALRECORDING
# 20-18EXPANDMAP
# 31-21Unused
            # laseroutput = unpacked_data & 0x7
            # unpacked_data >> 3
            # align = unpacked_data & 0x7
            # unpacked_data >> 3
            # rec = unpacked_data & 0x7
            # unpacked_data >> 3
            # loc = unpacked_data & 0x7
            # unpacked_data >> 3
            # map = unpacked_data & 0x7
            # unpacked_data >> 3
            # visualrecording = unpacked_data & 0x7
            # unpacked_data >> 3
            # expandmap = unpacked_data & 0x7

            laseroutput = data & 0x7
            data >> 3
            align = data & 0x7
            data >> 3
            rec = data & 0x7
            data >> 3
            loc = data & 0x7
            data >> 3
            map = data & 0x7
            data >> 3
            visualrecording = data & 0x7
            data >> 3
            expandmap = data & 0x7

            bits = bitarray.bitarray(endian='little')
            bits.frombytes(data)

            print(f"LASEROUTPUT: {laseroutput}")
            print(f"ALIGN: {align}")
            print(f"REC: {rec}")
            print(f"LOC: {loc}")
            print(f"MAP: {map}")
            print(f"VISUALRECORDING: {visualrecording}")
            print(f"EXPANDMAP: {expandmap}")

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




if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="a program to parse binary data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
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


    parser.print_help()

    args = parser.parse_args()
    # config.json has the highest priority and it will overide other command-line arguments
    # if args.config:
    #     with open(args.config, "r") as f:
    #         config.update(json.load(f))
    # else:
    #     config.update(vars(args))

    # print(config)
    
    
    if args.host:
        host=args.host
    else:
        host="127.0.0.1"

    if args.port:
        port=args.port
    else:
        port = 9004


    # format = "%(asctime)s [%(levelname)s] %(threadName)s %(message)s"
    format = "%(asctime)s [%(levelname)s] %(funcName)s(), %(message)s"
    logging.basicConfig(
        format=format,
        level=logging.INFO,
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    get_client_control_mode(host,port)
