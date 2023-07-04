# locator_plc_bridge

## 位姿初始化介绍

seed.py是ROKIT Locator位姿（坐标和方向）初始化的示例程序，主要使用Locator API的ClientLocalizationPoseDatagram和clientLocalizationSetSeed.

程序中将发送Locator的初始位姿称为seed. 一般情况下，seed不需要很精确，与实际值偏离+-0.5m和几度也可以，Locator可以推算出准确位置。

位姿初始化分两种情况，

1. 车重启后的位姿相对关机前没有变化，使用关机前最后保存的有效位姿来初始化。
2. 车重启后的位姿相对关机前发生变化，将车移动到坐标和方向已知的站点，使用此站点的坐标和车的方向来初始化车的位姿。

位姿初始化的方法：
1. 移动车辆，让它自动初始化位姿。
2. 在aXessor上手动初始化位姿。
3. 通过API clientLocalizationSetSeed.


## 数据转发
relay.py将ROKIT Locator从端口9011发出的位姿数据转发到指定端口9511，并且可以降低发送频率。此程序是用来解决西门子S7 1200 TCP通讯数据处理能力不足的问题。

## 安装教程



## 使用说明

## 文件说明

| 文件 | 说明 |
| :--- | --- |
| seed.py | seed[]存储于西门子S7 1200，PLC程序更新当前位姿到seed0. 当seed[x].teachSeed字段由0变为1时，程序通过ClientLocalizationPose读取Locator当前位姿，写入seed[x]. 当车辆重启时，操作员点击按钮，seed[x].setSeed字段由0变为1时，程序读取PLC数据块seed[x]的(x, y, yaw), 初始化车辆位姿。|
| seed_sqlite.py | seed[]存储与SQLite数据库 |
| seed_modbus.py | seed[]存储与PLC保持寄存器(holding registers), 程序通过modbus读写seed[] |
| locator.db | SQLite数据库 |
| config.json | seed*.py配置文件，通过命令行参数--config或-c传递 |
| ./cfg/modbus_slave.json | 仿真modbus从站的配置，pymodbus.simulator --json_file "./cfg/modbus_slave.json" --modbus_server server --modbus_device device_seed --http_host localhost --http_port 1889 |
| ./others/delta/dvp15mc/dvp15mc.elcx | data type seed_t and data block in Delta DVP15MC |
| ./others/modbustools | 用来自https://www.modbustools.com/的Modbus Poll和Modbus Slave仿真主站和从站，数据块定义与DVP15MC相同。mbw和msw是软件workspace文件，包含了窗口文件mbp和mbs. |
