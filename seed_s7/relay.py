#!/usr/bin/env python3
# coding=utf-8
# reference https://realpython.com/python-sockets/
#
# File: relay.py
# Created On: 2023-04-12
# SPDX-FileCopyrightText: Copyright (c) 2023 Shanghai Bosch Rexroth Hydraulics & Automation Ltd.
# SPDX-License-Identifier: MIT
#

import argparse
import socket
import time
import sys
import logging
import json
import errno


frq = 15
src_host = "127.0.0.1"
src_port = 9011

dst_host = ""  # If a socket binds to an empty IP address, it means that the socket is listening on all available network interfaces.
dst_port = 9511

format = "%(asctime)s [%(levelname)s] %(funcName)s(), %(message)s"
logging.basicConfig(
    format=format,
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)


# Arguments
parser = argparse.ArgumentParser(
    description="works as a relay to retransmit poses at a specific frequency",
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
)
# parser.add_argument(
#     "-c",
#     "--config",
#     type=str,
#     help="Configuration file with path",
# )
parser.add_argument("--frq", type=float, default=frq, help="frequency of package relay")
parser.add_argument(
    "--src_host", type=str, default=src_host, help="IP address of source host"
)
parser.add_argument(
    "--src_port", type=int, default=src_port, help="port of source host"
)
parser.add_argument(
    "--dst_host",
    type=str,
    default=dst_host,
    help="IP address of destination host. Empty by default, listening on all available network interfaces.",
)
parser.add_argument(
    "--dst_port", type=int, default=dst_port, help="port of destination host"
)
parser.print_help()
args = parser.parse_args()

if args.frq:
    frq = args.frq
if args.src_host:
    src_host = args.src_host
if args.src_port:
    r = range(1, 65535)
    if args.src_port not in r:
        raise argparse.ArgumentTypeError("Port number has to be between 1 and 65535")
    src_port = args.src_port
if args.dst_host:
    dst_host = args.dst_host
if args.dst_port:
    r = range(1, 65535)
    if args.dst_port not in r:
        raise argparse.ArgumentTypeError("Port number has to be between 1 and 65535")
    dst_port = args.dst_port

logging.info(f"Frequency: {frq}")
logging.info(f"Source host: {src_host}")
logging.info(f"Source port: {src_port}")
logging.info(f"Destination host: {dst_host}")
logging.info(f"Destination port: {dst_port}")

# Socket instances
c = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# Avoid bind() exception: OSError: [Errno 48] Address already in use
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind((dst_host, dst_port))
s.listen(1)
c.settimeout(5)
# s.settimeout(5)
conn, addr = s.accept()

tic = time.perf_counter()
t_delta = 1.0 / frq


while True:
    try:
        try:
            c.connect((src_host, src_port))
            logging.info(f"{c.getsockname()} <-- {c.getpeername()}")
        except OSError as e:
            if e.errno == errno.EISCONN:
                # print('OSError: [Errno 106] Transport endpoint is already connected')
                pass
            else:
                # Re-raise the exception
                raise

        try:
            if "conn" not in globals():
                conn, addr = s.accept()
            logging.info(f"{s.getsockname()} --> {addr}")
        except OSError as e:
            if e.errno == errno.EISCONN:
                # print('Socket is already connected')
                pass
            elif e.errno == 107:
                # print('OSError: [Errno 107] Transport endpoint is not connected')
                # Re-raise the exception
                raise
            else:
                raise

        while True:
            data = c.recv(1024)  # length of pose payload is 188
            if not data:
                continue
            toc = time.perf_counter()
            if (toc - tic) >= t_delta:
                conn.sendall(data)
                tic = toc
                # print('.')
    except KeyboardInterrupt:
        # press ctrl+c to stop the program
        c.close()
        s.close()
        # logging.info("Caught keyboard interrupt, exiting")
        logging.exception(KeyboardInterrupt)
        sys.exit("Caught keyboard interrupt, exiting")
    except OSError as e:
        logging.exception(e)
        time.sleep(3)
    except Exception as e:
        logging.exception(e)
        time.sleep(3)
