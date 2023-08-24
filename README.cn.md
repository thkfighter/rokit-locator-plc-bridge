[![en](https://img.shields.io/badge/lang-en-red.svg)](https://github.com/boschrexroth/rokit-locator-plc-bridge/blob/main/README.md)
[![pt-br](https://img.shields.io/badge/lang-cn-green.svg)](https://github.com/boschrexroth/rokit-locator-plc-bridge/blob/main/README.cn.md)

# 1 定位初始化介绍

seed*.py是ROKIT Locator位姿（坐标和方向）初始化的示例程序，主要使用Locator API的ClientLocalizationPoseDatagram和clientLocalizationSetSeed.

关于seed的解释，参考软件手册。

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

位姿初始化分两种情况，

1. 车重启后的位姿相对关机前没有变化，使用关机前最后保存的有效位姿来初始化。
2. 车重启后的位姿相对关机前发生变化，将车移动到坐标和方向已知的站点，使用此站点的坐标和车的方向来初始化车的位姿。

位姿初始化的方法：

1. 移动车辆，让它自动初始化位姿。
2. 在aXessor上手动初始化位姿。
3. 通过API clientLocalizationSetSeed.

# 2 文件说明

| 文件 | 说明 |
| :- | - |
| seed_s7.py | seed[]存储于西门子S7 1200 data block，PLC程序更新当前位姿到seed[0]. 当seed[x].teachSeed字段由0变为1时，程序通过ClientLocalizationPose读取Locator当前位姿，写入seed[x]. 当车辆重启时，操作员点击按钮，seed[x].setSeed字段由0变为1时，程序读取PLC数据块seed[x]的(x, y, yaw), 初始化车辆位姿。 |
| seed_sqlite.py | seed[]存储在SQLite数据库。seed[0]由此程序更新。其他逻辑与seed_s7.py一样。 |
| seed_modbus.py | seed[]存储在PLC保持寄存器(holding registers), 程序通过modbus读写seed[]. seed[0]由此程序更新。其他逻辑与seed_s7.py一样。 |
| locator.db | SQLite数据库 |
| config.json | seed_modbus.py配置文件，通过命令行参数--config或-c传递 |
| ./cfg/modbus_slave.json | 仿真modbus从站的配置，pymodbus.simulator --json_file "./cfg/modbus_slave.json" --modbus_server server --modbus_device device_seed --http_host localhost --http_port 1889 |
| ./others/delta/dvp15mc/dvp15mc.elcx | data type seed_t and data block in Delta PLC DVP15MC |
| ./others/modbustools | 用来自<https://www.modbustools.com/>的Modbus Poll和Modbus Slave仿真主站和从站，数据块定义与DVP15MC相同。mbw和msw是软件workspace文件，包含了窗口文件mbp和mbs. |
| relay.py | 将ROKIT Locator从端口9011发出的位姿数据转发到指定端口9511，并且可以降低发送频率。此程序是用来解决西门子S7 1200 TCP通讯数据处理能力不足的问题。|

# 3 使用说明

seed*.py是通过ROKIT Locator API实现车辆位姿初始化的程序，根据seed存储的位置加了不同的后缀，如上表中的说明。

创建virtual environment
> $ python3 -m venv venv

## 3.1 seed_modbus.py

安装依赖
> $ python3 -m pip install -r requirements_modbus.txt

配置文件config.json

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

| 参数 | 说明 |
| :- | - |
| password | Locator用户默认密码在手册ROKIT_Locator_1.6.4_User_Manual.pdf的11.2.4 Default User Accounts. |
| locator_host | Locator client所在电脑的IP |
| plc_host | PLC IP |
| plc_port | PLC modbus port |
| bits_starting_addr | 在PLC保持寄存器存储的Locator seed状态变量（enforceSeed, uncertainSeed, teachSeed, setSeed）的起始地址 |
| poses_starting_addr | 在PLC保持寄存器存储的Locator seed pose的起始地址 |
| seed_num | 在PLC保持寄存器存储的Locator seed数量 |
| "byte_order": ">", "word_order": "<" | PLC float32字节顺序，对应Modbus Poll中的"Little-endian byte swap". |

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

seed存储在SQLite数据库locator.db的表seeds. 可以使用数据库软件dbeaver-ce来查看、编辑数据库.

数据表seeds DDL(Data Definition Language)

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

在Ubuntu上安装dbeaver-ce，
> $ sudo snap install dbeaver-ce

## 3.3 seed_s7.py

安装依赖
> $ python3 -m pip install -r requirements_s7.txt

# 4 Packaging

Package with pyinstaller.

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

# 5 Modbus simulation

```bash
source venv/bin/activate
pymodbus.simulator --json_file "./cfg/modbus_slave.json" --modbus_server server --modbus_device device_seed --http_host localhost --http_port 1889
python seed_modbus.py -c "./build/config.json"
pymodbus.console tcp --host localhost --port 5020
```
