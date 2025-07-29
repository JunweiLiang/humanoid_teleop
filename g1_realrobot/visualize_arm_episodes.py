# coding=utf-8
"""
Given a json episode of two arms (collected using xr_teleoperate), visualize in meshcat
"""
import argparse
import casadi
import meshcat.geometry as mg
import numpy as np
import pinocchio as pin
import time
from pinocchio import casadi as cpin
from pinocchio.robot_wrapper import RobotWrapper
from pinocchio.visualize import MeshcatVisualizer
import os
import sys

parser = argparse.ArgumentParser()

parser.add_argument("episode_json")
parser.add_argument("urdf")

if __name__ == "__main__":
    args = parser.parse_args()

    # -----------   定义右手初始姿态
    #urdf_path = args.urdf
    down_target = np.zeros(7)
    arm_ik = G1_29_ArmIK(urdf=args.urdf, visualization=True, start_q=down_target)
