# coding=utf-8
"""
Given a json episode of two arms (collected using xr_teleoperate), visualize in meshcat
"""
import argparse
import json
import meshcat.geometry as mg
import numpy as np
import pinocchio as pin
import time
from pinocchio.robot_wrapper import RobotWrapper
from pinocchio.visualize import MeshcatVisualizer
import os
import sys
import threading

parser = argparse.ArgumentParser()

parser.add_argument("episode_json")
parser.add_argument("urdf")
parser.add_argument("--fps", type=float, default="60", help="the episode is recored in this fps, so we play in this fps")

""" # joint id for reduced g1 with inspire hand
Joint ID 1: left_shoulder_pitch_joint
Joint ID 2: left_shoulder_roll_joint
Joint ID 3: left_shoulder_yaw_joint
Joint ID 4: left_elbow_joint
Joint ID 5: left_wrist_roll_joint
Joint ID 6: left_wrist_pitch_joint
Joint ID 7: left_wrist_yaw_joint
Joint ID 8: L_index_proximal_joint
Joint ID 9: L_middle_proximal_joint
Joint ID 10: L_pinky_proximal_joint
Joint ID 11: L_ring_proximal_joint
Joint ID 12: L_thumb_proximal_yaw_joint
Joint ID 13: L_thumb_proximal_pitch_joint
Joint ID 14: right_shoulder_pitch_joint
Joint ID 15: right_shoulder_roll_joint
Joint ID 16: right_shoulder_yaw_joint
Joint ID 17: right_elbow_joint
Joint ID 18: right_wrist_roll_joint
Joint ID 19: right_wrist_pitch_joint
Joint ID 20: right_wrist_yaw_joint
Joint ID 21: R_index_proximal_joint
Joint ID 22: R_middle_proximal_joint
Joint ID 23: R_pinky_proximal_joint
Joint ID 24: R_ring_proximal_joint
Joint ID 25: R_thumb_proximal_yaw_joint
Joint ID 26: R_thumb_proximal_pitch_joint
"""
class G1_29_Vis_Episode:
    def __init__(self, urdf, fps=60):

        np.set_printoptions(precision=5, suppress=True, linewidth=200)

        self.robot = pin.RobotWrapper.BuildFromURDF(urdf, os.path.dirname(urdf))

        self.mixed_jointsToLockIDs = [
            # 固定下半身
            "left_hip_pitch_joint" ,
            "left_hip_roll_joint" ,
            "left_hip_yaw_joint" ,
            "left_knee_joint" ,
            "left_ankle_pitch_joint" ,
            "left_ankle_roll_joint" ,
            "right_hip_pitch_joint" ,
            "right_hip_roll_joint" ,
            "right_hip_yaw_joint" ,
            "right_knee_joint" ,
            "right_ankle_pitch_joint" ,
            "right_ankle_roll_joint" ,
            "waist_yaw_joint" ,
            "waist_roll_joint" ,
            "waist_pitch_joint",


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
        # fixed joint from xr_teleoperate/teleop/robot_control/robot_arm_ik.py
        # use g1_body29_hand14.urdf
        """
        self.mixed_jointsToLockIDs = [
                                        "left_hip_pitch_joint" ,
                                        "left_hip_roll_joint" ,
                                        "left_hip_yaw_joint" ,
                                        "left_knee_joint" ,
                                        "left_ankle_pitch_joint" ,
                                        "left_ankle_roll_joint" ,
                                        "right_hip_pitch_joint" ,
                                        "right_hip_roll_joint" ,
                                        "right_hip_yaw_joint" ,
                                        "right_knee_joint" ,
                                        "right_ankle_pitch_joint" ,
                                        "right_ankle_roll_joint" ,
                                        "waist_yaw_joint" ,
                                        "waist_roll_joint" ,
                                        "waist_pitch_joint" ,

                                        # 用的宇树三指手的URDF，每个7自由度，全部锁了
                                        "left_hand_thumb_0_joint" ,
                                        "left_hand_thumb_1_joint" ,
                                        "left_hand_thumb_2_joint" ,
                                        "left_hand_middle_0_joint" ,
                                        "left_hand_middle_1_joint" ,
                                        "left_hand_index_0_joint" ,
                                        "left_hand_index_1_joint" ,

                                        "right_hand_thumb_0_joint" ,
                                        "right_hand_thumb_1_joint" ,
                                        "right_hand_thumb_2_joint" ,
                                        "right_hand_index_0_joint" ,
                                        "right_hand_index_1_joint" ,
                                        "right_hand_middle_0_joint",
                                        "right_hand_middle_1_joint"
                                    ]
        """

        # https://docs.ros.org/en/kinetic/api/pinocchio/html/classpinocchio_1_1robot__wrapper_1_1RobotWrapper.html#aef341b27b4709b03c93d66c8c196bc0f
        # the above joint will be locked, at 0.0
        self.reduced_robot = self.robot.buildReducedRobot(
            list_of_joints_to_lock=self.mixed_jointsToLockIDs,
            reference_configuration=np.array([0.0] * self.robot.model.nq),
        )

        #debugging printouts
        """
        print("reduced_robot.model.nframes")
        for i in range(self.reduced_robot.model.nframes):
            frame = self.reduced_robot.model.frames[i]
            frame_id = self.reduced_robot.model.getFrameId(frame.name)
            print(f"Frame ID: {frame_id}, Name: {frame.name}")

        #assert len(self.reduced_robot.model.frames) == len(self.reduced_robot.data.oMf), \
        #    f"Mismatch: {len(self.reduced_robot.model.frames)} frames vs. {len(self.reduced_robot.data.oMf)} transformations"

        # Print all joints in the original robot model
        print("All Joints in Original Robot:")
        for idx, joint in enumerate(self.robot.model.names):
            print(f"Joint ID {idx}: {joint}")

        # Print joints in the reduced robot model
        print("\nJoints in Reduced Robot:")
        for idx, joint in enumerate(self.reduced_robot.model.names):
            print(f"Joint ID {idx}: {joint}")

        print("reduced_robot.model.nq:%s" % self.reduced_robot.model.nq)
        sys.exit()
        """


        self.init_data = np.zeros(self.reduced_robot.model.nq)

        self.current_q = np.zeros(self.reduced_robot.model.nq) # used to save the current q


        # Initialize the Meshcat visualizer for visualization
        self.vis = MeshcatVisualizer(
            self.reduced_robot.model, self.reduced_robot.collision_model, self.reduced_robot.visual_model)
        self.vis.initViewer(open=True)
        self.vis.loadViewerModel("pinocchio")

        self.vis.display(pin.neutral(self.reduced_robot.model))

        self.paused = False
        self.current_step = 0
        self.total_steps = 0
        self.fps = fps
        self.lock = threading.Lock()

    def update_display_text(self):
        with self.lock:
            current_time_display = self.current_step / self.fps
            self.vis.viewer["info"].set_object(
                mg.Text(f"Time: {current_time_display:.2f}s | Step: {self.current_step}/{self.total_steps}",
                        height=0.1))
            self.vis.viewer["info"].set_transform(
                mg.Translation(0.5, 0, 0.5)
            ) # Adjust position as needed

    def process_key_event(self, event):
        if event.key == "s":
            with self.lock:
                self.paused = not self.paused
                print(f"Playback {'paused' if self.paused else 'resumed'}")
        elif self.paused:
            if event.key == "-":
                with self.lock:
                    self.current_step = max(0, self.current_step - 10)
                    print(f"Jumped back to step {self.current_step}")
                    self.display_current_frame()
            elif event.key == "+":
                with self.lock:
                    self.current_step = min(self.total_steps - 1, self.current_step + 10)
                    print(f"Jumped forward to step {self.current_step}")
                    self.display_current_frame()

    def display_current_frame(self):
        # This function will be called to update the robot's pose based on current_step
        # You'll need access to the `episode` data here.
        # For simplicity, let's assume `self.episode_data` holds the loaded episode.
        if self.current_step < self.total_steps:
            step_data = self.episode_data["data"][self.current_step]["actions"]

            left_arm_pos = step_data["left_arm"]["qpos"]
            right_arm_pos = step_data["right_arm"]["qpos"]

            left_ee_pos = np.array(step_data["left_ee"]["qpos"])
            left_ee_pos = left_ee_pos[left_inspire_api_to_urdf_index]
            right_ee_pos = np.array(step_data["right_ee"]["qpos"])
            right_ee_pos = right_ee_pos[right_inspire_api_to_urdf_index]

            target_q = np.zeros((26, ), dtype=np.float32)
            target_q[:7] = left_arm_pos
            target_q[7:13] = left_ee_pos
            target_q[13:20] = right_arm_pos
            target_q[20:] = right_ee_pos

            self.vis.display(target_q)
            self.update_display_text()

left_inspire_api_joint_names = [
    'L_pinky_proximal_joint',
    'L_ring_proximal_joint',
    'L_middle_proximal_joint',
    'L_index_proximal_joint',
    'L_thumb_proximal_pitch_joint',
    'L_thumb_proximal_yaw_joint' ]

left_inspire_urdf_joint_names = [
    'L_index_proximal_joint',
    'L_middle_proximal_joint',
    'L_pinky_proximal_joint',
    'L_ring_proximal_joint',
    'L_thumb_proximal_yaw_joint',
    'L_thumb_proximal_pitch_joint',
]
left_inspire_api_to_urdf_index = [
    left_inspire_api_joint_names.index(name)
    for name in left_inspire_urdf_joint_names]

right_inspire_api_joint_names = [
    'R_pinky_proximal_joint',
    'R_ring_proximal_joint',
    'R_middle_proximal_joint',
    'R_index_proximal_joint',
    'R_thumb_proximal_pitch_joint',
    'R_thumb_proximal_yaw_joint' ]

right_inspire_urdf_joint_names = [
    'R_index_proximal_joint',
    'R_middle_proximal_joint',
    'R_pinky_proximal_joint',
    'R_ring_proximal_joint',
    'R_thumb_proximal_yaw_joint',
    'R_thumb_proximal_pitch_joint',
]
right_inspire_api_to_urdf_index = [
    right_inspire_api_joint_names.index(name)
    for name in right_inspire_urdf_joint_names]

if __name__ == "__main__":
    args = parser.parse_args()

    vis_model = G1_29_Vis_Episode(urdf=args.urdf, fps=args.fps)

    # load the episode
    episode = json.load(open(args.episode_json))
    vis_model.episode_data = episode # Store episode data for access in display_current_frame

    num_data_step = len(episode["data"])
    vis_model.total_steps = num_data_step
    print("total %d data steps, it should be %.2f seconds long" % (num_data_step, num_data_step/args.fps))

    # Set up keyboard callback
    vis_model.vis.viewer.on_render(vis_model.process_key_event)
    vis_model.vis.viewer["info"].set_object(mg.Text("Loading...", height=0.1))


    while True:
        with vis_model.lock:
            if not vis_model.paused:
                if vis_model.current_step < num_data_step:
                    vis_model.display_current_frame()
                    vis_model.current_step += 1
                else:
                    print("Episode finished.")
                    vis_model.paused = True # Pause at the end

        time.sleep(1 / args.fps)
