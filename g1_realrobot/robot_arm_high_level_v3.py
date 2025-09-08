# coding=utf-8
# junwei: v1.4.0固件更新后，06/24/2025高层动作版本
# 需要我们的python sdk: https://github.com/JunweiLiang/unitree_sdk2_python

import time
from unitree_sdk2py.core.channel import ChannelPublisher, ChannelFactoryInitialize
from unitree_sdk2py.core.channel import ChannelSubscriber
from unitree_sdk2py.g1.loco.g1_loco_client import LocoClient
from unitree_sdk2py.g1.arm.g1_arm_action_client import G1ArmActionClient

# v3 添加自定义的手势动作序列
# Arm action 这里，用的是 G1 的arm service
# rt/arm_sdk topic 用于控制 上半身包括腰的DDS
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowCmd_
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowState_
from unitree_sdk2py.idl.default import unitree_hg_msg_dds__LowCmd_
from unitree_sdk2py.utils.crc import CRC
import threading
from enum import IntEnum
import logging_mp
import numpy as np
import json
import os
logger_mp = logging_mp.get_logger(__name__)

# action map from
action_map = {
    "release arm": 99, # 放下手
    "two-hand kiss": 11, # 双手飞吻
    "left kiss": 12, #  左手飞吻
    "right kiss": 13,  #  右手飞吻
    "hands up": 15,  # 双手举起来
    "clap": 17,   # 鼓掌
    "high five": 18,  # 手抬起击掌
    "hug": 19,  # 拥抱?
    "heart": 20,  # 比心
    "right heart": 21,  # 右手比心？
    "reject": 22,  # 双手交叉
    "right hand up": 23,  # 右手抬起
    "x-ray": 24,  # 奥特曼
    "face wave": 25,    #胸前挥手
    "high wave": 26,    #高举挥手
    "shake hand": 27,   #握手
}

custom_action = {
    "left_welcome": {
        "json_name": "0022_data.json",
        "start": 40,
        "end": 439
    },
    "right_welcome": {
        "json_name": "0021_data.json",
        "start": 65,
        "end": 516
    }}


class DataBuffer:
    def __init__(self):
        self.data = None
        self.lock = threading.Lock()

    def GetData(self):
        with self.lock:
            return self.data

    def SetData(self, data):
        with self.lock:
            self.data = data

class MotorState:
    def __init__(self):
        self.q = None
        self.dq = None
G1_29_Num_Motors = 35
class G1_29_LowState:
    def __init__(self):
        self.motor_state = [MotorState() for _ in range(G1_29_Num_Motors)]


class G1_Highlevel_Controller:
    def __init__(self, network_name, custom_data_path=None):

        # 用偏低的位置和速度系数，避免大扭矩输出
        self.kp = 40.0 # 60.0
        self.kd = 1.5
        # 腰部电机的刚度系数要高一些，否则转腰就会因为重心弯腰了
        self.kp_waist = 300.0
        self.kd_waist = 3.0

        # episode["data"][current_step]["states"] or episode["data"][current_step]["actions"]
        self.use_states = False

        # load the custom data first

        self.custom_action_data = {}
        for gesture in custom_action:
            episode_file = os.path.join(custom_data_path, custom_action[gesture]["json_name"])
            episode = json.load(open(episode_file, "r"))
            start = custom_action[gesture]["start"]
            end = custom_action[gesture]["end"]
            self.custom_action_data[gesture] = episode["data"][start:end]
            logger_mp.info("loaded custom gesture %s with %s steps" % (gesture, len(self.custom_action_data[gesture])))

        ChannelFactoryInitialize(0, network_name)

        # v1.4.0固件更新后，arm和loco 分开
        # 具体看https://github.com/JunweiLiang/unitree_sdk2_python/blob/master/example/g1/high_level/note_junwei.md
        self.arm_client = G1ArmActionClient()
        self.arm_client.SetTimeout(10.0)
        self.arm_client.Init()

        self.sport_client = LocoClient()
        self.sport_client.SetTimeout(10.0)
        # simply register APIs
        self.sport_client.Init()


        # for self-defined  arm  sequence
        self.lowcmd_publisher = ChannelPublisher("rt/arm_sdk", LowCmd_)
        self.lowcmd_publisher.Init()
        # create subscriber #
        self.lowstate_subscriber = ChannelSubscriber("rt/lowstate", LowState_)
        self.lowstate_subscriber.Init()
        self.lowstate_buffer = DataBuffer()

        # initialize subscribe thread
        self.subscribe_thread = threading.Thread(target=self._subscribe_motor_state)
        self.subscribe_thread.daemon = True
        self.subscribe_thread.start()

        while not self.lowstate_buffer.GetData():
            time.sleep(0.1)
            logger_mp.warning("[G1_29_ArmController] Waiting to subscribe dds...")
        logger_mp.info("[G1_29_ArmController] Subscribe dds ok.")

        self.control_dt = 1.0 / 60.0 # 60.0 fps

    def _subscribe_motor_state(self):
        while True:
            msg = self.lowstate_subscriber.Read()
            if msg is not None:
                lowstate = G1_29_LowState()
                for id in range(G1_29_Num_Motors):
                    lowstate.motor_state[id].q  = msg.motor_state[id].q
                    lowstate.motor_state[id].dq = msg.motor_state[id].dq
                self.lowstate_buffer.SetData(lowstate)
            time.sleep(0.002)

    def get_mode_machine(self):
        '''Return current dds mode machine.'''
        return self.lowstate_subscriber.Read().mode_machine

    def _ctr_arm_waist_given_seq(self, seq):
        # initialize hg's lowcmd msg
        crc = CRC()
        msg = unitree_hg_msg_dds__LowCmd_() # 默认的 lowcmd，全部零位

        # https://support.unitree.com/home/zh/G1_developer/joint_motor_sequence
        # 上面说 Joint Name (LowCmd_.mode_pr or LowState_.mode_pr == 0)
        # 名字WAIST_YAW，  WAIST_ROLL, WAIST_PITCH,
        # LowCmd_.mode_machine == 2
        msg.mode_pr = 0
        msg.mode_machine = self.get_mode_machine()

        for id in G1_29_JointArmIndex:
            msg.motor_cmd[id].mode = 1 # 1 enable, 0 disable
            msg.motor_cmd[id].kp = self.kp
            msg.motor_cmd[id].kd = self.kd

        for id in G1_29_JointWaistIndex:
            msg.motor_cmd[id].mode = 1 # 1 enable, 0 disable
            msg.motor_cmd[id].kp = self.kp_waist
            msg.motor_cmd[id].kd = self.kd_waist

        # 1: enable arm_sdk, # 0: disable arm_sdk
        msg.motor_cmd[G1_29_JointIndex.kNotUsedJoint0].q = 1.0;

        for idx, step_data in enumerate(seq):
            start_time = time.time()

            if self.use_states:
                step_data = step_data["states"]
            else:
                step_data = step_data["actions"]

            # TODO: add smooth filter, clip q target, etc. to avoid large changes?
            # get the current q and compute dq, and check velocity limit

            # left + right
            # Joint ID 1: left_shoulder_pitch_joint
            #Joint ID 2: left_shoulder_roll_joint
            #Joint ID 3: left_shoulder_yaw_joint
            #Joint ID 4: left_elbow_joint
            #Joint ID 5: left_wrist_roll_joint
            #Joint ID 6: left_wrist_pitch_joint
            #Joint ID 7: left_wrist_yaw_joint
            arm_pos = np.array(step_data["left_arm"]["qpos"] + step_data["right_arm"]["qpos"])
            waist_q = np.array(step_data["waist"]["qpos"]) # yaw roll pitch


            for idx, id in enumerate(G1_29_JointArmIndex):
                msg.motor_cmd[id].q = arm_pos[idx]
                # position control, so feedforward tau is zero.
                msg.motor_cmd[id].dq = 0.
                msg.motor_cmd[id].tau = 0.

            for idx, id in enumerate(G1_29_JointWaistIndex):
                msg.motor_cmd[id].q = waist_q[idx]
                msg.motor_cmd[id].dq = 0.
                msg.motor_cmd[id].tau = 0.

            msg.crc = crc.Crc(msg)
            self.lowcmd_publisher.Write(msg)

            current_time = time.time()
            all_t_elapsed = current_time - start_time
            sleep_time = max(0, (self.control_dt - all_t_elapsed))
            time.sleep(sleep_time)

        release_duration = 0.5  # seconds to slowly release the arm
        start_time = time.time()
        elapsed_time = 0

        # Loop for the duration of the release
        while elapsed_time < release_duration:
            elapsed_time = time.time() - start_time

            ratio = np.clip(elapsed_time / release_duration, 0.0, 1.0)

            msg.motor_cmd[G1_29_JointIndex.kNotUsedJoint0].q = 1 - ratio;
            msg.crc = crc.Crc(msg)
            self.lowcmd_publisher.Write(msg)
            # Sleep for a short duration to control the update rate (e.g., 100Hz)
            time.sleep(0.01)
        logger_mp.info("arm sdk released!")

    def left_welcome(self, ):
        # 主运控
        #self.sport_client.SetNormalWalkMode()
        #time.sleep(0.5)
        self._ctr_arm_waist_given_seq(self.custom_action_data["left_welcome"])
        time.sleep(0.1)
        self.arm_client.Init()  # 每次用了arm_sdk都需要再init这个才能再用arm service
        # 切回去走跑
        #self.sport_client.SetRunWalkMode()

    def right_welcome(self, ):
        # 主运控
        #self.sport_client.SetNormalWalkMode()
        #time.sleep(0.5)
        self._ctr_arm_waist_given_seq(self.custom_action_data["right_welcome"])
        time.sleep(0.1)
        self.arm_client.Init()  # 每次用了arm_sdk都需要再init这个才能再用arm service
        # 切回去走跑
        #self.sport_client.SetRunWalkMode()

    def wave_hand(self, turn=False):
        self.arm_client.ExecuteAction(action_map.get("high wave"))

    def low_wave_hand(self, turn=False):
        self.arm_client.ExecuteAction(action_map.get("face wave"))

    def shake_hand_up(self):
        self.arm_client.ExecuteAction(action_map.get("shake hand"))

    def release_arm(self):
        self.arm_client.ExecuteAction(action_map.get("release arm"))

    def clap(self):
        self.arm_client.ExecuteAction(action_map.get("clap"))

    def heart(self):
        self.arm_client.ExecuteAction(action_map.get("heart"))

    def hand_up(self):
        self.arm_client.ExecuteAction(action_map.get("right hand up"))

    # 走跑运控
    def set_run_walk(self):
        self.sport_client.SetRunWalkMode()
    # 主运控，更稳一点
    def set_normal_walk(self, free_waist=False):
        if free_waist:
            # 别用这个，好像会出问题
            self.sport_client.SetNormalWalkMode3DoFWaist()
        else:
            self.sport_client.SetNormalWalkMode()

    def move_forward(self):
        # vx: float, vy: float, vyaw: float, duration
        # g1的原点在骨盆pelvis 关节，x往前，y往左手，z往上
        self.sport_client.SetVelocity(1.0, 0, 0, 1.0)

    def move_backward(self):
        self.sport_client.SetVelocity(-0.3, 0, 0, 2.0)

    def move_left_lateral(self):
        self.sport_client.SetVelocity(0, 0.3, 0, 2.0)

    def move_right_lateral(self):
        self.sport_client.SetVelocity(0, -0.3, 0, 2.0)

    def move_turn_left(self):
        # vx: float, vy: float, vyaw: float, duration
        # g1的原点在骨盆pelvis 关节，x往前，y往左手，z往上
        # Yaw = +90°（正方向）
        # 表示 绕 Z 轴逆时针旋转 90°（从上往下看），也就是说：机器人往左转
        self.sport_client.SetVelocity(0, 0, 1.0, 1.6) #大概往左转90度

    def move_turn_right(self):
        # vx: float, vy: float, vyaw: float, duration
        # g1的原点在骨盆pelvis 关节，x往前，y往左手，z往上
        # Yaw = +90°（正方向）
        # 表示 绕 Z 轴逆时针旋转 90°（从上往下看），也就是说：机器人往左转
        self.sport_client.SetVelocity(0, 0, -1.0, 1.6)




class G1_29_JointArmIndex(IntEnum):
    # Left arm
    kLeftShoulderPitch = 15
    kLeftShoulderRoll = 16
    kLeftShoulderYaw = 17
    kLeftElbow = 18
    kLeftWristRoll = 19
    kLeftWristPitch = 20
    kLeftWristyaw = 21
    # Right arm
    kRightShoulderPitch = 22
    kRightShoulderRoll = 23
    kRightShoulderYaw = 24
    kRightElbow = 25
    kRightWristRoll = 26
    kRightWristPitch = 27
    kRightWristYaw = 28

class G1_29_JointWaistIndex(IntEnum):
    kWaistYaw = 12
    kWaistRoll = 13
    kWaistPitch = 14



class G1_29_JointIndex(IntEnum):
    # Left leg
    kLeftHipPitch = 0
    kLeftHipRoll = 1
    kLeftHipYaw = 2
    kLeftKnee = 3
    kLeftAnklePitch = 4
    kLeftAnkleRoll = 5

    # Right leg
    kRightHipPitch = 6
    kRightHipRoll = 7
    kRightHipYaw = 8
    kRightKnee = 9
    kRightAnklePitch = 10
    kRightAnkleRoll = 11

    kWaistYaw = 12
    kWaistRoll = 13
    kWaistPitch = 14

    # Left arm
    kLeftShoulderPitch = 15
    kLeftShoulderRoll = 16
    kLeftShoulderYaw = 17
    kLeftElbow = 18
    kLeftWristRoll = 19
    kLeftWristPitch = 20
    kLeftWristyaw = 21

    # Right arm
    kRightShoulderPitch = 22
    kRightShoulderRoll = 23
    kRightShoulderYaw = 24
    kRightElbow = 25
    kRightWristRoll = 26
    kRightWristPitch = 27
    kRightWristYaw = 28

    # not used
    kNotUsedJoint0 = 29
    kNotUsedJoint1 = 30
    kNotUsedJoint2 = 31
    kNotUsedJoint3 = 32
    kNotUsedJoint4 = 33
    kNotUsedJoint5 = 34

