import socket
import datetime
import struct


ClientLocalizationPoseDatagram = struct.Struct('<ddQiQQddddddddddddddQddd')


def getClientLocalizationPose(locator_ip, port_client_localization_pose) -> dict:
    # Creating a TCP/IP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Connecting to the server
    server_address = (locator_ip, port_client_localization_pose)

    print('connecting to Locator %s : %s ...' % (server_address))
    try:
        sock.connect(server_address)
        print('Connected.')
    except socket.error as e:
        print(str(e.message))
        print('Connection to Locator failed...')
        return

    # read the socket
    data = sock.recv(ClientLocalizationPoseDatagram.size)
    # upack the data (= interpret the datagram)
    unpacked_data = ClientLocalizationPoseDatagram.unpack(data)
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
