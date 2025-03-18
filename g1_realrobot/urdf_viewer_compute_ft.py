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

parser = argparse.ArgumentParser()
parser.add_argument("urdf")

if __name__ == "__main__":
    args = parser.parse_args()

    robot = pin.RobotWrapper.BuildFromURDF(args.urdf, os.path.dirname(args.urdf))



    # add a frame to the joint/link you want to compute transform for
    robot.model.addFrame(
        pin.Frame('R_ee',
                  robot.model.getJointId('right_wrist_yaw_joint'),
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

    # visualize the frames you want
    red = 0xff0000
    green = 0x00FF00
    vis.viewer["origin/sphere"].set_object(g.Sphere(0.05), g.MeshLambertMaterial(color=red))
    vis.viewer["origin"].set_transform(origin_pose.homogeneous)
    vis.viewer["target/sphere"].set_object(g.Sphere(0.05), g.MeshLambertMaterial(color=red))
    vis.viewer["target"].set_transform(target_pose.homogeneous)
    vis.viewer["ee/sphere"].set_object(g.Sphere(0.02), g.MeshLambertMaterial(color=red))
    vis.viewer["ee"].set_transform(ee_pose.homogeneous)
    vis.displayFrames(True, frame_ids=[ee_frame_id, origin_frame_id, target_frame_id], axis_length = 0.15, axis_width = 5)

    for frame_name in visualization_list:
        pose = robot.data.oMf[robot.model.getFrameId(frame_name)]
        vis.viewer["%s/sphere" % frame_name].set_object(g.Sphere(0.02), g.MeshLambertMaterial(color=green))
        vis.viewer[frame_name].set_transform(pose.homogeneous)



    while True:
        time.sleep(1)
