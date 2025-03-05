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

parent2_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(parent2_dir)

class WeightedMovingFilter:
    def __init__(self, weights, data_size = 14):
        self._window_size = len(weights)
        self._weights = np.array(weights)
        assert np.isclose(np.sum(self._weights), 1.0), "[WeightedMovingFilter] the sum of weights list must be 1.0!"
        self._data_size = data_size
        self._filtered_data = np.zeros(self._data_size)
        self._data_queue = []

    def _apply_filter(self):
        if len(self._data_queue) < self._window_size:
            return self._data_queue[-1]

        data_array = np.array(self._data_queue)
        temp_filtered_data = np.zeros(self._data_size)
        for i in range(self._data_size):
            temp_filtered_data[i] = np.convolve(data_array[:, i], self._weights, mode='valid')[-1]

        return temp_filtered_data

    def add_data(self, new_data):
        assert len(new_data) == self._data_size

        if len(self._data_queue) > 0 and np.array_equal(new_data, self._data_queue[-1]):
            return  # skip duplicate data

        if len(self._data_queue) >= self._window_size:
            self._data_queue.pop(0)

        self._data_queue.append(new_data)
        self._filtered_data = self._apply_filter()

    @property
    def filtered_data(self):
        return self._filtered_data

class G1_29_ArmIK:
    def __init__(self, urdf, visualization=False):
        np.set_printoptions(precision=5, suppress=True, linewidth=200)
        self.visualization = visualization # will use meshcat in browser to visualize
        self.robot = pin.RobotWrapper.BuildFromURDF(urdf, os.path.dirname(urdf))

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
        # https://docs.ros.org/en/kinetic/api/pinocchio/html/classpinocchio_1_1robot__wrapper_1_1RobotWrapper.html#aef341b27b4709b03c93d66c8c196bc0f
        # the above joint will be locked, at 0.0
        self.reduced_robot = self.robot.buildReducedRobot(
            list_of_joints_to_lock=self.mixed_jointsToLockIDs,
            reference_configuration=np.array([0.0] * self.robot.model.nq),
        )

        self.reduced_robot.model.addFrame(
            # pin.Frame(name, parentJoint, placement, frameType)
            pin.Frame('L_ee',
                      self.reduced_robot.model.getJointId('left_wrist_yaw_joint'),
                      # relative to the parant joint,
                      pin.SE3(np.eye(3), # so no rotation. 3x3 rotation matrix
                              np.array([0.05,0,0]).T), # 5cm along the x-axis from parent
                      pin.FrameType.OP_FRAME) # This defines the type of the frame. OP_FRAME stands for Operational Frame, which is typically used for end-effectors or other points of interest.
        )
        
        self.reduced_robot.model.addFrame(
            pin.Frame('R_ee',
                      self.reduced_robot.model.getJointId('right_wrist_yaw_joint'),
                      pin.SE3(np.eye(3),
                              np.array([0.05,0,0]).T),
                      pin.FrameType.OP_FRAME)
        )

        # for i in range(self.reduced_robot.model.nframes):
        #     frame = self.reduced_robot.model.frames[i]
        #     frame_id = self.reduced_robot.model.getFrameId(frame.name)
        #     print(f"Frame ID: {frame_id}, Name: {frame.name}")
        
        # Creating Casadi models and data for symbolic computing
        self.cmodel = cpin.Model(self.reduced_robot.model)
        self.cdata = self.cmodel.createData()

        # Creating symbolic variables
        self.cq = casadi.SX.sym("q", self.reduced_robot.model.nq, 1) 
        self.cTf_l = casadi.SX.sym("tf_l", 4, 4)
        self.cTf_r = casadi.SX.sym("tf_r", 4, 4)
        cpin.framesForwardKinematics(self.cmodel, self.cdata, self.cq)

        # Get the hand joint ID and define the error function
        self.L_hand_id = self.reduced_robot.model.getFrameId("L_ee")
        self.R_hand_id = self.reduced_robot.model.getFrameId("R_ee")

        self.translational_error = casadi.Function(
            "translational_error",
            [self.cq, self.cTf_l, self.cTf_r],
            [
                casadi.vertcat(
                    self.cdata.oMf[self.L_hand_id].translation - self.cTf_l[:3,3],
                    self.cdata.oMf[self.R_hand_id].translation - self.cTf_r[:3,3]
                )
            ],
        )
        self.rotational_error = casadi.Function(
            "rotational_error",
            [self.cq, self.cTf_l, self.cTf_r],
            [
                casadi.vertcat(
                    cpin.log3(self.cdata.oMf[self.L_hand_id].rotation @ self.cTf_l[:3,:3].T),
                    cpin.log3(self.cdata.oMf[self.R_hand_id].rotation @ self.cTf_r[:3,:3].T)
                )
            ],
        )

        # Defining the optimization problem
        self.opti = casadi.Opti()
        self.var_q = self.opti.variable(self.reduced_robot.model.nq)
        self.var_q_last = self.opti.parameter(self.reduced_robot.model.nq)   # for smooth
        self.param_tf_l = self.opti.parameter(4, 4)
        self.param_tf_r = self.opti.parameter(4, 4)
        self.translational_cost = casadi.sumsqr(self.translational_error(self.var_q, self.param_tf_l, self.param_tf_r))
        self.rotation_cost = casadi.sumsqr(self.rotational_error(self.var_q, self.param_tf_l, self.param_tf_r))
        self.regularization_cost = casadi.sumsqr(self.var_q)
        self.smooth_cost = casadi.sumsqr(self.var_q - self.var_q_last)

        # Setting optimization constraints and goals
        self.opti.subject_to(self.opti.bounded(
            self.reduced_robot.model.lowerPositionLimit,
            self.var_q,
            self.reduced_robot.model.upperPositionLimit)
        )
        self.opti.minimize(50 * self.translational_cost + self.rotation_cost + 0.02 * self.regularization_cost + 0.1 * self.smooth_cost)

        opts = {
            'ipopt':{
                'print_level':0,
                'max_iter':50,
                'tol':1e-6
            },
            'print_time':False,# print or not
            'calc_lam_p':False # https://github.com/casadi/casadi/wiki/FAQ:-Why-am-I-getting-%22NaN-detected%22in-my-optimization%3F
        }
        self.opti.solver("ipopt", opts)

        self.init_data = np.zeros(self.reduced_robot.model.nq)
        self.smooth_filter = WeightedMovingFilter(np.array([0.4, 0.3, 0.2, 0.1]), 14)
        self.vis = None

        if self.visualization:
            # Initialize the Meshcat visualizer for visualization
            self.vis = MeshcatVisualizer(self.reduced_robot.model, self.reduced_robot.collision_model, self.reduced_robot.visual_model)
            self.vis.initViewer(open=True) 
            self.vis.loadViewerModel("pinocchio") 
            self.vis.displayFrames(True, frame_ids=[101, 102], axis_length = 0.15, axis_width = 5)
            self.vis.display(pin.neutral(self.reduced_robot.model))

            # Enable the display of end effector target frames with short axis lengths and greater width.
            frame_viz_names = ['L_ee_target', 'R_ee_target']
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
                self.vis.viewer[frame_viz_name].set_object(
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

    def solve_ik(self, left_wrist, current_lr_arm_motor_q = None, current_lr_arm_motor_dq = None):
        if current_lr_arm_motor_q is not None:
            self.init_data = current_lr_arm_motor_q
        self.opti.set_initial(self.var_q, self.init_data)

        R_target = pin.SE3(pin.Quaternion(1, 0, 0, 0), np.array([0.25, -0.25, 0.1]))
        right_wrist = R_target.homogeneous
        self.opti.set_value(self.param_tf_l, left_wrist)
        self.opti.set_value(self.param_tf_r, right_wrist)
        self.opti.set_value(self.var_q_last, self.init_data) # for smooth


        sol = self.opti.solve()
        # sol = self.opti.solve_limited()

        sol_q = self.opti.value(self.var_q)
        self.smooth_filter.add_data(sol_q)
        sol_q = self.smooth_filter.filtered_data

        if current_lr_arm_motor_dq is not None:
            v = current_lr_arm_motor_dq * 0.0
        else:
            v = (sol_q - self.init_data) * 0.0

        self.init_data = sol_q

        # Calculate Feedforward Torques
        # Uses Recursive Newton-Euler Algorithm (RNEA) to compute the inverse dynamics.
        sol_tauff = pin.rnea(self.reduced_robot.model, self.reduced_robot.data, sol_q, v, np.zeros(self.reduced_robot.model.nv))

        if self.visualization:
            self.vis.display(sol_q)  # for visualization, set the robot's joints

        return sol_q, sol_tauff
        


printed = False
def print_once(string):
    global printed
    if not printed:
        print(string)
        printed = True


def interpolate_se3(start, end, alpha):
    # Interpolate translation linearly
    interp_translation = (1 - alpha) * start.translation + alpha * end.translation

    # Slerp (spherical linear interpolation) for rotation
    start_quat = pin.Quaternion(start.rotation)
    end_quat = pin.Quaternion(end.rotation)
    interp_quat = start_quat.slerp(alpha, end_quat)

    return pin.SE3(interp_quat.matrix(), interp_translation)


import meshcat.geometry as g

if __name__ == "__main__":
    # 这里直接开了meshcat web browser visualization
    arm_ik = G1_29_ArmIK(Unit_Test = True, Visualization = True)
    #arm_ik = H1_2_ArmIK(Unit_Test = True, Visualization = True)

    # initial positon
    # we are not moving right arm
    R_target = pin.SE3(pin.Quaternion(1, 0, 0, 0), np.array([0.25, -0.25, 0.1]))

    L_start = pin.SE3(pin.Quaternion(1, 0, 0, 0), np.array([0.25, 0.25, 0.1]))
    L_target = pin.SE3(pin.Quaternion(1, 0, 0, 0), np.array([0.4, 0.1, 0.3]))

    # 可视化一个axis和一个红球在目标位置

    arm_ik.vis.viewer["L_ee_target/sphere"].set_object(g.Sphere(0.05), g.MeshLambertMaterial(color=0xff0000))
    arm_ik.vis.viewer["L_ee_target/axes"].set_object(g.triad(scale=0.1))
    arm_ik.vis.viewer["L_ee_target"].set_transform(L_target.homogeneous)

    # 这里会以100Hz计算IK，把左手从初始位置移动到一个目标位置，然后回来，丝滑

    user_input = input("Please enter the start signal (enter 's' to start the subsequent program):\n")
    if user_input.lower() == 's':

        step = 0
        max_steps = 240

        while True:
            # Normalize step to [0, 1] range for interpolation
            alpha = (step % max_steps) / max_steps
             # Move forward for first half, backward for second half
            if alpha <= 0.5:
                alpha *= 2  # Scale alpha to [0, 1] for first phase
            else:
                alpha = 2 * (1 - alpha)  # Reverse alpha for the second phase


            # Interpolate left end-effector smoothly
            L_tf_target = interpolate_se3(L_start, L_target, alpha)

            # Right end-effector remains fixed
            R_tf_target = R_target

            # both list of 14
            sol_q, sol_tauff = arm_ik.solve_ik(L_tf_target.homogeneous, R_tf_target.homogeneous)
            print_once(sol_q)

            step += 1
            if step > max_steps:
                step = 0
            time.sleep(0.01)
