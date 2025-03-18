# coding=utf-8
# given urdf, print all the joint. compute transform between one link to origin
# also visualize

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

    return T_origin_to_target.homogeneous, T_target_to_origin.homogeneous

if __name__ == "__main__":
    args = parser.parse_args()

    robot = pin.RobotWrapper.BuildFromURDF(args.urdf, os.path.dirname(args.urdf))


    # add a frame to the joint/link you want to compute transform for
    robot.model.addFrame(
        pin.Frame('R_ee',
                  robot.model.getJointId('R_index_tip_joint'),
                  pin.SE3(np.eye(3),
                          np.array([0.1, 0.0, 0.]).T), # on the palm
                  pin.FrameType.OP_FRAME)
    )

    for i in range(robot.model.nframes):
        frame = robot.model.frames[i]
        frame_id = robot.model.getFrameId(frame.name)
        print(f"Frame ID: {frame_id}, Name: {frame.name}")

    # 必须要更新这个，否则data.oMf没有这个新的frame
    robot.data = pin.Data(robot.model)

    ee_frame_id = robot.model.getFrameId("R_ee")

    # using meshcat visualizer to show origin, and the ee pose
    vis = MeshcatVisualizer(robot.model, robot.collision_model, robot.visual_model)
    vis.initViewer(open=True)
    vis.loadViewerModel("pinocchio")

    vis.display(pin.neutral(robot.model))

    # this will show the ee axis
    #vis.displayFrames(True, frame_ids=[ee_frame_id], axis_length = 0.15, axis_width = 5)

    # now, compute the transform between some target frame
    # in red balls
    origin_frame = "pelvis"
    target_frame = "d435_link"

    # in green balls
    visualization_list = [
        "d435_joint",
        "R_ee"
    ]
    # forward kinematics
    # Update kinematics to get the latest pose (update joint position and frame position)
    pin.framesForwardKinematics(robot.model,
                                robot.data,
                                np.zeros(robot.model.nq)) # use the zero pose

    ## Update the data object to reflect the new frames
    # 必须要更新这个，否则data.oMf没有这个新的frame
    #  self.reduced_robot.data = pin.Data(self.reduced_robot.model)
    assert len(robot.model.frames) == len(robot.data.oMf)

    origin_frame_id = robot.model.getFrameId(origin_frame)
    target_frame_id = robot.model.getFrameId(target_frame)
    origin_pose = robot.data.oMf[origin_frame_id]
    target_pose = robot.data.oMf[target_frame_id]
    ee_pose = robot.data.oMf[ee_frame_id]

    T_origin_to_target, T_target_to_origin = compute_transformation(origin_pose, target_pose)

    print("Transformation from %s to %s:\n" % (origin_frame, target_frame), T_origin_to_target)
    print("Transformation from %s to %s:\n" % (target_frame, origin_frame), T_target_to_origin)
    # given xyz in the target frame (camera frame), compute xyz in the origin frame
    # P_camera = np.array([x, y, z, 1])  # Homogeneous coordinates in the camera frame
    # P_origin = T_origin_to_camera @ P_camera  # Transform to the origin frame

    # visualize the frames you want
    red = 0xff0000
    green = 0x00FF00
    vis.viewer["origin/sphere"].set_object(g.Sphere(0.05), g.MeshLambertMaterial(color=red))
    vis.viewer["origin"].set_transform(origin_pose.homogeneous)
    vis.viewer["target/sphere"].set_object(g.Sphere(0.05), g.MeshLambertMaterial(color=red))
    vis.viewer["target"].set_transform(target_pose.homogeneous)
    vis.viewer["ee/sphere"].set_object(g.Sphere(0.02), g.MeshLambertMaterial(color=red))
    vis.viewer["ee"].set_transform(ee_pose.homogeneous)


    for frame_name in visualization_list:
        pose = robot.data.oMf[robot.model.getFrameId(frame_name)]
        vis.viewer["%s/sphere" % frame_name].set_object(g.Sphere(0.02), g.MeshLambertMaterial(color=green))
        vis.viewer[frame_name].set_transform(pose.homogeneous)

    # Enable the display of end effector target frames with short axis lengths and greater width.
    frame_viz_names = [origin_frame, target_frame, "R_ee"] + visualization_list
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
