#!/usr/bin/env python3
# coding=utf-8
# reference https://realpython.com/python-sockets/
#
# File: relay.py
# Created On: 2023-12-24
# SPDX-FileCopyrightText: Copyright (c) 2023 Shanghai Bosch Rexroth Hydraulics & Automation Ltd.
# SPDX-License-Identifier: MIT
#

import argparse
import socket
import time
import logging
import threading
import queue

frq_divisor = 3
src_host = "127.0.0.1"
src_port = 9011
# If a socket binds to an empty IP address, it means that the socket is listening on all available network interfaces.
dst_host = ""
dst_port = 9511
debug = 0

data_queue = queue.Queue(1)


def receive_data(src_host, src_port, frq_divisor, data_queue):
    while True:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as c:
                # c.settimeout(5)
                c.connect((src_host, src_port))
                logging.info(f"producer {c.getpeername()} --> {c.getsockname()}")
                count = 0
                while True:
                    data = c.recv(188)
                    count += 1
                    if count == frq_divisor:
                        if data_queue.full():
                            data_queue.get()
                        data_queue.put_nowait(data)
                        count = 0
        except KeyboardInterrupt:
            logging.exception(KeyboardInterrupt)
            return
        except OSError as e:
            logging.exception(e)
            time.sleep(3)
        except Exception as e:
            logging.exception(e)
            time.sleep(3)


def send_data(dst_host, dst_port, data_queue):
    while True:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                # s.settimeout(5)
                # Avoid bind() exception: OSError: [Errno 48] Address already in use
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind((dst_host, dst_port))
                s.listen(1)
                conn, addr = s.accept()
                with conn:
                    logging.info(f"{s.getsockname()} --> consumer {addr}")
                    while True:
                        data = data_queue.get()
                        conn.sendall(data)
        except KeyboardInterrupt:
            logging.exception(KeyboardInterrupt)
            return
        except OSError as e:
            logging.exception(e)
            time.sleep(3)
        except Exception as e:
            logging.exception(e)
            time.sleep(3)


if __name__ == "__main__":
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
    parser.add_argument(
        "--frq_divisor",
        type=int,
        default=frq_divisor,
        help="frequency divisor; frequency of outgoing bytes = frequency of incoming bytes / frq_divisor",
    )
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
    parser.add_argument(
        "--debug",
        type=int,
        default=debug,
        help="0: logging.INFO, 1: logging.DEBUG",
    )
    parser.print_help()
    args = parser.parse_args()

    if args.frq_divisor:
        frq_divisor = args.frq_divisor
    if args.src_host:
        src_host = args.src_host
    if args.src_port:
        r = range(1, 65535)
        if args.src_port not in r:
            raise argparse.ArgumentTypeError(
                "Port number has to be between 1 and 65535"
            )
        src_port = args.src_port
    if args.dst_host:
        dst_host = args.dst_host
    if args.dst_port:
        r = range(1, 65535)
        if args.dst_port not in r:
            raise argparse.ArgumentTypeError(
                "Port number has to be between 1 and 65535"
            )
        dst_port = args.dst_port
    if args.debug:
        debug = args.debug

    format = "%(asctime)s [%(levelname)s] %(funcName)s(), %(message)s"
    logging.basicConfig(
        format=format,
        level=logging.DEBUG if debug else logging.INFO,
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logging.info(f"Frequency divisor: {frq_divisor}")
    logging.info(f"Source host: {src_host}")
    logging.info(f"Source port: {src_port}")
    logging.info(f"Destination host: {dst_host}")
    logging.info(f"Destination port: {dst_port}")

    receive_thread = threading.Thread(
        target=receive_data, args=(src_host, src_port, frq_divisor, data_queue)
    )
    send_thread = threading.Thread(
        target=send_data, args=(dst_host, dst_port, data_queue)
    )

    receive_thread.start()
    send_thread.start()

    receive_thread.join()
    send_thread.join()
