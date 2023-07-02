import socket
import time
import struct

HOST = '192.168.8.78'  # replace with the remote host
PORT = 9011         # replace with the remote port

unpacker = struct.Struct("<ddQiQQddddddddddddddQddd")

while True:
    try:
        # create a new socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # set a timeout to prevent the socket from blocking indefinitely
        s.settimeout(5)
        # try to connect to the remote host and port
        s.connect((HOST, PORT))
        # if the connection is successful, break out of the loop
        break
    except OSError:
        # if there is a socket error, wait for 5 seconds before trying again
        print("Failed to connect. Retrying in 5 seconds...")
        time.sleep(5)

while True:
    try:
        data = s.recv(unpacker.size)
        if not data:
            continue
        unpacked_data = unpacker.unpack(data)
        # create a json row
        pose = {
            "x": unpacked_data[6],
            "y": unpacked_data[7],
            # 'yaw': math.degrees(unpacked_data[8]),
            "yaw": unpacked_data[8],
            "localization_state": unpacked_data[3],
        }
        print(pose)
    except OSError:
        # if there is a socket error, close the socket and start the loop again to try to reconnect
        s.close()
        print("Socket error. Reconnecting...")
        while True:
            try:
                # create a new socket and try to reconnect
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(5)
                s.connect((HOST, PORT))
                break
            except OSError:
                print("Failed to reconnect. Retrying in 5 seconds...")
                time.sleep(5)
