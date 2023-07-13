# Use specific version of python on different versions of Ubuntu, otherwise issues may arise. 
# I have tried Python 3.11.0rc1 on Ubuntu 22.04, and there was a ModuleNotFoundError, No module named 'bitstring'
# on Ubuntu 22.04
python3.10 -m venv venv
# on Ubuntu 18.04
python3.8 -m venv venv

source venv/bin/activate
python -m pip install -U pip
pip install -r requirements_modbus.txt
pip install pyinstaller
pyinstaller seed_modbus.py --onefile
./dist/seed_modbus -c config.json