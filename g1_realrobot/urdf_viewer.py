# coding=utf-8
# visualize the urdf and display the origin of the robot


import mujoco
import mujoco.viewer
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("urdf")

if __name__ == "__main__":
    args = parser.parse_args()

    # Load the model from the URDF
    m = mujoco.MjModel.from_xml_path(args.urdf)
    d = mujoco.MjData(m)

    # Function to add axis geoms
    def add_axis_geoms(model):
        # X-axis (red)
        model.worldbody.add('geom', type="cylinder", fromto="0 0 0 0.1 0 0", size="0.002", rgba="1 0 0 1")
        # Y-axis (green)
        model.worldbody.add('geom', type="cylinder", fromto="0 0 0 0 0.1 0", size="0.002", rgba="0 1 0 1")
        # Z-axis (blue)
        model.worldbody.add('geom', type="cylinder", fromto="0 0 0 0 0 0.1", size="0.002", rgba="0 0 1 1")
        # Small sphere at the origin
        model.worldbody.add('geom', type="sphere", pos="0 0 0", size="0.005", rgba="1 1 0 1")

    # Add the axes and reload the model
    add_axis_geoms(m)

    # Launch the MuJoCo viewer
    with mujoco.viewer.launch_passive(m, d) as viewer:
        print("Viewer running. Press ESC to exit.")
