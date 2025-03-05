# G1 实机测试

电气接口说明: https://support.unitree.com/home/zh/G1_developer/about_G1

1. 初始连接，网络等
```

    PC2接外接显示器 (Jetson): 可把DP 1.4线的USBC接到g1的9号typec口，另外一头接显示器，重启机器，另外的typec口接鼠标键盘，用户名unitree密码123即可使用PC2。PC2和主控板是分开的，手机APP连接的是主控板的wifi;
    typec转DP没能成功，typec转HDMI可以，而且偶尔typec口还接触不良需要插拔才有显示

    网络:
        g1外接了个GL-Net-MT3000的无线路由器，有typec供电（需要5V/3A，typec口是5V/1.5A的
            有线连接g1网口后，g1的192网络可以无线访问 (PC2、PC1都在这个网络里了，还有激光雷达)
            无线路由器的管理端口改到了192.168.123.111；无线路由的网络名为precognition-g1wifi-123，密码12345Ssdlh;
            无线路由器桥接了5G路由，可以直接上外网
            已知的需要避开的ip: PC1-192.168.123.161, PC2(Jetson)-192.168.123.164, 激光雷达-192.168.123.120
            无线路由设置了DHCP ip地址为192.168.123.165 - 200, 所以新连接上这个无线网络的IP就不会和下面已知的IP冲突

        g1的网络架构图: https://support.unitree.com/home/zh/G1_developer/architecture_description

    由于连接的是5G网络，github都连接不了，需要按网上的方法修改/etc/hosts文件，才能git clone github的东西, 才能浏览器打开github.com
        这样也是偶尔能连上
```


2. realsense可视化
```
    # https://support.unitree.com/home/zh/G1_developer/depth_camera_instruction

    需要安装realsense
    # https://github.com/IntelRealSense/librealsense/blob/master/doc/installation_jetson.md

        # 可以直接 apt install，不需要git clone代码build
        # 安装完成后需要重启jetson，然后realsense-viewer可以看到


```

3. 激光雷达可视化
```
    # https://support.unitree.com/home/zh/G1_developer/lidar_Instructions

    # 无线连接路由器，livox viewer会自动remove device，有线连接才work
```

### 电机学习记录
```
    # 来自aliengo/A1电机介绍: https://www.yuque.com/ironfatty/nly1un/ygglc6

        宇树用的是永磁同步电机。步进电机只能控制目标角度，这里需要精确控制力矩
            原理：通过三个绕组电压大小和通断，实现3个永磁体构成的磁场 (定子)，可以控制 转子 的角度位置和输出力矩。这种控制方法叫做永磁同步电机的矢量控制 （Field Oriented Control, FOC）
            可以实现低转速精确控制
            能换向旋转
            行星减速器：电机是高转速低力矩，需要减速器，弄成低转速高力矩
            编码器encoder: 测量旋转角度，单圈绝对位置编码器。可能会有累计误差。双编码器可以更精确

        前馈Feedforward, 就是计算出的东西，反馈Feedback，要根据传感器进行修正
        电机需要的输入：获得当前的角度位置，当前的角速度，给定前馈力矩，期望角速度、角度，位置刚度(unit: N·m/rad)、速度刚度，计算输出力矩
            τ = τff + kp · (pdes − p) + kd · (ωdes − ω)

            力矩 Torque： (unit: N·m) 旋转力，有力臂的感念。
            位置刚度：收到外界力矩，产生的位移，位移越小，刚度越大 (unit: N·m/rad)
                位置刚度，会乘以，位置差（当前位置、目标位置），得到力矩

            位置模式(让关节在固定位置)，把前馈力矩τff、期望角速度ωdes设置为0， 得到
                τ = kp · (pdes − p) - kd ·  ω

            阻尼模式(阻抗控制，Impedance Control)，期望角速度ωdes设置为0，位置刚度为0（所以不管你位置在哪），前馈力矩也是0.
                所以当前有角速度的话，力矩输出会降速关节运动，形成阻抗力矩

                τ = - kd · ω
                就只跟速度刚度、当前的角速度有关

                模式       k_p     k_d    效果
                自由漂移模式  0   0   机器人完全跟随外力，无限制。
                低刚度模式   小值（如 10~100）    适中值（如 1~10） 柔顺跟随，但能回到目标位置。
                高阻尼模式   小值（如 10~100）    较大值（如 50~200）   缓慢恢复目标位置，适用于缓冲。
                纯力控制模式  0   适中值 仅依赖力传感器感知与外界互动。

            零力矩模式，τff为0，


            有些客户会产生误解，以为混合控制是同时控制目标位置和目标速度，即以一个特定速度到达特定位置，
                这个单靠5个参数设置是达不到的。
                如果我们要实现以上效果，需要先对轨迹进行规划，然后再离散轨迹进行控制，轨迹的斜率就是目标速度

```

### 手臂操作测试

```

    # 在PC2上，连接学校有线网后，才能git clone安装package
    # 在其他电脑上安装也一样的，要控制的时候接入192.168.123.*网段就行

        unitree@ubuntu:~/projects$ git clone https://github.com/eclipse-cyclonedds/cyclonedds
        unitree@ubuntu:~/projects/cyclonedds$ git checkout 0.10.2
        unitree@ubuntu:~/projects/cyclonedds/build$ cmake ..
        unitree@ubuntu:~/projects/cyclonedds/build$ cmake --build .
        unitree@ubuntu:~/projects/cyclonedds/build$ sudo cmake --build . --target install

        unitree@ubuntu:~/projects/cyclonedds/build$ export CYCLONEDDS_HOME=/usr/local/

        unitree@ubuntu:~/projects$ git clone https://github.com/unitreerobotics/unitree_sdk2_python

        unitree@ubuntu:~/projects/unitree_sdk2_python$ pip3 install -e .

        # 不要直接pip安装，会报错，用上面的github源码pip安装
            $ pip install unitree_sdk2py

    # 测试手臂例程，需要把PC2切换回192.168.*的网段；先ping 192.168.123.161 看看能不能ping通PC1

        # 不需要进入调试模式（开机后L1+A，然后L1+上，然后R1+X让它站直了，再按L1+上，就可以开始给arm命令）

        unitree@ubuntu:~/projects/unitree_sdk2_python$ python example/g1/high_level/g1_arm7_sdk_dds_example.py eth0

        # 手臂回零位，举起来，再回零位，然后放下
            # 给定了双臂平张开的目标电机角度
                kPi = 3.141592654   # 180度
                kPi_2 = 1.57079632  # 90 度

                # 手臂14 自由度，7自由度的手臂
                self.target_pos = [
                    0., kPi_2,  0., kPi_2, 0., 0., 0.,
                    0., -kPi_2, 0., kPi_2, 0., 0., 0.,
                    0, 0, 0
                ]
                self.arm_joints = [
                  G1JointIndex.LeftShoulderPitch,  G1JointIndex.LeftShoulderRoll,
                  G1JointIndex.LeftShoulderYaw,    G1JointIndex.LeftElbow,
                  G1JointIndex.LeftWristRoll,      G1JointIndex.LeftWristPitch,
                  G1JointIndex.LeftWristYaw,
                  G1JointIndex.RightShoulderPitch, G1JointIndex.RightShoulderRoll,
                  G1JointIndex.RightShoulderYaw,   G1JointIndex.RightElbow,
                  G1JointIndex.RightWristRoll,     G1JointIndex.RightWristPitch,
                  G1JointIndex.RightWristYaw,
                  G1JointIndex.WaistYaw,
                  G1JointIndex.WaistRoll,
                  G1JointIndex.WaistPitch
                ]
                用mujoco 打开g1 urdf查看
                    junweiliang@work_laptop:~/Desktop/projects/tennis/tennis_project$ python -m mujoco.viewer
                    拖文件进去，然后可以拉pi角度的对应关节，看看是否一致
                        projects/robot_dog_and_arm/unitree_ros/robots/g1_description/g1_29dof_with_hand_rev_1_0.urdf
            # 读代码所需
                # MotorCMD, low_cmd接口说明：https://support.unitree.com/home/zh/G1_developer/basic_services_interface
                # https://support.unitree.com/home/zh/G1_developer/sport_services_interface
                    # DDS 接口支持上肢控制，仅能在锁定站立、运控 1 与运控 2 中使用。（运控 1 与运控 2是啥？）
                    # 用户可以根据《DDS 通信接口》与底层服务《底层服务接口》，向 rt/arm_sdk 话题发送 LowCmd 类型的消息。参照《关节电机顺序》，为上肢设置电机指令。
                # 电机控制，可以参考aliengo的
                    # 电机控制详细的计算说明(来自aliengo)：https://www.yuque.com/ironfatty/nly1un/tx53dx
                    #   https://www.yuque.com/ironfatty/nly1un/ygglc6
                    """
                    对于电机的底层控制算法，唯一需要的控制目标就是输出力矩。对于机器人，我们通常需要给关节设定位置、速度和力矩，就需要对关节电机进行混合控制。
                    在关节电机的混合控制中，使用PD控制器将电机在输出位置的偏差反馈到力矩输出上：
                    tau' = tau + Kp * ( q - q' ) + Kd * ( dq - dq' )
                    其中，tau' 为电机输出力矩，q' 为电机当前角度，dq' 为电机当前角速度。
                    SDK中已经做了电机减速比的转换，客户不需要关心电机减速问题。
                    """

                    # motor cmd说明： https://support.unitree.com/home/zh/G1_developer/basic_services_interface
                    # // 关节前馈力矩 / 期望的输出力矩 / (unit: N·m)
                    self.low_cmd.motor_cmd[joint].tau = 0.
                    # 关节目标位置/ 期望的角度 / (unit: rad)
                    self.low_cmd.motor_cmd[joint].q = (1.0 - ratio) * self.low_state.motor_state[joint].q
                    # // 关节目标（角）速度 / 期望的角速度 / (unit: rad/s)
                    self.low_cmd.motor_cmd[joint].dq = 0.
                    #// 关节刚度系数/ 位置刚度 / (unit: N·m/rad)
                    self.low_cmd.motor_cmd[joint].kp = self.kp
                    # // 关节阻尼系数 / 速度刚度 (unit: N·m/(rad/s))
                    self.low_cmd.motor_cmd[joint].kd = self.kd

```

### 测试G1手臂IK
```
    # 用这个代码; 宇树文档：https://support.unitree.com/home/zh/Teleoperation
        $ git clone https://github.com/unitreerobotics/avp_teleoperate/
        $ conda install pinocchio -c conda-forge
        $ pip install meshcat
        $ pip install casadi

        # 使用 pinocchio 和 CasADi 库加载 URDF 并进行逆运动学计算，求解出到达该位姿的关节电机角度值。 meshcat 库则用于调试时在 Web 端进行可视化显示。
            # 添加了双目相机，可以在AVP中看到机器人的视野; 连接到PC2，把双目相机视觉推流到一个server，然后在另一台有线连接的主机host开client，然后在AVP中，打开浏览器观看主机上的推流

    # 直接浏览器可视化，给定一个左手的目标位置，丝滑移动过去再回来
        # 自己的代码在: https://github.com/JunweiLiang/humanoid_teleop

        (g1) junweil@home-lab:~/projects/humanoid_teleop/avp_teleoperate/teleop/robot_control$ python robot_arm_ik.py
```
