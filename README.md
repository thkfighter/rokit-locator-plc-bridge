[![en](https://img.shields.io/badge/lang-en-red.svg)](https://github.com/boschrexroth/rokit-locator-plc-bridge/blob/main/README.md)
[![pt-br](https://img.shields.io/badge/lang-cn-green.svg)](https://github.com/boschrexroth/rokit-locator-plc-bridge/blob/main/README.cn.md)

# 1 Localization initialization

seed*.py is a sample program for initializing localization of ROKIT Locator，mainly using Locator's interfaces ClientLocalizationPoseDatagram and clientLocalizationSetSeed.

Refer to the manuals for explanations of seed.

ROKIT_Locator_1.6.4_User_Manual.pdf

```
10.11.1 User-Supplied Initial Pose Estimates (Seed Pose)
The user can assist the ROKIT Locator Client in its initial localization or during re-localization
by providing a seed pose. This seed pose represents the current pose of the sensor, greatly
simplifying the self-localization process. To provide a seed pose, the user must first determine
the position and orientation of the client sensor through some external means. For example,
the initial pose may be known if the vehicle is powering up from a known parking position.
Sending this pose to the ROKIT Locator Client through the appropriate RPC method can greatly
reduce the amount of sensor data the ROKIT Locator Client must collect before it can localize
itself.
10.11.2 Detecting, Handling, and Resolution of Localization Errors
...
```

ROKIT_Locator_1.6.4_API_Documentation.pdf

```
ClientLocalizationSeedMessage
• “sessionId”: SessionId
• “enforceSeed”: boolean
• “uncertainSeed”: boolean (optional)
• “seedPose”: Pose2D

Pose2D
• “x”: IEEE754Double
• “y”: IEEE754Double
• “a”: IEEE754Double
```

This program covers two situations of pose initialization.

1. If the vehicle's pose remains unchanged after restart compared to the pose before shutdown, initialize localization using the last saved valid pose before shutdown.
2. If the vehicle's pose has changed after restart relative to the pose before shutdown, move the vehicle to a position with known coordinates and orientation, initialize localization using the coordinates and orientation.

Methods for localization initialization:

1. Move the vehicle to make it automatically relocate.
2. Manually set seed using aXessor.
3. Program to use the API method clientLocalizationSetSeed.

# 2 File description

| File | Description |
| :- | - |
| seed_s7.py | seed[] is stored in data block of Siemens S7 1200. seed[0] is updated by PLC program. When seed[x].teachSeed changes from 0 to 1, this python program reads current pose through method ClientLocalizationPose and writes it to seed[x].pose. When the vehicle restarts, the operator clicks a switch bound to boolean variable seed[x].setSeed and make this variable change from 0 to 1, the python program reads seed[x].pose (x, y, yaw) from the PLC data block to initialize the vehicle's localization. |
| seed_sqlite.py | seed[] is stored in a SQLite database locator.db. seed[0] is updated by this program. The logic is the same as seed_s7.py. |
| seed_modbus.py | seed[] is stored in holding registers of a general PLC. seed[0] is updated by this program. This program reads and writes seed[x] via Modbus. The logic is the same as seed_s7. |
| locator.db | SQLite database |
| config.json | seed_modbus.py configuration file，involved by command-line argument --config or -c |
| ./cfg/modbus_slave.json | configuration for simulating a Modbus slave，pymodbus.simulator --json_file "./cfg/modbus_slave.json" --modbus_server server --modbus_device device_seed --http_host localhost --http_port 1889 |
| ./others/delta/dvp15mc/dvp15mc.elcx | data type seed_t and data block in Delta PLC DVP15MC |
| ./others/modbustools | use software Modbus Poll and Modbus Slave from <https://www.modbustools.com/> to simulate Modbus master and slave, with same data block definition as DVP15MC. mbw and msw are saved workspace files，including window files mbp and mbs. |
| relay.py | This program forwards the pose data emitted by ROKIT Locator from port 9011 to port 9511, and it also allows for reducing the data transmission frequency and discarding excess data. This program is used to take care of Siemens S7 1200 for its insufficient data processing capability of TCP communication. |

# 3 Instuctions

seed*.py is intended for helping ROKIT Locator to initialize localization. The suffixe in the file name indicates where seed data is stored, as described in the above table.

Create a virtual environment
> $ python3 -m venv venv

## 3.1 seed_modbus.py

Install dependencies
> $ python3 -m pip install -r requirements_modbus.txt

Edit config.json

```
{
    "user_name" : "admin",
    "password" : "admin",
    "locator_host" : "127.0.0.1",
    "locator_pose_port" : 9011,
    "locator_json_rpc_port" : 8080,
    "plc_host": "192.168.8.71",
    "plc_port": 502,
    "bits_starting_addr": 16,
    "poses_starting_addr": 32,
    "seed_num": 16,
    "byte_order": ">",
    "word_order": "<"
}
```

| Argument | Description |
| :- | - |
| password | Locator user password. Look for the default user names and passwords in part 11.2.4 Default User Accounts of manual ROKIT_Locator_1.6.4_User_Manual.pdf. |
| locator_host | IP address of the computer with Locator client installed |
| plc_host | PLC IP |
| plc_port | PLC modbus port |
| bits_starting_addr | Starting address of holding registers for boolean variables of Locator seeds, enforceSeed, uncertainSeed, teachSeed and setSeed |
| poses_starting_addr | Starting address of holding registers for Locator seed poses |
| seed_num | Numbers of seeds stored in PLCs' holding registers |
| "byte_order": ">", "word_order": "<" | Byte order of PLC data type float32，corresponding to "Little-endian byte swap" in software Modbus Poll. |

```bash
$ python seed_modbus.py -h
usage: seed_modbus.py [-h] [-c CONFIG] [--user_name USER_NAME] [--password PASSWORD] [--locator_host LOCATOR_HOST] [--locator_pose_port LOCATOR_POSE_PORT] [--locator_json_rpc_port LOCATOR_JSON_RPC_PORT]

a program to teach and set seeds for ROKIT Locator

options:
  -h, --help            show this help message and exit
  -c CONFIG, --config CONFIG
                        The path to the configuration file
  --user_name USER_NAME
                        User name of ROKIT Locator client
  --password PASSWORD   Password of ROKIT Locator client
  --locator_host LOCATOR_HOST
                        IP of ROKIT Locator client
  --locator_pose_port LOCATOR_POSE_PORT
                        Port of binary ClientLocalizationPose
  --locator_json_rpc_port LOCATOR_JSON_RPC_PORT
                        Port of JSON RPC ROKIT Locator Client
```

## 3.2 seed_sqlite.py

seed[] is stored in table seeds of SQLite database locator.db. You can use the software dbeaver-ce to operate this database.

DDL(Data Definition Language) of table seeds in database locator.db

```
CREATE TABLE "seeds" (
 "id" INTEGER UNIQUE,
 "name" TEXT,
 "x" REAL,
 "y" REAL,
 "yaw" REAL,
 "enforceSeed" INTEGER DEFAULT 1,
 "uncertainSeed" INTEGER DEFAULT 0,
 "teachSeed" INTEGER DEFAULT 0,
 "setSeed" INTEGER DEFAULT 0,
 PRIMARY KEY("id")
);
```

Install dbeaver-ce on Ubuntu
> $ sudo snap install dbeaver-ce

## 3.3 seed_s7.py

Install dependencies
> $ python3 -m pip install -r requirements_s7.txt

# 4 Packaging

## 4.1 Using pyinstaller.

**Use specific version of python on different versions of Ubuntu, otherwise issues may arise.**

I have tried Python 3.11.0rc1 on Ubuntu 22.04, and there was a ModuleNotFoundError, No module named 'bitstring'.

If an OSError of python library not found arises, you need to install python3.10-dev or python3.8-dev outside venv.

Related issure, <https://gitee.com/thkfighter/locator_plc_bridge/issues/I7KTMJ>

[How to install python 3 on Ubuntu](https://phoenixnap.com/kb/how-to-install-python-3-ubuntu)

```bash
# on Ubuntu 20.04 and 22.04
sudo apt install python3.10-dev
python3.10 -m venv venv
# on Ubuntu 18.04
sudo apt install python3.8-dev
python3.8 -m venv venv
```

```bash
source venv/bin/activate
python -m pip install -U pip
pip install -r requirements_modbus.txt
pip install pyinstaller
pyinstaller seed_modbus.py --onefile # make one file 
./dist/seed_modbus -c config.json
```

For the executable file generated by pyinstaller, run it with arguments without python before it. When copy the executable seed_modbus to other computers, remember to allow it to execute as program.

```bash
chmod +x seed_modbus
seed_modbus -c config.json
```
## 4.2 Using cxfreeze
When running the seed_s7 executable generated by pyinstaller, an error arises, saying that snap7 cannot be found. The executable relay made by pyinstaller from relay.py works.  
[cx_Freeze](https://cx-freeze.readthedocs.io/en/latest/script.html) can turn seed_s7.py to an executalbe that works, but cannot make a single-file executable.

```bash
# on Ubuntu 20.04 and 22.04
sudo apt install python3.10-venv
python3.10 -m venv venv
source venv/bin/activate
pip install --upgrade cx_Freeze
pip install -r requirements_s7.txt
cxfreeze -c seed_s7.py --target-dir dist
```
## 4.3 Using snapcraft


# 5 Modbus simulation

```bash
source venv/bin/activate
pymodbus.simulator --json_file "./cfg/modbus_slave.json" --modbus_server server --modbus_device device_seed --http_host localhost --http_port 1889
python seed_modbus.py -c "./build/config.json"
pymodbus.console tcp --host localhost --port 5020
```
