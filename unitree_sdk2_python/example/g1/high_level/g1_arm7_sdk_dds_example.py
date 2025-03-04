import time
import sys

from unitree_sdk2py.core.channel import ChannelPublisher, ChannelFactoryInitialize
from unitree_sdk2py.core.channel import ChannelSubscriber, ChannelFactoryInitialize
from unitree_sdk2py.idl.default import unitree_hg_msg_dds__LowCmd_
from unitree_sdk2py.idl.default import unitree_hg_msg_dds__LowState_
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowCmd_
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowState_
from unitree_sdk2py.utils.crc import CRC
from unitree_sdk2py.utils.thread import RecurrentThread
from unitree_sdk2py.comm.motion_switcher.motion_switcher_client import MotionSwitcherClient

import numpy as np

kPi = 3.141592654
kPi_2 = 1.57079632

class G1JointIndex:
    # Left leg
    LeftHipPitch = 0
    LeftHipRoll = 1
    LeftHipYaw = 2
    LeftKnee = 3
    LeftAnklePitch = 4
    LeftAnkleB = 4
    LeftAnkleRoll = 5
    LeftAnkleA = 5

    # Right leg
    RightHipPitch = 6
    RightHipRoll = 7
    RightHipYaw = 8
    RightKnee = 9
    RightAnklePitch = 10
    RightAnkleB = 10
    RightAnkleRoll = 11
    RightAnkleA = 11

    WaistYaw = 12
    WaistRoll = 13        # NOTE: INVALID for g1 23dof/29dof with waist locked
    WaistA = 13           # NOTE: INVALID for g1 23dof/29dof with waist locked
    WaistPitch = 14       # NOTE: INVALID for g1 23dof/29dof with waist locked
    WaistB = 14           # NOTE: INVALID for g1 23dof/29dof with waist locked

    # Left arm
    LeftShoulderPitch = 15
    LeftShoulderRoll = 16
    LeftShoulderYaw = 17
    LeftElbow = 18
    LeftWristRoll = 19
    LeftWristPitch = 20   # NOTE: INVALID for g1 23dof
    LeftWristYaw = 21     # NOTE: INVALID for g1 23dof

    # Right arm
    RightShoulderPitch = 22
    RightShoulderRoll = 23
    RightShoulderYaw = 24
    RightElbow = 25
    RightWristRoll = 26
    RightWristPitch = 27  # NOTE: INVALID for g1 23dof
    RightWristYaw = 28    # NOTE: INVALID for g1 23dof

    kNotUsedJoint = 29 # NOTE: Weight

class Custom:
    def __init__(self):
        self.time_ = 0.0
        self.control_dt_ = 0.02  
        self.duration_ = 3.0   
        self.counter_ = 0
        self.weight = 0.
        self.weight_rate = 0.2
        self.kp = 60.
        self.kd = 1.5
        self.dq = 0.
        self.tau_ff = 0.
        self.mode_machine_ = 0
        # 接口说明：https://support.unitree.com/home/zh/G1_developer/basic_services_interface
        self.low_cmd = unitree_hg_msg_dds__LowCmd_()  
        self.low_state = None 
        self.first_update_low_state = False
        self.crc = CRC()
        self.done = False

        # 双臂平张开的关节位置
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

    def Init(self):
        # https://support.unitree.com/home/zh/G1_developer/sport_services_interface
        # DDS 接口支持上肢控制，仅能在锁定站立、运控 1 与运控 2 中使用。（运控 1 与运控 2是啥？）
        # 用户可以根据《DDS 通信接口》与底层服务《底层服务接口》，向 rt/arm_sdk 话题发送 LowCmd 类型的消息。参照《关节电机顺序》，为上肢设置电机指令。

        # create publisher #
        self.arm_sdk_publisher = ChannelPublisher("rt/arm_sdk", LowCmd_)
        self.arm_sdk_publisher.Init()

        # create subscriber # 
        # 参考： https://support.unitree.com/home/zh/G1_developer/basic_services_interface
        self.lowstate_subscriber = ChannelSubscriber("rt/lowstate", LowState_)
        self.lowstate_subscriber.Init(self.LowStateHandler, 10)

    def Start(self):
        self.lowCmdWriteThreadPtr = RecurrentThread(
            interval=self.control_dt_, target=self.LowCmdWrite, name="control"
        )
        while self.first_update_low_state == False:
            time.sleep(1)

        if self.first_update_low_state == True:
            self.lowCmdWriteThreadPtr.Start()

    def LowStateHandler(self, msg: LowState_):
        self.low_state = msg

        if self.first_update_low_state == False:
            self.first_update_low_state = True
        
    def LowCmdWrite(self):
        self.time_ += self.control_dt_

        if self.time_ < self.duration_ :
          # [Stage 1]: set robot to zero posture
          self.low_cmd.motor_cmd[G1JointIndex.kNotUsedJoint].q =  1 # 1:Enable arm_sdk, 0:Disable arm_sdk
          for i,joint in enumerate(self.arm_joints):
            ratio = np.clip(self.time_ / self.duration_, 0.0, 1.0)

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

        elif self.time_ < self.duration_ * 3 :
          # [Stage 2]: lift arms up
          for i,joint in enumerate(self.arm_joints):
              ratio = np.clip((self.time_ - self.duration_) / (self.duration_ * 2), 0.0, 1.0)
              self.low_cmd.motor_cmd[joint].tau = 0. 
              self.low_cmd.motor_cmd[joint].q = ratio * self.target_pos[i] + (1.0 - ratio) * self.low_state.motor_state[joint].q 
              self.low_cmd.motor_cmd[joint].dq = 0. 
              self.low_cmd.motor_cmd[joint].kp = self.kp 
              self.low_cmd.motor_cmd[joint].kd = self.kd

        elif self.time_ < self.duration_ * 6 :
          # [Stage 3]: set robot back to zero posture
          for i,joint in enumerate(self.arm_joints):
              ratio = np.clip((self.time_ - self.duration_*3) / (self.duration_ * 3), 0.0, 1.0)
              self.low_cmd.motor_cmd[joint].tau = 0. 
              self.low_cmd.motor_cmd[joint].q = (1.0 - ratio) * self.low_state.motor_state[joint].q
              self.low_cmd.motor_cmd[joint].dq = 0. 
              self.low_cmd.motor_cmd[joint].kp = self.kp 
              self.low_cmd.motor_cmd[joint].kd = self.kd

        elif self.time_ < self.duration_ * 7 :
          # [Stage 4]: release arm_sdk
          for i,joint in enumerate(self.arm_joints):
              ratio = np.clip((self.time_ - self.duration_*6) / (self.duration_), 0.0, 1.0)
              self.low_cmd.motor_cmd[G1JointIndex.kNotUsedJoint].q =  (1 - ratio) # 1:Enable arm_sdk, 0:Disable arm_sdk
        
        else:
            self.done = True
  
        self.low_cmd.crc = self.crc.Crc(self.low_cmd)
        self.arm_sdk_publisher.Write(self.low_cmd)

if __name__ == '__main__':

    print("WARNING: Please ensure there are no obstacles around the robot while running this example.")
    input("Press Enter to continue...")

    if len(sys.argv)>1:
        # 提供网卡interface名称
        ChannelFactoryInitialize(0, sys.argv[1])
    else:
        ChannelFactoryInitialize(0)

    custom = Custom()
    custom.Init()
    custom.Start()

    while True:        
        time.sleep(1)
        if custom.done: 
           print("Done!")
           sys.exit(-1)    
