## 宇树的底层控制note

+ 关键基础知识
```
    宇树用的是永磁同步电机。步进电机只能控制目标角度，这里需要精确控制力矩
    电机需要的输入：
        当前角度位置，当前角速度，
        (Feedforward FF)前馈力矩，
        期望角度(rad)，期望角速度(rad/s)，
        位置刚度(N·m/rad)kp、速度刚度kd，(N·m/rad/s)
        计算输出力矩
        力矩 Torque： (unit: N·m) 旋转力

        电机转子实际输出扭矩(Nm) = 前馈转子扭矩(Nm)+（转子目标速度(rad/s)-转子当前速度(rad/s)）*速度Kd+（转子目标位置(rad)-转子当前位置(rad)）*位置Kp

        tau = tauff + kp * (q_target - q) + kd * (dq_target - dq)

        位置模式，把tauff=0, dq_target=0, 关节固定在某个位置。
            tau = kp*(q_target-q) - kd * dq

        阻尼模式: 期望角速度为0，位置刚度为0（不关心具体在哪）
            tau = - kd * dq # 所以当前有角速度，就会有力矩阻抗

        # 电机控制模式文档： https://support.unitree.com/home/zh/Motor_SDK_Dev_Guide/control_mode
    # 电机的文档： https://support.unitree.com/home/zh/Motor_SDK_Dev_Guide

```

+ 控制电机命令
```
    发布话题 rt/lowcmd(类型: unitree_hg::msg::dds_::LowCmd_) 控制全身关节电机（不含灵巧手）、电池等设备。

        struct LowCmd_ {
          octet mode_pr;                                         // 并联机构（脚踝和腰部）控制模式 (默认 0) 0:PR, 1:AB
          octet mode_machine;                                    // G1 型号
          unitree_hg::msg::dds_::MotorCmd_ motor_cmd[35];        // 身体所有电机控制指令
          unsigned long reserve[4];                              // 保留
          unsigned long crc;                                     // 校验和
        };


        # unitree_hg::msg::dds_::MotorCmd_ [35个]
            # 29  MotorCmd_.q 表示权重，取值范围为 [0.0, 1.0]。
            # 12 - 28 腰部与上肢电机控制参数。
        struct MotorCmd_ {
          octet mode;                                            // 电机控制模式 0:Disable, 1:Enable
          float q;                                               // 关节目标位置
          float dq;                                              // 关节目标速度
          float tau;                                             // 关节前馈力矩
          float kp;                                              // 关节刚度系数
          float kd;                                              // 关节阻尼系数
          unsigned long reserve[3];                              // 保留
        };

        motor_cmd[id].mode = motor_mode // 1:Enable, 0:Disables
        cmd.mode = 1       # 0.刹车 1.FOC模式(解锁电机)
        cmd.q = 0.0        # 转子期望位置 rad
        cmd.dq = 6.28*6.33 # 转子期望转速 rad/s
        cmd.kp = 0.0       # 位置误差比例系数
        cmd.kd = 0.01      # 转速误差比例系数
        cmd.tau = 0.0      # 转子期望前馈扭矩 N.m
```

+ 获取机器人状态
```
    # 文档： https://support.unitree.com/home/zh/G1_developer/basic_services_interface
        分 机器人 和灵巧手 状态获取
        订阅话题 rt/lowstate(类型: unitree_hg::msg::dds_::LowState_) 获取 G1 当前状态。


        # 机器人状态：unitree_hg::msg::dds_::LowState_
            struct LowState_ {
              unsigned long version[2];                              // 版本
              octet mode_pr;                                         // 并联机构（脚踝和腰部）控制模式 (默认 0) 0:PR, 1:AB
              octet mode_machine;                                    // G1 型号
              unsigned long tick;                                    // 计时器 每1ms递增
              unitree_hg::msg::dds_::IMUState_ imu_state;            // IMU 状态
              unitree_hg::msg::dds_::MotorState_ motor_state[35];    // 身体所有电机状态
              octet wireless_remote[40];                             // 宇树实体遥控器原始数据
              unsigned long reserve[4];                              // 保留
              unsigned long crc;                                     // 校验和
            };

        # IMU状态类型：unitree_hg::msg::dds_::IMUState_
        struct IMUState_ {
          float quaternion[4];                                   // 四元数 QwQxQyQz
          float gyroscope[3];                                    // 陀螺仪(角速度) omega_xyz
          float accelerometer[3];                                // 加速度 acc_xyz
          float rpy[3];                                          // 欧拉角
          short temperature;                                     // IMU 温度
        };

        # unitree_hg::msg::dds_::MotorState_ [35个]，

            struct MotorState_ {
              octet mode;                                            // 电机当前模式
              float q;                                               // 关节反馈位置 (rad)
              float dq;                                              // 关节反馈速度 (rad/s)
              float ddq;                                             // 关节反馈加速度 (rad/s^2)
              float tau_est;                                         // 关节反馈力矩
              float q_raw;                                           // 保留
              float dq_raw;                                          // 保留
              float ddq_raw;                                         // 保留
              short temperature[2];                                  // 电机温度 (外表与绕组温度)
              unsigned long sensor[2];                               // 传感器数据
              float vol;                                             // 电机端电压
              unsigned long motorstate;                              // 电机状态
              unsigned long reserve[4];                              // 保留
            };

        # 灵巧手里也有IMU? unitree_hg::msg::dds_::HandState_
        struct HandState_ {
          sequence<unitree_hg::msg::dds_::MotorState_>
            motor_state;                                         // 灵巧手所有电机状态
          unitree_hg::msg::dds_::IMUState_ imu_state;            // 灵巧手 IMU 状态
          sequence<unitree_hg::msg::dds_::PressSensorState_>
            press_sensor_state;                                  // 灵巧手压力传感器状态
          float power_v;                                         // 灵巧手电源电压
          float power_a;                                         // 灵巧手电源电流
          unsigned long reserve[2];                              // 保留
        };
```
+ 宇树的 样例解读
1. `g1/high_level/g1_arm7_sdk_dds_example.py`
```
    # 效果：手臂举起来 然后放回零位
    # 使用话题： rt/arm_sdk

        # 原理分析：代码50Hz构建对应的motor cmd（手臂7x2 + 腰3共17个joint）发送到arm_sdk，底层运控跑宇树的。
            # 每个motor cmd 前馈tau和dq都设置0， q在50Hz里计算插值。kp = 60.0, kd=1.5，纯位置控制，就行
```
2. `g1/high_level/g1_arm_action_example.py`
```
    # 这个就是使用 rt/arm 这个服务来叫机器人做挥手等写死的动作了; 同时走跑运控、主运控不需要退出
```
3. `xr_teleoperate/teleop/teleop_hand_and_arm.py`
```
    # 遥操作
    # 60Hz 循环，
        # 每次 先获取 TeleVuer的人的手pose以及dex-retarget之后的灵巧手pos
        # 以及机器人的7x2自由度 arm q和 dq
            # 给定当前 arm 14 q和dq，以及双手ee 目标位置，计算ik pose(两只手ee一起用casadi.Opti计算的)，得到sol_q，
            # 然后用sol_q和机器人数据，得到 sol_tauff (前馈力矩)
            # 然后控制机器人，使用 rt/lowcmd或者 rt/arm_sdk
            # 每个motor cmd, 用的就是上诉计算的目标位置和前馈力矩控制，dq设置为0
                # q添加了一个平滑控制
                # kp 和 kd, 对于 手腕关节/arm关节、弱关节、强关节，分别设置不同的;
                # 手腕最弱，kp=40.0,kd=1.5; 弱关节 kp=80.0,kd=3.0;强关节 kp=300.0,kd=3.0
            # 60Hz给新的命令，但是底层其实是250Hz control dt

```
