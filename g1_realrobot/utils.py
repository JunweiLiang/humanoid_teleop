# coding=utf-8
"""
    All the tedious helper functions classes here
"""
import struct
import os
import threading
import torch
import math
import numpy as np
from enum import IntEnum
# for visualization
import pinocchio as pin
from pinocchio.robot_wrapper import RobotWrapper
from pinocchio.visualize import MeshcatVisualizer
import time

class HistoryWrapper:
    def __init__(self, env):
        self.env = env

        self.obs_history_length = self.env.num_history_length
        self.num_obs_history = self.obs_history_length * self.env.num_obs
        self.obs_history = torch.zeros(self.env.num_envs, self.num_obs_history, dtype=torch.float,
                                       device=self.env.device, requires_grad=False)

    def step(self, action):
        obs, low_cmd_targets = self.env.step(action)
        self.obs_history = torch.cat((self.obs_history[:, self.env.num_obs:], obs), dim=-1)
        return {'obs': obs, 'obs_history': self.obs_history}, low_cmd_targets

    def get_obs(self):
        obs = self.env.get_obs()
        self.obs_history = torch.cat((self.obs_history[:, self.env.num_obs:], obs), dim=-1)
        return {'obs': obs, 'obs_history': self.obs_history}

    def reset(self):
        ret = self.env.reset()
        self.obs_history[:, :] = 0
        return {"obs": ret, "obs_history": self.obs_history}

    def __getattr__(self, name):
        return getattr(self.env, name)


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

def get_rotation_matrix_from_rpy(rpy):
    """
    Get rotation matrix from the given quaternion.
    Args:
        q (np.array[float[4]]): quaternion [w,x,y,z]
    Returns:
        np.array[float[3,3]]: rotation matrix.
    """
    r, p, y = rpy
    R_x = np.array([[1, 0, 0],
                    [0, math.cos(r), -math.sin(r)],
                    [0, math.sin(r), math.cos(r)]
                    ])

    R_y = np.array([[math.cos(p), 0, math.sin(p)],
                    [0, 1, 0],
                    [-math.sin(p), 0, math.cos(p)]
                    ])

    R_z = np.array([[math.cos(y), -math.sin(y), 0],
                    [math.sin(y), math.cos(y), 0],
                    [0, 0, 1]
                    ])

    rot = np.dot(R_z, np.dot(R_y, R_x))
    return rot




class UnitreeRemoteController:
    def __init__(self, height_limit=(1.0, 1.65), height_change_interval=0.5, height_change_step=0.1):
        # key
        self.Lx = 0
        self.Rx = 0
        self.Ry = 0
        self.Ly = 0

        # button
        self.L1 = 0
        self.L2 = 0
        self.R1 = 0
        self.R2 = 0
        self.A = 0
        self.B = 0
        self.X = 0
        self.Y = 0
        self.Up = 0
        self.Down = 0
        self.Left = 0
        self.Right = 0
        self.Select = 0
        self.F1 = 0
        self.F3 = 0
        self.Start = 0

        # --- Added for height control ---
        self.height_min, self.height_max = height_limit
        # Initialize height to the maximum value
        self.height = self.height_max
        # Time in seconds between height adjustments
        self.height_change_interval = height_change_interval
        self.height_change_step = height_change_step # 按一次增减多少
        # Timestamp of the last height change, initialized to 0 for immediate first press
        self.last_height_change_time = 0

    def parse_botton(self, data1, data2):
        self.R1 = (data1 >> 0) & 1
        self.L1 = (data1 >> 1) & 1
        self.Start = (data1 >> 2) & 1
        self.Select = (data1 >> 3) & 1
        self.R2 = (data1 >> 4) & 1
        self.L2 = (data1 >> 5) & 1
        self.F1 = (data1 >> 6) & 1
        self.F3 = (data1 >> 7) & 1
        self.A = (data2 >> 0) & 1
        self.B = (data2 >> 1) & 1
        self.X = (data2 >> 2) & 1
        self.Y = (data2 >> 3) & 1
        self.Up = (data2 >> 4) & 1
        self.Right = (data2 >> 5) & 1
        self.Down = (data2 >> 6) & 1
        self.Left = (data2 >> 7) & 1

    def parse_key(self, data): # 这应该是摇杆？？
        lx_offset = 4
        self.Lx = struct.unpack('<f', data[lx_offset:lx_offset + 4])[0]
        rx_offset = 8
        self.Rx = struct.unpack('<f', data[rx_offset:rx_offset + 4])[0]
        ry_offset = 12
        self.Ry = struct.unpack('<f', data[ry_offset:ry_offset + 4])[0]
        L2_offset = 16
        L2 = struct.unpack('<f', data[L2_offset:L2_offset + 4])[0] # Placeholder，unused
        ly_offset = 20
        self.Ly = struct.unpack('<f', data[ly_offset:ly_offset + 4])[0]

    def parse(self, remoteData):
        self.parse_key(remoteData)
        self.parse_botton(remoteData[2], remoteData[3])

        # --- Logic for height control ---
        current_time = time.time()

        # Check if enough time has passed since the last height change
        if current_time - self.last_height_change_time > self.height_change_interval:
            # Check Up button
            if self.Up == 1:
                # Calculate new height and ensure it doesn't exceed the max limit
                new_height = round(self.height + self.height_change_step, 2)
                if new_height <= self.height_max:
                    self.height = new_height
                    print(f"Height increased to: {self.height:.2f}")
                    # Update the time of the last change
                    self.last_height_change_time = current_time
            # Check Down button
            elif self.Down == 1:
                # Calculate new height and ensure it doesn't go below the min limit
                new_height = round(self.height - self.height_change_step, 2)
                if new_height >= self.height_min:
                    self.height = new_height
                    print(f"Height decreased to: {self.height:.2f}")
                    # Update the time of the last change
                    self.last_height_change_time = current_time

        """
         # print了一下宇树遥控器，摇杆可能都有误差
                    # 左摇杆，上下值 Ly=[0.95, -0.83], 左右值范围Lx=[-1.0, 1.0]
                    # 右摇杆，上下值 Ry=[1.0, -1.0], 左右值范围Rx=[-0.92, 0.94]
                    # 其他按键按下了就是持续是1值
        print("debug unitreeRemoteController: ")
        print("Lx:", self.Lx)
        print("Rx:", self.Rx)
        print("Ry:", self.Ry)
        print("Ly:", self.Ly)

        print("L1:", self.L1)
        print("L2:", self.L2)
        print("R1:", self.R1)
        print("R2:", self.R2)
        print("A:", self.A)
        print("B:", self.B)
        print("X:", self.X)
        print("Y:", self.Y)
        print("Up:", self.Up)
        print("Down:", self.Down)
        print("Left:", self.Left)
        print("Right:", self.Right)
        print("Select:", self.Select)
        print("F1:", self.F1)
        print("F3:", self.F3)
        print("Start:", self.Start)
        print("\n")
        """

# ----以下仅用于可视化
class G1_29_Vis_WholeBody:
    def __init__(self, urdf, hand_type="inspire1"):

        np.set_printoptions(precision=5, suppress=True, linewidth=200)

        self.robot = pin.RobotWrapper.BuildFromURDF(urdf, os.path.dirname(urdf))

        # 五指手，三指手
        assert hand_type in ["inspire1", "dex3"]

        if hand_type == "inspire1":
            self.mixed_jointsToLockIDs = [

                # 单手URDF里，12个自由度，4个手指每个2个所以8个，剩4个自由度在拇指
                # 实机单手只有6自由度，每个手指一个，拇指2个

                # 这六个是主动关节， 我们锁定其他的被动关节
                # 遥操作的时候也只有6个主动关节的数据
                #'R_thumb_proximal_yaw_joint',
                #'R_thumb_proximal_pitch_joint',
                #'R_index_proximal_joint',
                #'R_middle_proximal_joint',
                #'R_ring_proximal_joint',
                #'R_pinky_proximal_joint'

                # 左手关节
                #"L_pinky_proximal_joint",
                "L_pinky_intermediate_joint",
                #"L_ring_proximal_joint",
                "L_ring_intermediate_joint",
                "L_thumb_intermediate_joint",
                #"L_thumb_proximal_yaw_joint",
                #"L_thumb_proximal_pitch_joint",
                "L_thumb_distal_joint",
                #"L_middle_proximal_joint",
                "L_middle_intermediate_joint",
                #"L_index_proximal_joint",
                "L_index_intermediate_joint",

                # 右手关节（已更新）
                #"R_pinky_proximal_joint",
                "R_pinky_intermediate_joint",
                #"R_ring_proximal_joint",
                "R_ring_intermediate_joint",
                "R_thumb_intermediate_joint",
                #"R_thumb_proximal_yaw_joint",
                #"R_thumb_proximal_pitch_joint",
                "R_thumb_distal_joint",
                #"R_index_proximal_joint",
                "R_index_intermediate_joint",
                #"R_middle_proximal_joint",
                "R_middle_intermediate_joint"
            ]
        elif hand_type == "dex3":

            self.mixed_jointsToLockIDs = [

                # 用的宇树三指手的URDF，每个7自由度，都不用锁

            ]

        # https://docs.ros.org/en/kinetic/api/pinocchio/html/classpinocchio_1_1robot__wrapper_1_1RobotWrapper.html#aef341b27b4709b03c93d66c8c196bc0f
        # the above joint will be locked, at 0.0
        self.reduced_robot = self.robot.buildReducedRobot(
            list_of_joints_to_lock=self.mixed_jointsToLockIDs,
            reference_configuration=np.array([0.0] * self.robot.model.nq),
        )

        self.init_data = np.zeros(self.reduced_robot.model.nq)

        self.current_q = np.zeros(self.reduced_robot.model.nq) # used to save the current q

        # Initialize the Meshcat visualizer for visualization
        self.vis = MeshcatVisualizer(
            self.reduced_robot.model, self.reduced_robot.collision_model, self.reduced_robot.visual_model)
        self.vis.initViewer(open=True)
        self.vis.loadViewerModel("pinocchio")

        self.vis.display(pin.neutral(self.reduced_robot.model))
class G1_29_Dex3_JointIndex(IntEnum):
    """Enumeration for the joint indices of the G1_29_Dex3 robot."""
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

    # Waist
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
    kLeftWristYaw = 21

    # Left hand
    kLeftHandIndex0 = 22
    kLeftHandIndex1 = 23
    kLeftHandMiddle0 = 24
    kLeftHandMiddle1 = 25
    kLeftHandThumb0 = 26
    kLeftHandThumb1 = 27
    kLeftHandThumb2 = 28

    # Right arm
    kRightShoulderPitch = 29
    kRightShoulderRoll = 30
    kRightShoulderYaw = 31
    kRightElbow = 32
    kRightWristRoll = 33
    kRightWristPitch = 34
    kRightWristYaw = 35

    # Right hand
    kRightHandIndex0 = 36
    kRightHandIndex1 = 37
    kRightHandMiddle0 = 38
    kRightHandMiddle1 = 39
    kRightHandThumb0 = 40
    kRightHandThumb1 = 41
    kRightHandThumb2 = 42

class G1_29_Inspire_JointIndex(IntEnum):
    """Enumeration for the joint indices of the G1_29_Inspire robot."""
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

    # Waist
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
    kLeftWristYaw = 21

    # Left hand
    kLeftHandIndex = 22
    kLeftHandMiddle = 23
    kLeftHandPinky = 24
    kLeftHandRing = 25
    kLeftHandThumbRotation = 26
    kLeftHandThumbBend = 27

    # Right arm
    kRightShoulderPitch = 28
    kRightShoulderRoll = 29
    kRightShoulderYaw = 30
    kRightElbow = 31
    kRightWristRoll = 32
    kRightWristPitch = 33
    kRightWristYaw = 34

    # Right hand
    kRightHandIndex = 35
    kRightHandMiddle = 36
    kRightHandPinky = 37
    kRightHandRing = 38
    kRightHandThumbRotation = 39
    kRightHandThumbBend = 40

# G1 DDS LowState 35个MotorState，对应的就是下面的顺序。12-28是上肢
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
    kLeftWristYaw = 21

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

class G1_29_ArmJointIndex(IntEnum):
    # 12 + 3

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
    kLeftWristYaw = 21

    # Right arm
    kRightShoulderPitch = 22
    kRightShoulderRoll = 23
    kRightShoulderYaw = 24
    kRightElbow = 25
    kRightWristRoll = 26
    kRightWristPitch = 27
    kRightWristYaw = 28


