# coding=utf-8
# visualize the urdf and display the origin of the robot


import mujoco
import mujoco.viewer
import argparse
import sys
import re
import numpy as np

parser = argparse.ArgumentParser()
parser.add_argument("urdf")

if __name__ == "__main__":
    args = parser.parse_args()

    with open(args.urdf, "r") as f:
        urdf_xml = f.read()

    # Add coordinate axes and origin marker to the URDF XML
    axes_geoms = """
      <!-- Base link where the axes will be placed -->
      <link name="base_link">

        <!-- Inertial properties: Add mass and inertia to prevent the "body mass too small" error -->
        <inertial>
          <mass value="0.001"/> <!-- Small mass to prevent the error -->
          <inertia ix="0.0001" iy="0.0001" iz="0.0001" ixx="0.0001" iyy="0.0001" izz="0.0001" ixy="0" ixz="0" iyz="0"/>
        </inertial>

        <!-- X-axis (Red) -->
        <!-- 圆柱体 默认坐立在x轴上，会往上长，所以要pitch 转90度，就成了x轴-->
        <visual>
          <origin xyz="0 0 0" rpy="0 1.5707 0"/>
          <geometry>
            <cylinder radius="0.005" length="1.3"/>
          </geometry>
          <material name="red">
            <color rgba="1.0 0.0 0 1"/>
          </material>
        </visual>

        <!-- Y-axis (Green) -->
        <visual>
          <origin xyz="0 0 0" rpy="1.5707 0 0"/>
          <geometry>
            <cylinder radius="0.005" length="1.3"/>
          </geometry>
          <material name="green">
            <color rgba="0.0 1.0 0 1"/>
          </material>
        </visual>

        <!-- z-axis (blue) -->
        <visual>
          <origin xyz="0 0 0" rpy="0 0 0"/>
          <geometry>
            <cylinder radius="0.005" length="1.3"/>
          </geometry>
          <material name="blue">
            <color rgba="0 0 1.0 1"/>
          </material>
        </visual>

        <!-- Origin Marker (Yellow Sphere) -->
        <visual>
          <origin xyz="0 0 0" rpy="0 0 0"/>
          <geometry>
            <sphere radius="0.05"/>
          </geometry>
          <material name="yellow">
            <color rgba="1.0 1.0 0 1"/>
          </material>
        </visual>

      </link>
    """

    # Check if the <robot> tag exists and capture the robot's attributes (if any)
    robot_tag_match = re.search(r'(<robot\s+[^>]+>)', urdf_xml)
    if robot_tag_match:
        robot_tag = robot_tag_match.group(1)  # Capture the full <robot> tag with attributes
    else:
        sys.exit("Error: No <robot> tag found in URDF")

    # Inject the axes and origin marker geometries after the <robot> tag
    urdf_xml = urdf_xml.replace(robot_tag, robot_tag + axes_geoms)

    # Load the model from the URDF
    model = mujoco.MjModel.from_xml_string(urdf_xml)
    data = mujoco.MjData(model)

    # print out the robot joints as in the GUI's order. The GUI might not show all the joint names
    # Iterate through joints by their IDs, which corresponds to the GUI order
    for joint_id in range(model.njnt):
        joint_name = model.joint(joint_id).name # Use named access to get the joint name [8]
        print("joint id: %d, name: %s" % (joint_id, joint_name))

    # Launch the MuJoCo viewer using the `launch` method
    mujoco.viewer.launch(model, data)

