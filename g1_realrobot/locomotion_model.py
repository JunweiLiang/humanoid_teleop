# coding=utf-8
# load Homie model and run inference whenever

import argparse
import onnxruntime as ort
import torch
import numpy as np
import time
import os

import threading
import json
import math
import copy
from enum import IntEnum
import logging_mp
logger_mp = logging_mp.get_logger(__name__)

# for visualization
import pinocchio as pin
from pinocchio.robot_wrapper import RobotWrapper
from pinocchio.visualize import MeshcatVisualizer

from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from unitree_sdk2py.core.channel import ChannelPublisher
from unitree_sdk2py.core.channel import ChannelSubscriber
from unitree_sdk2py.idl.default import unitree_hg_msg_dds__LowCmd_
from unitree_sdk2py.idl.default import unitree_hg_msg_dds__LowState_
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowCmd_
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowState_
from unitree_sdk2py.idl.std_msgs.msg.dds_ import String_
from unitree_sdk2py.utils.crc import CRC

class LocoMotionInference:
    def __init__(
            self, model_path, network_interface,
            device="cuda:0", urdf=None, hand_type=None,
            use_waist3=False,
            control_g1=True,
            sim=False,
            only_calibrate=False,
            show_freq=True,
            max_freq=60.0):

        self.device = device
        self.sim = sim
        self.show_freq = show_freq
        self.control_g1 = control_g1
        self.only_calibrate = only_calibrate
        if not self.control_g1:
            self.g1_visualizer = G1_29_Vis_WholeBody(urdf=urdf, hand_type=hand_type)
            self.hand_type = hand_type

        # 载入locomotion policy model as a function
        self.loco_policy = self._load_loco_policy(model_path)
        print("loco-motion policy loaded.")

        # 监听G1 DDS states, 转换成obs给policy, 发送DDS 控制指令
        # 监听自定义的command DDS topic, 可以用Oculus的控制器发送或者键盘发送
        self.control_agent = G1_Control_Agent(
            network_interface, use_waist3=use_waist3,
            device=device, control_g1=control_g1, sim=self.sim)
        # add obs
        self.control_agent_with_history = HistoryWrapper(self.control_agent)
        self.ctr_max_freq = max_freq # 控制频率 Hz

    def _load_loco_policy(self, path):
        loco_model = ort.InferenceSession(path)
        self.loco_model = loco_model
        def run_inference(input_tensor):
            ort_inputs = {loco_model.get_inputs()[0].name: input_tensor.cpu().numpy()}
            ort_outs = loco_model.run(None, ort_inputs)
            return torch.tensor(ort_outs[0], device=self.device)
        return run_inference

    def calibrate_robot(self):
        # 让机器人回到零位
        self.control_agent_with_history.get_obs()
        # 当前joint pos
        num_lower_dofs = self.control_agent_with_history.num_lower_dofs # 12 lower body
        joint_pos = self.control_agent_with_history.joint_pos[:num_lower_dofs]
        final_goal = np.array(
            [-0.1000,  0.0000,  0.0000,  0.3000, -0.2000,  0.0000,
            -0.1000,  0.0000, 0.0000,  0.3000, -0.2000,  0.0000], dtype=float)
        print("starting to calibrate...")
        target = joint_pos
        cal_action = np.zeros((1, num_lower_dofs))
        # 获取 一系列 PD动作目标
        target_sequence = []
        while np.max(np.abs(target - final_goal)) > 0.01:
            target -= np.clip((target - final_goal), -0.05, 0.05)
            target_sequence += [copy.deepcopy(target)]

        for target in target_sequence:
            next_target = target
            action_scale = 0.25 # 为啥除action  scale,放大4倍？

            next_target = next_target / action_scale
            cal_action[:, 0:12] = next_target

            self.control_agent_with_history.step(torch.from_numpy(cal_action))
            self.control_agent_with_history.get_obs()
            time.sleep(0.05)
        print("calibration done")
        obs = self.control_agent_with_history.reset()
        return obs

    def run(self):
        # 这个会循环控制机器人,
        self.control_agent_with_history.reset()
        obs_history = self.calibrate_robot()["obs_history"]

        try:
            while True:
                start_time = time.time()
                actions = self.loco_policy(obs_history)

                if not self.only_calibrate:
                    obs, low_cmd_targets = self.control_agent_with_history.step(actions)

                    obs_history = obs["obs_history"]

                if not self.control_g1:
                    self._show_current_targets(low_cmd_targets)

                if self.show_freq:
                    # Calculate elapsed time and frequency
                    current_time = time.time()
                    time_elapsed = current_time - start_time

                    # Avoid division by zero and calculate frequency
                    frequency = 1.0 / time_elapsed if time_elapsed > 0 else 0

                    # Print the frequency on the same line, overwriting the previous one
                    print(f"Running at: {frequency:.2f} Hz", end='\r')

                # Ensure consistent frame rate
                current_time = time.time()
                time_elapsed = current_time - start_time
                sleep_time = max(0, (1 / self.ctr_max_freq) - time_elapsed)
                time.sleep(sleep_time)
        finally:
            # finally, return to the nominal pose
            # TODO: 和teleop一起使用，teleop退出时已经 让G1手臂回0了,这里回脚？
            print("returning to zero pose..")
            obs = self.calibrate_robot()
            print("return done.")

    def _show_current_targets(self, low_cmd):
        # see visualize_arm_episodes for joint ID list
        # we map the joint states from DDS to the visualization platform (URDF/Meshcat/Pin)
        current_q = np.zeros(self.g1_visualizer.reduced_robot.model.nq, dtype=float) # 43 or 41

        for joint in G1_29_JointIndex:
            # Skip unused joints for a cleaner output
            if "NotUsed" in joint.name:
                continue
            q = low_cmd.motor_cmd[joint.value].q
            if self.hand_type == "dex3":
                current_q[G1_29_Dex3_JointIndex[joint.name].value] = q
            elif self.hand_type == "inspire1":
                current_q[G1_29_Inspire_JointIndex[joint.name].value] = q
            else:
                raise Exception("unknown hand: %s" % self.hand_type)

        self.g1_visualizer.vis.display(current_q)



class G1_Control_Agent():
    def __init__(self,
            network_interface, use_waist3=False, sim=False,
            device="cuda:0", control_g1=True):

        self.device = device
        self.control_g1 = control_g1
        self.sim = sim
        # channel factory只能 init一次
        if self.sim:
            # 仿真中测试
            ChannelFactoryInitialize(1)
        else:
            ChannelFactoryInitialize(0, network_interface)
        self.crc = CRC()

        # Homie原本腰部只用一个自由度作为观测
        self.joint_idxs = [0,1,2,3,4,5,6,7,8,9,10,11,12,15,16,17,18,19,20,21,22,23,24,25,26,27,28]
        self.default_dof_pos = np.array(
            [-0.1000,  0.0000,  0.0000,  0.3000, -0.2000,  0.0000, -0.1000,  0.0000,
            0.0000,  0.3000, -0.2000,  0.0000,  0.0000,  0.0000,  0.0000,  0.0000,
            0.0000,  0.0000,  0.0000,  0.0000,  0.0000, 0.0000,  0.0000,  0.0000,
            0.0000,  0.0000,  0.0000], dtype=float)
        # 我们训练了新的
        if use_waist3:
            self.joint_idxs = range(29)
            self.default_dof_pos = np.array(
                [-0.1000,  0.0000,  0.0000,  0.3000, -0.2000,  0.0000, -0.1000,  0.0000,
                0.0000,  0.3000, -0.2000,  0.0000,  0.0000,  0.0000,  0.0000,  0.0000,
                0.0000,  0.0000,  0.0000,  0.0000,  0.0000, 0.0000,  0.0000,  0.0000,
                0.0000,  0.0000,  0.0000, 0.0000,  0.0000], dtype=float)
        # 关节电机pd参数代码位于在“HomieDeploy/unitree_sdk2unitree_sdk2/g1_control.cpp”下的第85行
        self.Kp = [
            150, 150, 150, 300, 40, 40,      #// legs
            150, 150, 150, 300, 40, 40,      #// legs
            300, 300, 300,                   #// waist
            150, 150, 150, 100,  10, 10, 5,  #// arms
            150, 150, 150, 100,  10, 10, 5,  #// arms
        ]
        self.Kd = [
            2, 2, 2, 4, 2, 2,     #// legs
            2, 2, 2, 4, 2, 2,     #// legs
            5, 5, 5,              #// waist
            4, 4, 4, 1, 0.5, 0.5, 0.5,  #// arms
            4, 4, 4, 1, 0.5, 0.5, 0.5   #// arms
        ]
        # 如teleop -> robot_arm.py设置
        self.kp_high = 300.0
        self.kd_high = 3.0
        self.kp_low = 80.0
        self.kd_low = 3.0
        self.kp_wrist = 40.0
        self.kd_wrist = 1.5
        assert len(self.default_dof_pos) == len(self.joint_idxs)
        self.num_dofs = len(self.joint_idxs) # 27 or 29

        self.joint_pos = np.zeros(self.num_dofs)
        self.joint_vel = np.zeros(self.num_dofs)

        # 各种default
        self.num_lower_dofs = 12
        self.actions = torch.zeros(self.num_lower_dofs)
        self.gravity_vector = np.zeros(3)

        # cmd的default
        self.joint_pos_target = np.zeros(29)
        # 前馈扭矩，没有用上
        self.tauff = np.zeros(29)

        # 用于HistoryWrapper，get_obs的时候就会存储obs history
        self.num_obs = 2* self.num_dofs + 10 + 12 # 91
        self.num_history_length = 6
        self.num_envs = 1


        self.lowstate_subscriber = ChannelSubscriber("rt/lowstate", LowState_)
        self.lowstate_subscriber.Init()
        self.lowstate_buffer = DataBuffer()

        # initialize subscribe thread
        self.subscribe_motor_thread = threading.Thread(target=self._subscribe_motor_state)
        self.subscribe_motor_thread.daemon = True
        self.subscribe_motor_thread.start()
        while not self.lowstate_buffer.GetData():
            time.sleep(0.1)
            logger_mp.info("[G1_29_State] Waiting to subscribe dds...")
        logger_mp.info("[G1_29_State] Subscribe dds ok.")

        # command 用string格式
        self.cmd_subscriber = ChannelSubscriber("rt/loco_cmd", String_)
        self.cmd_subscriber.Init()
        self.cmd_buffer = DataBuffer()

        # initialize subscribe thread
        self.subscribe_cmd_thread = threading.Thread(target=self._subscribe_cmd)
        self.subscribe_cmd_thread.daemon = True
        self.subscribe_cmd_thread.start()
        # 一开始可能cmd topic还没有publish

        # 同时我们还要subscribe arm_cmd(包括手臂和腰部命令), 也是由teleop程序发布
        # 也是LowCmd_数据，只有手臂12+3腰的q有用
        self.arm_subscriber = ChannelSubscriber("rt/arm_cmd", LowCmd_)
        self.arm_subscriber.Init()
        self.arm_buffer = DataBuffer()

        # initialize subscribe thread
        self.subscribe_arm_thread = threading.Thread(target=self._subscribe_arm)
        self.subscribe_arm_thread.daemon = True
        self.subscribe_arm_thread.start()
        # 一开始可能arm topic还没有publish
        # 默认手臂就是零位的
        self.arm_buffer.SetData(self._get_default_arm_cmd())

        if self.control_g1:
            # create publisher #
            self.lowcmd_publisher = ChannelPublisher("rt/lowcmd", LowCmd_)
            self.lowcmd_publisher.Init()
        # 默认命令
        self.low_cmd = unitree_hg_msg_dds__LowCmd_()

    def _get_default_arm_cmd(self):
        # 与teleop的robot_arm.py同样设置，获取零位的手臂+腰的kp kd的默认cmd
        # default low cmd
        lowcmd = unitree_hg_msg_dds__LowCmd_()
        for joint in G1_29_ArmJointIndex:
            joint_id = joint.value
            #lowcmd.motor_cmd[joint_id].mode = 1 # 1 enable, 0 disable # 不需要这个
            if self._Is_wrist_motor(joint_id):
                lowcmd.motor_cmd[joint_id].kp = self.kp_wrist
                lowcmd.motor_cmd[joint_id].kd = self.kd_wrist
            else:
                lowcmd.motor_cmd[joint_id].kp = self.kp_low
                lowcmd.motor_cmd[joint_id].kd = self.kd_low
        return lowcmd

    def _Is_wrist_motor(self, motor_index):
        wrist_motors = [
            G1_29_JointIndex.kLeftWristRoll.value,
            G1_29_JointIndex.kLeftWristPitch.value,
            G1_29_JointIndex.kLeftWristYaw.value,
            G1_29_JointIndex.kRightWristRoll.value,
            G1_29_JointIndex.kRightWristPitch.value,
            G1_29_JointIndex.kRightWristYaw.value,
        ]
        return motor_index in wrist_motors

    def _subscribe_motor_state(self):
        while True:
            msg = self.lowstate_subscriber.Read()
            if msg is not None:
                # default low state
                lowstate = unitree_hg_msg_dds__LowState_()
                # 确认是否需要copy
                lowstate.motor_state = copy.deepcopy(msg.motor_state) # 0-28 is for G1
                lowstate.imu_state = copy.deepcopy(msg.imu_state)
                self.lowstate_buffer.SetData(lowstate)
            time.sleep(0.002)

    def _subscribe_cmd(self):
        while True:
            msg = self.cmd_subscriber.Read()
            if msg is not None:
                cmd_string = msg.data
                self.cmd_buffer.SetData(cmd_string)
            time.sleep(0.01) # 100Hz

    def _subscribe_arm(self):
        while True:
            msg = self.arm_subscriber.Read()
            if msg is not None:
                # default low cmd
                lowcmd = unitree_hg_msg_dds__LowCmd_()
                for joint in G1_29_ArmJointIndex:
                    joint_id = joint.value
                    lowcmd.motor_cmd[joint_id].q = msg.motor_cmd[joint_id].q
                    lowcmd.motor_cmd[joint_id].dq = msg.motor_cmd[joint_id].dq
                    # IK will compute and get some feed forward tau
                    lowcmd.motor_cmd[joint_id].tau = msg.motor_cmd[joint_id].tau

                    # kp kd也根据telep里发布的来
                    lowcmd.motor_cmd[joint_id].kp = msg.motor_cmd[joint_id].kp
                    lowcmd.motor_cmd[joint_id].kd = msg.motor_cmd[joint_id].kd

                self.arm_buffer.SetData(lowcmd)

            time.sleep(0.002) # 500Hz

    def reset(self):
        self.actions = torch.zeros(12)

        return self.get_obs()

    def _get_command(self):
        # default cmd

        # 0.74
        cmd = np.array([0.0, 0.0, 0.0, 0.74])

        cmd_string = self.cmd_buffer.GetData()
        if cmd_string is not None:
            try:
                cmd_json = json.loads(cmd_string)
                # 给定的cmd指令应该都是0-1.0之间
                # 类似teleop中sport_client 也是用0.2米每秒最大
                v_x = float(cmd_json["v_x"]) * 0.2
                v_y = float(cmd_json["v_y"]) * 0.2
                v_yaw = float(cmd_json["v_yaw"]) * 0.2
                height = float(cmd_json["height"])
                # height必须 1.65~0.74之间,下面就会得到0.74 ~ 0.08
                height = max(1.2, min(height, 1.65))
                height = 0.74 - 0.54 * (1.65-min(height, 1.65))*1.0/(1.65-0.91)
                # TODO: 加 filter/ value check
                cmd = np.array([v_x, v_y, v_yaw, height])

            except json.JSONDecodeError:
                logger_mp.warn("Received malformed command string. Ignoring.")

        return cmd

    def _get_robot_states(self):
        lowstate = self.lowstate_buffer.GetData()
        #motor_state = lowstate.motor_state[self.joint_idxs]
        motor_state = [lowstate.motor_state[idx] for idx in self.joint_idxs]

        joint_pos = np.zeros(len(self.joint_idxs))
        joint_vel = np.zeros(len(self.joint_idxs))
        for idx, motor in enumerate(motor_state):
            joint_pos[idx] = motor_state[idx].q
            joint_vel[idx] = motor_state[idx].dq

        imu_state = lowstate.imu_state
        """
        # Homie原本对应的imu数据, g1_control.cpp
        imu_tmp.omega = low_state.imu_state().gyroscope();
        imu_tmp.rpy = low_state.imu_state().rpy();
        imu_tmp.quat = low_state.imu_state().quaternion();
        imu_tmp.abody = low_state.imu_state().accelerometer();
        """

        body_angular_vel = imu_state.gyroscope # (3, )
        body_angular_vel = np.array(body_angular_vel)

        # get gravity vector
        rpy = np.array(imu_state.rpy)
        #R = np.eye(3)
        R = get_rotation_matrix_from_rpy(rpy)
        gravity_vector = np.dot(R.T, np.array([0, 0, -1]))

        return joint_pos, joint_vel, body_angular_vel, gravity_vector



    def get_obs(self):
        # 还有一些数据要存到self中，会更新一些变量

        # (4, )
        cmds = self._get_command()
        self.cmds = cmds
        # 不知道Homie为啥乘这个
        #self.commands[:, :] * np.array([2.0, 2.0, 0.25, 1.0])

        # 电机的q和dq, G1原本有29个，homie基础版本是用27个作为观测（减去腰的pitch roll）
        joint_pos, joint_vel, body_angular_vel, gravity_vector = self._get_robot_states()
        self.joint_pos = joint_pos
        self.joint_vel = joint_vel
        self.body_angular_vel = body_angular_vel
        self.gravity_vector = gravity_vector

        # 上一次的actions
        # 为啥是15不是12?
        actions =  torch.cat(
            (self.actions.reshape(1, -1).to(self.device),
             torch.zeros(1, 15).to(self.device)), dim=-1).to(self.device)

        # (4,) (3,) (3,) (27,) torch.Size([1, 27])
        #print(cmds.shape, body_angular_vel.shape, self.gravity_vector.shape, joint_pos.shape, actions.shape)
        ob = np.concatenate((cmds.reshape(1, -1), # 4
                             body_angular_vel.reshape(1, -1) * 0.5, # 3 # Homie为啥乘0.5?
                             self.gravity_vector.reshape(1, -1), # 3
                             (joint_pos - self.default_dof_pos).reshape(1, -1),
                             joint_vel.reshape(1, -1) * 0.05, # Homie为啥乘0.05?
                             actions.cpu().detach().numpy().reshape(1, -1)[:, :12]
                             ), axis=1)
        return torch.tensor(ob, device=self.device).float()

    def step(self, actions):
        # 为啥是clip 100?
        clip_actions = 100.
        # (12,)
        self.actions = torch.clip(actions[0:1, :], -clip_actions, clip_actions)
        actions = actions.cpu().numpy()
        # 模型输出平滑这么多？
        scaled_pos_target = actions * 0.25 + self.default_dof_pos[:12]
        # torques = (scaled_pos_target - self.dof_pos[:12]) * self.p_gains[:12]  - self.dof_vel[:12] * self.d_gains[:12]
        # torques = np.clip(torques[:12], -self.torque_limit[:12], self.torque_limit[:12])
        self.joint_pos_target[:12] = scaled_pos_target[:12]

        # 接收arm 和腰部的动作指令，一起控制G1
        arm_cmd = self.arm_buffer.GetData()

        # arm_actions = self.se.get_arm_action()
        # self.joint_pos_target[15:] = 0.#arm_actions
        # self.joint_pos_target[12] = scaled_pos_target[12] # waist
        # self.joint_pos_target[15:] = scaled_pos_target[13:]
        # self.torques[:12] = torques[:12]
        # print("torques: ", torques)
        # print("==============================================================================")
        # self.torques[15:] = torques[13:]
        #command_for_robot.q_des = self.joint_pos_target
        #command_for_robot.tau_ff = self.torques


        self.low_cmd.mode_pr = 0 # Series Control for Pitch/Roll Joints这是URDF的默认模式
        self.low_cmd.mode_machine = 0
        # 先设置腿部
        for i in range(12):
            self.low_cmd.motor_cmd[i].mode = 1 # 1:Enable, 0:Disable
            self.low_cmd.motor_cmd[i].tau = self.tauff[i] # 默认都是0
            self.low_cmd.motor_cmd[i].q = self.joint_pos_target[i]
            self.low_cmd.motor_cmd[i].dq = 0.
            self.low_cmd.motor_cmd[i].kp = self.Kp[i]
            self.low_cmd.motor_cmd[i].kd = self.Kd[i]

        for joint in G1_29_ArmJointIndex: # 12+3
            joint_id = joint.value
            self.low_cmd.motor_cmd[joint_id].mode = 1 # 1:Enable, 0:Disable
            self.low_cmd.motor_cmd[joint_id].tau = arm_cmd.motor_cmd[joint_id].tau
            self.low_cmd.motor_cmd[joint_id].q = arm_cmd.motor_cmd[joint_id].q
            self.low_cmd.motor_cmd[joint_id].dq = arm_cmd.motor_cmd[joint_id].dq
            self.low_cmd.motor_cmd[joint_id].kp = arm_cmd.motor_cmd[joint_id].kp
            self.low_cmd.motor_cmd[joint_id].kd = arm_cmd.motor_cmd[joint_id].kd

        if self.control_g1:
            # 发送指令控制G1
            self.low_cmd.crc = self.crc.Crc(self.low_cmd)
            self.lowcmd_publisher.Write(self.low_cmd)
            print(self.low_cmd)

        # 不发送指令，可以把low_cmd拿去可视化

        obs = self.get_obs()
        return obs, self.low_cmd


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


parser = argparse.ArgumentParser()
parser.add_argument("--model_path", help="locomotion policy onnx model ")
parser.add_argument("--use_waist3", action="store_true", help="homie observes 29 instead of 27 dof")
parser.add_argument("--urdf", default=None, help="need this for visualization")

parser.add_argument("--sim", action="store_true", help="read G1 states from simulation")
parser.add_argument("--no_control", action="store_true", help="visualize output control command instead of sending to G1")
parser.add_argument("--only_calibrate", action="store_true", help="only run calibration, see if G1 cmd works")
parser.add_argument("--network_interface", default=None)
parser.add_argument("--hand_type", default="dex3", help="dex3 or inspire1")
parser.add_argument("--max_freq", default=100.0, type=float, help="maximum freq")


if __name__ == "__main__":
    # 测试， 先开了G1 sim或者实机G1, 然后每次模型输出的q可视化到meshcat中
    args = parser.parse_args()
    locomotion_controller = LocoMotionInference(
        args.model_path, args.network_interface,
        device="cuda:0", urdf=args.urdf, hand_type=args.hand_type,
        use_waist3=args.use_waist3,
        control_g1=not args.no_control,
        sim=args.sim,
        only_calibrate=args.only_calibrate,
        show_freq=True,
        max_freq=args.max_freq)
    # this will block until keyboard interrupt
    locomotion_controller.run()
