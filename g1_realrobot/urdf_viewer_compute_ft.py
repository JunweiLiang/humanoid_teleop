# coding=utf-8
# given urdf, print all the joint. compute transform between one link to origin
# also visualize
"""
    给定G1+因时灵巧手，
    计算T_D435 -> robot base
    右手食指到右手腕的SE3 transform

"""

import argparse
import os
import numpy as np
import time

from pinocchio.visualize import MeshcatVisualizer
import pinocchio as pin
import meshcat.geometry as g
import meshcat.geometry as mg

parser = argparse.ArgumentParser()
parser.add_argument("urdf")

def compute_and_vis(origin_frame, target_frame, vis, robot):
    origin_frame_id = robot.model.getFrameId(origin_frame)
    target_frame_id = robot.model.getFrameId(target_frame)
    origin_pose = robot.data.oMf[origin_frame_id]
    target_pose = robot.data.oMf[target_frame_id]


    T_origin_to_target, T_target_to_origin = compute_transformation(origin_pose, target_pose)

    print("Transformation from %s to %s:\n" % (origin_frame, target_frame), T_origin_to_target.homogeneous)
    print("Transformation from %s to %s:\n" % (target_frame, origin_frame), T_target_to_origin.homogeneous)
    # given xyz in the target frame (camera frame), compute xyz in the origin frame
    # P_camera = np.array([x, y, z, 1])  # Homogeneous coordinates in the camera frame
    # P_origin = T_origin_to_camera @ P_camera  # Transform to the origin frame

    # visualize the frames you want
    red = 0xff0000
    green = 0x00FF00
    vis.viewer["%s/sphere" % origin_frame].set_object(g.Sphere(0.03), g.MeshLambertMaterial(color=red))
    vis.viewer[origin_frame].set_transform(origin_pose.homogeneous)
    vis.viewer["%s/sphere" % target_frame].set_object(g.Sphere(0.03), g.MeshLambertMaterial(color=red))
    vis.viewer[target_frame].set_transform(target_pose.homogeneous)

    return T_origin_to_target

def compute_transformation(origin_pose, target_pose):
    """
    Compute the 4x4 transformation matrices from origin to target and target to origin.

    Parameters:
        origin_pose (pin.SE3): Pose of the origin frame in world coordinates.
        target_pose (pin.SE3): Pose of the target frame in world coordinates.

    Returns:
        T_origin_to_target (np.ndarray): 4x4 transformation matrix from origin to target.
        T_target_to_origin (np.ndarray): 4x4 transformation matrix from target to origin.
    """
    T_origin_to_target = origin_pose.inverse() * target_pose
    T_target_to_origin = T_origin_to_target.inverse()

    #return T_origin_to_target.homogeneous, T_target_to_origin.homogeneous
    return T_origin_to_target, T_target_to_origin # SE3

if __name__ == "__main__":
    args = parser.parse_args()

    robot = pin.RobotWrapper.BuildFromURDF(args.urdf, os.path.dirname(args.urdf))


    # add a frame to the joint/link you want to compute transform for

    """
    frame_id = robot.model.getFrameId("R_index_tip")
    parent_joint_id = robot.model.frames[frame_id].parent  # Get the actual parent joint


    robot.model.addFrame(
        pin.Frame('R_ee',
                  #robot.model.getJointId('right_wrist_yaw_joint'),
                  parent_joint_id,
                  pin.SE3(np.eye(3),
                          np.array([0.1, 0.0, 0.]).T), # on the palm
                  pin.FrameType.OP_FRAME)
    )
    # 必须要更新这个，否则data.oMf没有这个新的frame
    robot.data = pin.Data(robot.model)

    ee_frame_id = robot.model.getFrameId("R_ee")
    """


    for i in range(robot.model.nframes):
        frame = robot.model.frames[i]
        frame_id = robot.model.getFrameId(frame.name)
        print(f"Frame ID: {frame_id}, Name: {frame.name}")


    # using meshcat visualizer to show origin, and the ee pose
    vis = MeshcatVisualizer(robot.model, robot.collision_model, robot.visual_model)
    vis.initViewer(open=True)
    vis.loadViewerModel("pinocchio")

    vis.display(pin.neutral(robot.model))


    # forward kinematics
    # Update kinematics to get the latest pose (update joint position and frame position)
    pin.framesForwardKinematics(robot.model,
                                robot.data,
                                np.zeros(robot.model.nq)) # use the zero pose

    ## Update the data object to reflect the new frames
    # 必须要更新这个，否则data.oMf没有这个新的frame
    #  self.reduced_robot.data = pin.Data(self.reduced_robot.model)
    assert len(robot.model.frames) == len(robot.data.oMf)

    # now, compute the transform between some target frame
    origin_frame = "pelvis"
    target_frame = "d435_link"

    """
    Transformation from pelvis to d435_link:
         [[ 0.67430239  0.          0.73845534  0.05366   ]
         [ 0.          1.          0.          0.01753   ]
         [-0.73845534  0.          0.67430239  0.47387   ]
         [ 0.          0.          0.          1.        ]]

    """
    T_o2t = compute_and_vis(origin_frame, target_frame, vis, robot)

    arm_frame = "right_wrist_yaw_joint"
    tip_frame = "R_index_tip"
    """
    Transformation from right_wrist_yaw_joint to R_index_tip:
     [[ 2.22018339e-16  9.99391313e-01 -3.48855737e-02  2.48686587e-01]
     [-1.00000000e+00  2.23989393e-16  5.02256656e-17  7.32847000e-03]
     [-5.80145042e-17  3.48855737e-02  9.99391313e-01  2.97837118e-02]
     [ 0.00000000e+00  0.00000000e+00  0.00000000e+00  1.00000000e+00]]

    """
    T_arm2tip = compute_and_vis(arm_frame, tip_frame, vis, robot)

    # show the computed arm2tip is good
    frame_id = robot.model.getFrameId(tip_frame)
    # since some joint in the inspired hand are fixed
    parent_joint_id = robot.model.frames[frame_id].parentJoint  # Get the actual parent joint
    robot.model.addFrame(
        pin.Frame('R_ee',
                  #robot.model.getJointId('right_wrist_yaw_joint'),
                  parent_joint_id,
                  T_arm2tip,
                  pin.FrameType.OP_FRAME)
    )
    # 必须要更新这个，否则data.oMf没有这个新的frame
    robot.data = pin.Data(robot.model)

    green = 0x00FF00
    ee_frame_id = robot.model.getFrameId("R_ee")
    ee_pose = robot.data.oMf[ee_frame_id]
    vis.viewer["target/sphere"].set_object(g.Sphere(0.03), g.MeshLambertMaterial(color=green))
    vis.viewer["target"].set_transform(ee_pose.homogeneous)



    # Enable the display of end effector target frames with short axis lengths and greater width.
    frame_viz_names = [
        origin_frame, target_frame,
        "R_ee"]
    FRAME_AXIS_POSITIONS = (
        np.array([[0, 0, 0], [1, 0, 0],
                  [0, 0, 0], [0, 1, 0],
                  [0, 0, 0], [0, 0, 1]]).astype(np.float32).T
    )
    FRAME_AXIS_COLORS = (
        np.array([[1, 0, 0], [1, 0.6, 0],
                  [0, 1, 0], [0.6, 1, 0],
                  [0, 0, 1], [0, 0.6, 1]]).astype(np.float32).T
    )
    axis_length = 0.1
    axis_width = 10
    for frame_viz_name in frame_viz_names:
        vis.viewer[frame_viz_name].set_object(
            mg.LineSegments(
                mg.PointsGeometry(
                    position=axis_length * FRAME_AXIS_POSITIONS,
                    color=FRAME_AXIS_COLORS,
                ),
                mg.LineBasicMaterial(
                    linewidth=axis_width,
                    vertexColors=True,
                ),
            )
        )


    while True:
        time.sleep(1)
