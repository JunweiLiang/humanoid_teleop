# coding=utf-8
# load Homie model and run inference whenever

import argparse
import onnxruntime as ort
import torch
import numpy as np
import time
import os
import sys
import struct

import threading
import json
import math
import copy
from enum import IntEnum
import logging_mp
logging_mp.basic_config(level=logging_mp.INFO)
logger_mp = logging_mp.get_logger(__name__)


from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from unitree_sdk2py.core.channel import ChannelPublisher
from unitree_sdk2py.core.channel import ChannelSubscriber
from unitree_sdk2py.idl.default import unitree_hg_msg_dds__LowCmd_
from unitree_sdk2py.idl.default import unitree_hg_msg_dds__LowState_
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowCmd_
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowState_
from unitree_sdk2py.idl.std_msgs.msg.dds_ import String_
from unitree_sdk2py.utils.crc import CRC

from unitree_sdk2py.comm.motion_switcher.motion_switcher_client import MotionSwitcherClient


# some helper stuff
from utils import UnitreeRemoteController
from utils import DataBuffer, HistoryWrapper
from utils import get_rotation_matrix_from_rpy
from utils import G1_29_JointIndex, G1_29_ArmJointIndex
from utils import SimpleFPSLogger
# for visualization
from utils import G1_29_Vis_WholeBody, G1_29_Dex3_JointIndex, G1_29_Inspire_JointIndex

class LocoMotionInference:
    def __init__(
            self, model_path, network_interface,
            device="cuda:0", urdf=None, hand_type=None,
            use_waist3=False,
            control_g1=True,
            sim=False,
            only_calibrate=False,
            use_rc=False,
            max_freq=60.0):

        self.device = device
        self.sim = sim
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
            use_rc=use_rc,
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

    # UNIFIED FUNCTION: Moves the entire body smoothly to the default pose.
    # Used for initial calibration
    def go_to_neutral_pose_smoothly(self, wait=False):
        """
        Moves all robot joints from their current position to the default neutral pose
        in a smooth, interpolated manner.
        """
        if wait:
            print("Press R2 to start moving to neutral pose...")
            while self.control_agent.remote_control.R2 != 1:
                time.sleep(0.01)

        print("Starting move to neutral pose...")

        # Step 1: Get current state and final goal for the ENTIRE body
        self.control_agent_with_history.get_obs()
        current_pos = np.copy(self.control_agent.joint_pos)
        final_goal = self.control_agent.default_dof_pos
        num_dofs = self.control_agent.num_dofs

        # Step 2: Generate a sequence of intermediate targets via interpolation
        target_sequence = []
        target = np.copy(current_pos)
        # Use a small clip value for slow, smooth motion
        clip_val = 0.02
        while np.max(np.abs(target - final_goal)) > clip_val:
            target -= np.clip((target - final_goal), -clip_val, clip_val)
            target_sequence.append(copy.deepcopy(target))
        # Ensure the final goal is reached
        target_sequence.append(final_goal)

        # Step 3: Command the robot through the interpolated trajectory
        for full_body_target in target_sequence:
            lowcmd_tmp = unitree_hg_msg_dds__LowCmd_()
            default_arm_cmd = self.control_agent.arm_buffer.GetData()

            # Iterate through all DOFs and set their target 'q'
            for i in range(num_dofs):
                # We map from the 27/29-dof array back to the G1 joint index (0-28)
                joint_idx = self.control_agent.joint_idxs[i]

                lowcmd_tmp.motor_cmd[joint_idx].mode = 1
                lowcmd_tmp.motor_cmd[joint_idx].q = full_body_target[i]
                lowcmd_tmp.motor_cmd[joint_idx].dq = 0.

                # Assign appropriate PD gains for legs vs. arms/waist
                if i < self.control_agent.num_lower_dofs: # Legs
                     lowcmd_tmp.motor_cmd[joint_idx].kp = self.control_agent.Kp[joint_idx]
                     lowcmd_tmp.motor_cmd[joint_idx].kd = self.control_agent.Kd[joint_idx]
                else: # Arms and Waist (use gains from teleop subscriber)
                     lowcmd_tmp.motor_cmd[joint_idx].kp = default_arm_cmd.motor_cmd[joint_idx].kp
                     lowcmd_tmp.motor_cmd[joint_idx].kd = default_arm_cmd.motor_cmd[joint_idx].kd

            if self.control_agent.control_g1:
                self.control_agent.lowcmd_buffer.SetData(lowcmd_tmp)

            time.sleep(0.02) # Control the speed of the motion (50Hz)

        print("Robot is in neutral pose.")

        if wait:
            print("[Press R2 to start controller]")
            while self.control_agent.remote_control.R2 != 1:
                time.sleep(0.01)

        # Return the first observation for the main loop
        obs = self.control_agent_with_history.reset()
        return obs

    def run(self):
        # 这个会循环控制机器人
        self.control_agent_with_history.reset()
        #obs_history = self.calibrate_robot(wait=True)["obs_history"]
        obs_history = self.go_to_neutral_pose_smoothly(wait=True)["obs_history"]

        # --- Main Loop FPS Logging Setup ---
        main_loop_fps_logger = SimpleFPSLogger(name="MainControlLoop", logger=logger_mp)

        print("controller started, L2+B to enter damping mode to exit")
        while True:

            if self.control_agent.stop:
                logger_mp.info("Stop signal received, exiting main control loop.")
                break

            start_time = time.time()

            # 如果要看ONNX时间对比control step，注释掉t0, t1, t2
            #t0 = time.time()
            actions = self.loco_policy(obs_history) # 5090笔记本电脑只需要1ms以内
            #t1 = time.time()

            if not self.only_calibrate:
                obs, low_cmd_targets = self.control_agent_with_history.step(actions)

                obs_history = obs["obs_history"]

            if not self.control_g1 and main_loop_fps_logger.frames_since_last_log % 10 == 0: # Visualize only every 5th frame
                # visualization can be slower
                self._show_current_targets(low_cmd_targets)

            #t2 = time.time()

            # Log timings occasionally
            #if main_loop_fps_logger.frames_since_last_log % 200 == 0:
            #    logger_mp.info(f"Timings (ms) -> Inference: {(t1-t0)*1000:.2f}, Step/vis: {(t2-t1)*1000:.2f}")

            # Ensure consistent frame rate
            current_time = time.time()
            time_elapsed = current_time - start_time
            sleep_time = max(0, (1 / self.ctr_max_freq) - time_elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)

            # Log FPS for the main control loop
            main_loop_fps_logger.tick()


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
            device="cuda:0", control_g1=True,
            use_rc=False):

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

        #height_cmd = 1.65 # 宇树遥控器上下按键可以改变这个
        self.remote_control = UnitreeRemoteController(
            height_limit=(1.0, 1.65))
        # command 用json格式

        self.cmd_buffer = DataBuffer()
        # 是否使用宇树遥控器的 vxyyaw_height指令
        self.use_rc = use_rc
        # 遥控器状态和机器人状态同时获取，遥控器应该低频点检查状态
        self.REMOTE_CHECK_INTERVAL = 10 # 10 对应 50 Hz
        self._remote_check_counter = 0


        # ================================================================

        # --- FPS Logging Setup for Threads ---
        self.motor_sub_fps_logger = SimpleFPSLogger(
            name="MotorSubscribeThread", logger=logger_mp)
        self.lowcmd_pub_fps_logger = SimpleFPSLogger(
            name="LowCmdPublishThread", logger=logger_mp)


        # Homie原本腰部只用一个自由度作为观测
        self.joint_idxs = [0,1,2,3,4,5,6,7,8,9,10,11,12,15,16,17,18,19,20,21,22,23,24,25,26,27,28]
        self.default_dof_pos = np.array(
            [-0.1000,  0.0000,  0.0000,  0.3000, -0.2000,  0.0000, -0.1000,  0.0000,
            0.0000,  0.3000, -0.2000,  0.0000,  0.0000,  0.0000,  0.0000,  0.0000,
            0.0000,  0.0000,  0.0000,  0.0000,  0.0000, 0.0000,  0.0000,  0.0000,
            0.0000,  0.0000,  0.0000], dtype=float) # 27
        # 我们训练了新的
        if use_waist3:
            self.joint_idxs = range(29)
            self.default_dof_pos = np.array(
                [-0.1000,  0.0000,  0.0000,  0.3000, -0.2000,  0.0000, -0.1000,  0.0000,
                0.0000,  0.3000, -0.2000,  0.0000,  0.0000,  0.0000,  0.0000,  0.0000,
                0.0000,  0.0000,  0.0000,  0.0000,  0.0000, 0.0000,  0.0000,  0.0000,
                0.0000,  0.0000,  0.0000, 0.0000,  0.0000], dtype=float)
        # 关节电机pd参数代码位于在“HomieDeploy/unitree_sdk2unitree_sdk2/g1_control.cpp”下的第85行
        # 按200Hz的控制频率
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
        # 如果频率上不去，腿抖的话，降低Kp，增大Kd
        """
        self.Kp = [
            120, 120, 120, 250, 30, 30,      #// legs
            120, 120, 120, 250, 30, 30,      #// legs
            300, 300, 300,                   #// waist
            150, 150, 150, 100,  10, 10, 5,  #// arms
            150, 150, 150, 100,  10, 10, 5,  #// arms
        ]
        self.Kd = [
            3, 3, 3, 4, 3, 3,     #// legs
            3, 3, 3, 4, 3, 3,     #// legs
            5, 5, 5,              #// waist
            4, 4, 4, 1, 0.5, 0.5, 0.5,  #// arms
            4, 4, 4, 1, 0.5, 0.5, 0.5   #// arms
        ]
        """
        # 腿部动作平滑
        self.smoothed_actions = None
        self.smoothing_alpha = 0.9 # TUNE THIS: 0.1=very smooth, 0.9=less smooth

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

        # --- NEW: Watchdog Timer for Network Safety ---
        # The maximum time in seconds to wait for a new LowState message
        # before triggering an emergency stop. 200ms is a safe and
        # conservative value, allowing for minor network jitter.
        self.STATE_TIMEOUT_S = 0.2
        self.last_lowstate_receipt_time = time.time()
        # --- End Watchdog Timer Setup ---

        self.lowstate_subscriber = ChannelSubscriber("rt/lowstate", LowState_)
        self.lowstate_subscriber.Init()
        self.lowstate_buffer = DataBuffer()

        self.update_mode_machine_ = False
        self.mode_machine_ = 0

        # initialize subscribe thread
        self.subscribe_motor_thread = threading.Thread(target=self._subscribe_motor_state)
        self.subscribe_motor_thread.daemon = True
        self.subscribe_motor_thread.start()
        while not self.lowstate_buffer.GetData():
            time.sleep(0.1)
            logger_mp.info("[G1_29_State] Waiting to subscribe dds...")
        logger_mp.info("[G1_29_State] Subscribe dds ok.")

        if not self.use_rc: # 不使用宇树遥控器的话才subscribe外部的loco_cmd
            self.cmd_subscriber = ChannelSubscriber("rt/loco_cmd", String_)
            self.cmd_subscriber.Init()

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


        # 默认0力矩命令
        self.low_cmd = unitree_hg_msg_dds__LowCmd_()
        self.low_cmd.mode_pr = 0 # Series Control for Pitch/Roll Joints这是URDF的默认模式
        #self.low_cmd.mode_machine = 5 # g1_low_level_example.py中获取到的
        self.low_cmd.mode_machine = self.mode_machine_
        # 阻尼命令
        self.low_cmd_damp = unitree_hg_msg_dds__LowCmd_()
        self.low_cmd_damp.mode_pr = 0 # Series Control for Pitch/Roll Joints这是URDF的默认模式
        self.low_cmd_damp.mode_machine = self.mode_machine_
        for joint in G1_29_JointIndex:
            joint_id = joint.value
            self.low_cmd_damp.motor_cmd[joint_id].mode = 1
            self.low_cmd_damp.motor_cmd[joint_id].q = 0.0
            self.low_cmd_damp.motor_cmd[joint_id].dq = 0.0
            self.low_cmd_damp.motor_cmd[joint_id].kp = 0.0
            self.low_cmd_damp.motor_cmd[joint_id].kd = 2.0
            self.low_cmd_damp.motor_cmd[joint_id].tau = 0.0

        self.stop = False  # 用于指示motor_cmd替换成damping

        if self.control_g1:
            self.lowcmd_buffer = DataBuffer()
            # create publisher #
            while not self.update_mode_machine_:
                logger_mp.info("[G1_29_Control] Waiting to update mode machine...")
                time.sleep(0.1)
            logger_mp.info("[G1_29_Control] Done. mode machine set to %s" % self.mode_machine_)
            self.lowcmd_publisher = ChannelPublisher("rt/lowcmd", LowCmd_)
            self.lowcmd_publisher.Init()

            self.send_lowcmd_thread = threading.Thread(target=self._send_lowcmd)
            self.send_lowcmd_thread.daemon = True
            self.send_lowcmd_thread.start()


    def _send_lowcmd(self):
        while True:
            # --- NEW: Watchdog Check ---
            # This check runs at 500Hz.
            if not self.stop:
                time_since_last_state = time.time() - self.last_lowstate_receipt_time
                if time_since_last_state > self.STATE_TIMEOUT_S:
                    logger_mp.info(
                        f"STATE TIMEOUT: No LowState message received for {time_since_last_state:.2f}s. "
                        f"Triggering emergency stop!"
                    )
                    self.stop = True
            # --- End Watchdog Check ---

            if self.stop:
                self.low_cmd_damp.crc = self.crc.Crc(self.low_cmd_damp)
                write_cmd = self.low_cmd_damp
            else:
                read_lowcmd = self.lowcmd_buffer.GetData()

                if read_lowcmd is not None:

                    for joint in G1_29_JointIndex:
                        joint_id = joint.value
                        self.low_cmd.motor_cmd[joint_id].mode = 1 # 1:Enable, 0:Disable
                        self.low_cmd.motor_cmd[joint_id].tau = read_lowcmd.motor_cmd[joint_id].tau
                        self.low_cmd.motor_cmd[joint_id].q = read_lowcmd.motor_cmd[joint_id].q
                        self.low_cmd.motor_cmd[joint_id].dq = read_lowcmd.motor_cmd[joint_id].dq
                        self.low_cmd.motor_cmd[joint_id].kp = read_lowcmd.motor_cmd[joint_id].kp
                        self.low_cmd.motor_cmd[joint_id].kd = read_lowcmd.motor_cmd[joint_id].kd

                self.low_cmd.crc = self.crc.Crc(self.low_cmd)
                write_cmd = self.low_cmd

            self.lowcmd_publisher.Write(write_cmd)

            # Log FPS for this thread, but only when actively publishing commands
            if not self.stop:
                self.lowcmd_pub_fps_logger.tick()

            time.sleep(0.002) # 500Hz

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

                # --- NEW: Update Watchdog Timestamp ---
                # Every time we successfully receive a state message, we update the timestamp.
                # This serves as the "heartbeat" from the robot.
                self.last_lowstate_receipt_time = time.time()
                # --- End Timestamp Update ---

                # Log FPS for this thread
                self.motor_sub_fps_logger.tick()

                # default low state
                lowstate = unitree_hg_msg_dds__LowState_()
                # 确认是否需要copy
                lowstate.motor_state = copy.deepcopy(msg.motor_state) # 0-28 is for G1
                lowstate.imu_state = copy.deepcopy(msg.imu_state)
                self.lowstate_buffer.SetData(lowstate)

                # need this to update the mode_machine
                # 这个值很重要，不对的话lowcmd就不work
                if self.update_mode_machine_ is False:
                    self.mode_machine_ = msg.mode_machine
                    print("changed model machine using lowstate to %s" % self.mode_machine_)
                    self.update_mode_machine_ = True

                # 获取遥控器状态，多一个保险
                # Only parse remote and check for E-stop every k steps.
                if self._remote_check_counter % self.REMOTE_CHECK_INTERVAL == 0:
                    self.remote_control.parse(msg.wireless_remote)
                    # 同样L2+B就应该退出程序急停
                    if self.remote_control.L2 == 1 and self.remote_control.B == 1:
                        # we set a shared 'stop' flag. The main loop will check this flag and exit.
                        if not self.stop:
                            logger_mp.info("Emergency stop (L2+B) detected! Initiating safe shutdown.")
                            self.stop = True

                    if self.use_rc:
                        # print了一下宇树遥控器，摇杆可能都有误差
                        # 左摇杆，上下值 Ly=[0.95, -0.83], 左右值范围Lx=[-1.0, 1.0]
                        # 右摇杆，上下值 Ry=[1.0, -1.0], 左右值范围Rx=[-0.92, 0.94]
                        # 其他按键按下了就是持续是1值
                        v_x = self.remote_control.Ly    # Forward/backward velocity
                        # 左摇杆，往左，是负的，对应机器人左手，是y轴正方向
                        v_y = -self.remote_control.Lx    # Sideways/strafing velocity
                        v_yaw = -self.remote_control.Rx  # Turning/yaw velocity
                        height = self.remote_control.height
                        cmd_json = {
                            "v_x": v_x,
                            "v_y": v_y,
                            "v_yaw": v_yaw,
                            #"height": 1.65
                            "height": height
                        }
                        #print(cmd_json)
                        self.cmd_buffer.SetData(cmd_json)

            time.sleep(0.002)

    def _subscribe_cmd(self):
        while True:
            msg = self.cmd_subscriber.Read()
            if msg is not None:
                cmd_string = msg.data
                cmd_json = json.loads(cmd_string)
                self.cmd_buffer.SetData(cmd_json)
            time.sleep(0.005) # 200Hz

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

            time.sleep(0.005) # 200Hz

    def reset(self):
        self.actions = torch.zeros(12)

        return self.get_obs()

    def _get_command(self):
        # default cmd

        # 0.74
        cmd = np.array([0.0, 0.0, 0.0, 0.74])
        speed_filter = 0.1 # 摇杆漂移的值，小于这个就抹零
        cmd_json = self.cmd_buffer.GetData()
        if cmd_json is not None:

            #cmd_json = json.loads(cmd_string)
            # 给定的cmd指令应该都是-1.0+1.0之间
            v_x = float(cmd_json["v_x"]) * 0.6
            v_y = float(cmd_json["v_y"]) * 0.5
            v_yaw = float(cmd_json["v_yaw"]) * 0.8

            if v_x>0:
                v_x=(max(np.abs(v_x)-speed_filter,0))
            else:
                v_x=-(max(np.abs(v_x)-speed_filter,0))
            if v_y>0:
                v_y=(max(np.abs(v_y)-speed_filter,0))
            else:
                v_y=-(max(np.abs(v_y)-speed_filter,0))
            if v_yaw>0:
                v_yaw=(max(np.abs(v_yaw)-speed_filter,0))
            else:
                v_yaw=-(max(np.abs(v_yaw)-speed_filter,0))

            height = float(cmd_json["height"])
            # height必须 1.65~0.74之间,下面就会得到0.74 ~ 0.08
            height = max(1.2, min(height, 1.65))
            height = 0.74 - 0.54 * (1.65-min(height, 1.65))*1.0/(1.65-0.91)
            # TODO: 加 filter/ value check
            cmd = np.array([v_x, v_y, v_yaw, height])

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
        cmds = self._get_command() * np.array([2.0, 2.0, 0.25, 1.0])
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
         # --- START SMOOTHING LOGIC ---
        if self.smoothed_actions is None:
            self.smoothed_actions = actions
        else:
            self.smoothed_actions = self.smoothing_alpha * actions + \
                                   (1 - self.smoothing_alpha) * self.smoothed_actions

        # 模型输出平滑这么多？
        #scaled_pos_target = actions * 0.25 + self.default_dof_pos[:12]
        scaled_pos_target = self.smoothed_actions * 0.25 + self.default_dof_pos[:12]

        # torques = (scaled_pos_target - self.dof_pos[:12]) * self.p_gains[:12]  - self.dof_vel[:12] * self.d_gains[:12]
        # torques = np.clip(torques[:12], -self.torque_limit[:12], self.torque_limit[:12])
        self.joint_pos_target[:12] = scaled_pos_target[:12]

        # 接收arm 和腰部的动作指令，一起控制G1
        arm_cmd = self.arm_buffer.GetData()


        lowcmd_tmp = unitree_hg_msg_dds__LowCmd_()
        # 先设置腿部
        for i in range(12):
            lowcmd_tmp.motor_cmd[i].mode = 1 # 1:Enable, 0:Disable
            lowcmd_tmp.motor_cmd[i].tau = self.tauff[i] # 默认都是0
            lowcmd_tmp.motor_cmd[i].q = self.joint_pos_target[i]
            lowcmd_tmp.motor_cmd[i].dq = 0.
            lowcmd_tmp.motor_cmd[i].kp = self.Kp[i]
            lowcmd_tmp.motor_cmd[i].kd = self.Kd[i]

        for joint in G1_29_ArmJointIndex: # 12+3 # 手臂加上腰部
            joint_id = joint.value
            lowcmd_tmp.motor_cmd[joint_id].mode = 1 # 1:Enable, 0:Disable
            lowcmd_tmp.motor_cmd[joint_id].tau = arm_cmd.motor_cmd[joint_id].tau
            lowcmd_tmp.motor_cmd[joint_id].q = arm_cmd.motor_cmd[joint_id].q
            lowcmd_tmp.motor_cmd[joint_id].dq = arm_cmd.motor_cmd[joint_id].dq
            lowcmd_tmp.motor_cmd[joint_id].kp = arm_cmd.motor_cmd[joint_id].kp
            lowcmd_tmp.motor_cmd[joint_id].kd = arm_cmd.motor_cmd[joint_id].kd


        if self.control_g1:
            self.lowcmd_buffer.SetData(lowcmd_tmp)

        # 不发送指令，可以把low_cmd拿去可视化

        obs = self.get_obs()
        return obs, lowcmd_tmp



parser = argparse.ArgumentParser()
parser.add_argument("--model_path", help="locomotion policy onnx model ")
parser.add_argument("--use_waist3", action="store_true", help="homie observes 29 instead of 27 dof")
parser.add_argument("--urdf", default=None, help="need this for visualization")

parser.add_argument("--sim", action="store_true", help="read G1 states from simulation")
parser.add_argument("--no_control", action="store_true", help="visualize output control command instead of sending to G1")
parser.add_argument("--only_calibrate", action="store_true", help="only run calibration, see if G1 cmd works")
parser.add_argument("--network_interface", default=None)
parser.add_argument("--hand_type", default="dex3", help="dex3 or inspire1")
parser.add_argument("--max_freq", default=200.0, type=float, help="maximum freq")
parser.add_argument("--use_rc", action="store_true", help="use unitree remote for loco cmd instead of teleop controller")

if __name__ == "__main__":
    # 测试， 先开了G1 sim或者实机G1, 然后每次模型输出的q可视化到meshcat中
    args = parser.parse_args()
    if args.no_control and args.only_calibrate:
        print("You cannot no control and only calibrate the robot")
        sys.exit()
    locomotion_controller = LocoMotionInference(
        args.model_path, args.network_interface,
        device="cuda:0", urdf=args.urdf, hand_type=args.hand_type,
        use_waist3=args.use_waist3,
        control_g1=not args.no_control,
        sim=args.sim,
        only_calibrate=args.only_calibrate,
        use_rc=args.use_rc,
        max_freq=args.max_freq)
    try:
        # This loop will now exit gracefully when the 'stop' flag is set from the remote or Ctrl+C.
        locomotion_controller.run()
    except KeyboardInterrupt:
        # This handles Ctrl+C.
        print("\nKeyboard interrupt detected. Initiating safe shutdown.")
    finally:
        # This block executes on ANY exit condition (remote stop or Ctrl+C), ensuring safety.
        print("Control loop exited. Starting safe shutdown procedure...")

        if locomotion_controller and locomotion_controller.control_agent:
            # Immediately switch to damping mode.
            print("Activating damping mode for safety...")
            locomotion_controller.control_agent.stop = True
            time.sleep(3.0) # Allow time for damping command to be sent consistently.



        print("Shutdown complete.")

