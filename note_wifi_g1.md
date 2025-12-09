# 宇树无线操控经验记录

+ 无线路由器相关经验
```
    由于小米路由器4A千兆版的路由性能较差，我们曾经测试该路由器时也发现了类似的问题：websocket容易断连。
    建议您换用性能更好的WIFI-6及以上配置路由器，WIFI热点使用仅5ghz频段，尽可能开启160mhz频带
        # https://github.com/unitreerobotics/xr_teleoperate/issues/155

    解除路由器双频合一特性，将WiFi设置为仅2.4Ghz与仅5Ghz频段。然后VR设备连接5Ghz频段热点
        # https://github.com/unitreerobotics/xr_teleoperate/issues/129

        你好，我之前使用的是中兴的路由器，后来更换成华硕的小旋风pro路由器就好了。

    无线teleop设置，teleop跑在PC2, PC2开热点或者连个无线wifi
        # https://github.com/unitreerobotics/xr_teleoperate/issues/133#issuecomment-3259154303

    用ping实时获取笔记本电脑与VR头显的时延。时延正常情况下应该小于50ms。
        # https://github.com/unitreerobotics/xr_teleoperate/issues/115

    G1 network topology
        # https://github.com/unitreerobotics/xr_teleoperate/issues/57#issuecomment-2995437255

    # 检查G1和电脑是否能连接
        在 用户电脑 上查看 IP 地址：

        ip addr  # or ifconfig
        计划用于 DDS 的那块网卡应在 192.168.123.x/24 段（与 PC1/PC2 一致）。

        用 cyclonedds ps 工具看DDS topics (pip install cyclonedds==0.10.2)

    # 官方无线路由器推荐
        # https://github.com/unitreerobotics/xr_teleoperate/wiki/Router_Device
```
+ DDS通讯相关
```
    # 官方指引：https://github.com/unitreerobotics/xr_teleoperate/wiki/CycloneDDS-and-UnitreeSDK-(zh%E2%80%90cn)

    # Domain ID, topic name, 数据类型(会生成.idl文件，不同编程语言通用)，QoS数据传输机制

    # 宇树python sdk要安装python dds: pip install cyclonedds==0.10.2 # 好像说安装这个就不需要github的cyclone c库安装了
        # 宇树python 使用from cyclonedds.xxx import xxx

    # 网络原理
        https://github.com/unitreerobotics/xr_teleoperate/wiki/CycloneDDS-and-UnitreeSDK-(zh%E2%80%90cn)#4-%E7%BD%91%E7%BB%9C%E9%85%8D%E7%BD%AE

        【底层通信】
            - 自动发现阶段：UDP 组播 (同一二层广播域内)
            - 数据传输阶段：UDP 单播 (同一 IP 子网内)

    在终端中输入cyclonedds ps，如果输出一系列机器人的话题信息，说明是正常的；如果输出为空，说明并未在局域网内订阅到dds消息：那么请检查当前开发设备是否与机器人处于同一局域网下（可使用ping 192.168.123.164等命令检查）。
    第1步正常的情况下，在终端中输入cyclonedds subscribe rt/lowstate，如果输出持续不断地机器人所有关节数据信息，说明是正常的；如果输出为空，说明存在问题。
        # https://github.com/unitreerobotics/xr_teleoperate/issues/57
```
+ PC2 相关，环境设置，ik加速
```
    # teleop 在PC2上的安装
        # https://github.com/unitreerobotics/xr_teleoperate/issues/133#issuecomment-3303005640
        # 官方指引： https://github.com/unitreerobotics/xr_teleoperate/wiki/%5BInstall%20Log%5D%20Ubuntu%20(arm)

    # ik 加速设置
        # https://github.com/unitreerobotics/xr_teleoperate/issues/120#issuecomment-3283599593

    # 限制OpenCV多线程，让data streaming更快
        # OMP_NUM_THREADS=1 python teleop_arms_and_hands.py --args
        # https://github.com/unitreerobotics/xr_teleoperate/issues/120#issuecomment-3312418484
```
