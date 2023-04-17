#!/usr/bin/env python3
# coding=utf-8
# reference https://realpython.com/python-sockets/
# 
# File: relay.py
# Created On: 2023-04-12
# Copyright (c) 2023 Shanghai Bosch Rexroth Hydraulics & Automation Ltd.
#

import argparse
import socket
import time
import sys
import logging


frq = 15
src_host = '192.168.8.12'
src_port = 9011

dst_host = ''
dst_port = 9511


# Create a custom logger
logger = logging.getLogger(__name__)

# Create handlers
c_handler = logging.StreamHandler(sys.stdout)
f_handler = logging.FileHandler('relay.log')
c_handler.setLevel(logging.INFO)
f_handler.setLevel(logging.INFO)

# Create formatters and add it to handlers
c_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
f_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
c_handler.setFormatter(c_format)
f_handler.setFormatter(f_format)

# Add handlers to the logger
logger.addHandler(c_handler)
logger.addHandler(f_handler)


# Arguments
parser = argparse.ArgumentParser(
description='works as a relay to retransmit payloads at a specific frequency', formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument("--frq", type=float,
                    default=frq, help="frequency of package relay")
parser.add_argument("--src_host", type=str,
                    default=src_host, help="IP address of source host")
parser.add_argument("--src_port", type=int,
                    default=src_port, help="port of source host")
parser.add_argument("--dst_host", type=str,
                    default=dst_host, help="IP address of destination host")
parser.add_argument("--dst_port", type=int,
                    default=dst_port, help="port of destination host")
args = parser.parse_args()
if args.frq:
    frq = args.frq
if args.src_host:
    src_host = args.src_host
if args.src_port:
    r = range(1, 65535)
    if args.src_port not in r:
        raise argparse.ArgumentTypeError('Port number has to be between 1 and 65535')
    src_port = args.src_port
if args.dst_host:
    dst_host = args.dst_host
if args.dst_port:
    r = range(1, 65535)
    if args.dst_port not in r:
        raise argparse.ArgumentTypeError('Port number has to be between 1 and 65535')
    dst_port = args.dst_port

logger.info(f"Frequency: {frq}")
logger.info(f"Destination host: {dst_host}")
logger.info(f"Destination port: {dst_port}")


# Socket instances
c = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# Avoid bind() exception: OSError: [Errno 48] Address already in use
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind((dst_host, dst_port))
s.listen(50)
logger.info(f"Listening on port {dst_port}")
tic = time.perf_counter()
t_delta = 1.0 / frq


while True:
    try:
        c.connect((src_host, src_port))
        logger.info("Source host has been connected.")
        conn, addr = s.accept()
        logger.info(f"Connected by {addr}")
        while True:
            data = c.recv(1024) # length of pose payload is 188
            if not data:
                continue
            toc = time.perf_counter()
            if (toc-tic) >= t_delta:
                conn.sendall(data)
                tic = toc
    except KeyboardInterrupt:
        # press ctrl+c to stop the program 
        c.close()
        s.close()
        # logger.info("Caught keyboard interrupt, exiting")
        logger.exception(KeyboardInterrupt)
        sys.exit("Caught keyboard interrupt, exiting")
    except Exception as e:
        logger.exception(e)
