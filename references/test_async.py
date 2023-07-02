import asyncio
import struct

unpacker = struct.Struct("<ddQiQQddddddddddddddQddd")


async def get_locator_poses(host, port):
    reader, writer = await asyncio.open_connection(
        host, port)

    # print(f'Send: {message!r}')
    # writer.write(message.encode())
    # await writer.drain()
    try:
        while True:
            data = await reader.read(unpacker.size)
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
    except:
        writer.close()
        await writer.wait_closed()

asyncio.run(get_locator_poses('localhost', 9011))
