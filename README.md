# locator_plc_bridge

## 介绍

seed.py是ROKIT Locator位姿（坐标和方向）初始化的示例程序，主要使用Locator API的ClientLocalizationPoseDatagram和clientLocalizationSetSeed.

程序中将发送Locator的初始位姿称为seed. 一般情况下，seed不需要很精确，与实际值偏离+-0.5m和几度也可以，Locator可以推算出准确位置。

位姿初始化分两种情况，

1. 车重启后的位姿相对关机前没有变化，使用关机前最后保存的有效位姿来初始化。
2. 车重启后的位姿相对关机前发生变化，将车移动到坐标和方向已知的站点，使用此站点的坐标和车的方向来初始化车的位姿。

位姿初始化的方法：
1. 移动车辆，让它自动初始化位姿。
2. 在aXessor上手动初始化位姿。
3. 通过API clientLocalizationSetSeed.

示例使用的PLC为西门子S7 1200. TODO

relay.py将ROKIT Locator从端口9011发出的位姿数据转发到指定端口9511，并且可以降低发送频率。

## 软件架构
软件架构说明


## 安装教程

1.  xxxx
2.  xxxx
3.  xxxx

## 使用说明

1.  xxxx
2.  xxxx
3.  xxxx

## 参与贡献

1.  Fork 本仓库
2.  新建 Feat_xxx 分支
3.  提交代码
4.  新建 Pull Request
