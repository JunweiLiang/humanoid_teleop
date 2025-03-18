# coding=utf-8
# given urdf, print all the joint. compute transform between one link to origin
# also visualize

import argparse
import os
import numpy as np

from pinocchio.visualize import MeshcatVisualizer
import pinocchio as pin


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
                          np.array([0., 0.0, 0.]).T), # on the palm
                  pin.FrameType.OP_FRAME)
    )

    for i in range(robot.model.nframes):
        frame = robot.model.frames[i]
        frame_id = robot.model.getFrameId(frame.name)
        print(f"Frame ID: {frame_id}, Name: {frame.name}")

    ee_frame_id = robot.model.getFrameId("R_ee")

    # using meshcat visualizer to show origin, and the ee pose
    vis = MeshcatVisualizer(robot.model, robot.collision_model, robot.visual_model)
    vis.initViewer(open=True)
    vis.loadViewerModel("pinocchio")

    vis.display(pin.neutral(robot.model))

    # this will show the ee axis
    vis.displayFrames(True, frame_ids=[ee_frame_id], axis_length = 0.15, axis_width = 5)
