# Use specific version of python on different versions of Ubuntu, otherwise issues may arise. 
# I have tried Python 3.11.0rc1 on Ubuntu 22.04, and there was a ModuleNotFoundError, No module named 'bitstring'
# on Ubuntu 20.04 and 22.04
python3.10 -m venv venv
# on Ubuntu 18.04
python3.8 -m venv venv

source venv/bin/activate
python -m pip install -U pip
pip install -r requirements_modbus.txt
pip install pyinstaller
pyinstaller seed_modbus.py --onefile
# If an OSError of python library not found arises, you need to install python3.10-dev or python3.8-dev outside venv
# https://gitee.com/thkfighter/locator_plc_bridge/issues/I7KTMJ
sudo apt install python3.10-dev
or
sudo apt install python3.8-dev
./dist/seed_modbus -c config.json