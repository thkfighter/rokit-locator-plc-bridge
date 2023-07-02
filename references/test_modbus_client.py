from pymodbus.client import ModbusTcpClient
import time

host = "127.0.0.1"
port = 5020

client = ModbusTcpClient(host, port)

while True:
    # Set up the Modbus client
    if client.connect():
        print("connected")
        break
    else:
        # if there is a socket error, wait for 5 seconds before trying again
        print("Failed to connect to modbus slave. Retrying in 5 seconds...")
        time.sleep(5)
        continue
