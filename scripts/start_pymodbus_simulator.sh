source venv/bin/activate
pymodbus.simulator --json_file "./cfg/modbus_slave.json" --modbus_server server --modbus_device device_seed --http_host localhost --http_port 1889
python seed_modbus.py -c "./build/config.json"
pymodbus.console tcp --host localhost --port 5020