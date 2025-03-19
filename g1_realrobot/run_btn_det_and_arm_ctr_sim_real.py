# coding=utf-8

import cv2
import sys
import argparse
import time
import datetime
import numpy as np
import pickle
import copy

from ultralytics import YOLO

import threading  # run the arm control async

from calibrate_intrinsics_depthcam import DepthCamera
from calibrate_intrinsics_depthcam import image_resize
from robot_arm_ik import  G1_29_ArmIK
from robot_arm_high_level import G1_29_ArmController

import meshcat.geometry as g
import pinocchio as pin
import time
from scipy.spatial.transform import Rotation as R
from pinocchio import casadi as cpin
from pinocchio.robot_wrapper import RobotWrapper
from pinocchio.visualize import MeshcatVisualizer

parser = argparse.ArgumentParser()

parser.add_argument("det_model", default="combtn59.pt")
parser.add_argument("urdf")
parser.add_argument("network_name", help="network name that connects 192.168.123.*")
#
parser.add_argument("--is_realsense", action="store_true", help="if not then orbbec")
parser.add_argument("--camera_type", default="d455")

parser.add_argument("--ee_link_name", default="ee_link")

parser.add_argument("--det_conf", type=float, help="confidence score threshold", default=0.3)
parser.add_argument("--target_btn_class", default="(")
parser.add_argument("--det_all", action="store_true", help="do all detection results instead of just target class")
parser.add_argument("--keep_last", action="store_true", help="keep the detected location from before")
parser.add_argument("--use_tracking", action="store_true")


"""
'<>' -> 'open'
'><' -> 'close'
'$'  -> 'alarm'
'#'  -> 'stop'
'^'  -> 'call'
'('  -> 'up'
')'  -> 'down'
'()' -> 'updown'
's'  -> 'star'
'-'  -> '-'
"""
"""
    假设URDF准，直接算eye-to-hand
        (g1) junweil@home-lab:~/projects/humanoid_teleop$ python g1_realrobot/urdf_viewer_compute_ft.py avp_teleoperate/assets/g1/g1_body29_inspired_hand.urdf

                    Transformation from pelvis to d435_link:
                     [[ 0.67430239  0.          0.73845534  0.05366   ]
                     [ 0.          1.          0.          0.01753   ]
                     [-0.73845534  0.          0.67430239  0.47387   ]
                     [ 0.          0.          0.          1.        ]]

                    Transformation from right_wrist_yaw_joint to R_index_tip:
                     [[ 2.22018339e-16  9.99391313e-01 -3.48855737e-02  2.48686587e-01]
                     [-1.00000000e+00  2.23989393e-16  5.02256656e-17  7.32847000e-03]
                     [-5.80145042e-17  3.48855737e-02  9.99391313e-01  2.97837118e-02]
                     [ 0.00000000e+00  0.00000000e+00  0.00000000e+00  1.00000000e+00]]
"""
# eye-to-base,
T_base_to_camera = np.array([[ 0.67430239, 0.   , 0.73845534, 0.05366   ],
                             [ 0. , 1. , 0. , 0.01753   ],
                             [-0.73845534, 0. , 0.67430239, 0.47387   ],
                             [ 0. , 0.  ,0.,   1.        ]])
# realsense里x往右，y朝下，z朝前；robot frame，x朝前，y朝左，z朝上
T_camera_to_camera = np.array([
            [0.,  0.,  1,  0],
            [-1., 0,  0,  0],
            [0., -1.,  0,  0],
            [0.,  0.,  0,  1]
        ])
T_base_to_camera = T_base_to_camera @ T_camera_to_camera

# arm to ee
# Transformation from right_wrist_yaw_joint to R_index_tip:
# our ik assume fixing all others
# this is used in robot_arm_ik.py
T_arm_to_ee = np.array([[ 2.22018339e-16, 9.99391313e-01, -3.48855737e-02,  2.48686587e-01],
                         [-1.00000000e+00,  2.23989393e-16,  5.02256656e-17,  7.32847000e-03],
                         [-5.80145042e-17,  3.48855737e-02,  9.99391313e-01,  2.97837118e-02],
                         [ 0.00000000e+00,  0.00000000e+00,  0.00000000e+00,  1.00000000e+00]])



class DetDepthModel:
    def __init__(self, det_model_path, camera_type="d435", is_realsense=True,
            det_conf=0.3,
            det_all=False, det_target_class="(",
            use_tracking=False):
        # initialize the detection model and the depth camera

        # initialize the object detection model
        # this will auto download the YOLOv9 checkpoint
        # see here for all the available models: https://docs.ultralytics.com/models/yolov9/#performance-on-ms-coco-dataset
        self.det_model = YOLO(det_model_path)
        self.det_conf = det_conf
        self.det_all = det_all
        self.det_target_class=det_target_class
        self.use_tracking = use_tracking


        self.camera_obj = DepthCamera(
            is_realsense=is_realsense, camera_type=camera_type)

        # for FPS computation
        self.frame_count = 0
        self.start_time = time.time()


    def run_od_and_return_frame(self, visualize_box=True, visualize_depth=False):
        # get one frame from stream and run object detection
        # then return the visualization image
        return_frame, det_results = None, None
        depth_data, color_data = self.camera_obj.get_data()

        if depth_data is None or color_data is None:
            return return_frame, det_results

        self.frame_count += 1


        #print(depth_data[depth_data != 0]) # in 毫米
        #print(depth_data.shape) # (960, 1280)
        #print(color_data.shape) # (960, 1280, 3)

        if self.det_all:
            target_class_list = None  # detect all the class and visualize
        else:
            # only detect and visualize the target class
            target_class_id = self.find_det_class_id(self.det_target_class)
            assert target_class_id is not None, "target class %s not found in det model" % self.det_target_class
            target_class_list = [target_class_id]

        if self.use_tracking:
            # detection result include center depth for each object
            frame, det_results = self.run_tracking_on_image_and_depth(
                color_data, depth_data,
                classes=target_class_list,
                visualize=visualize_box,
                conf=self.det_conf)
        else:
            # detection result include center depth for each object
            frame, det_results = self.run_od_on_image_and_depth(
                color_data, depth_data,
                classes=target_class_list,
                visualize=visualize_box,
                conf=self.det_conf)

        # -------- FPS and frame timestamp visualization

        # put a timestamp for the frame for possible synchronization
        # and a frame index to look up depth data
        date_time = str(datetime.datetime.now())
        frame = cv2.putText(
            frame, "#%d: %s" % (self.frame_count, date_time),
            (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
            fontScale=1, color=(0, 0, 255), thickness=2)

        # show the fps
        current_time = time.time()

        fps = self.frame_count / (current_time - self.start_time)
        frame = cv2.putText(
            frame, "FPS: %d" % int(fps),
            (10, 350), cv2.FONT_HERSHEY_SIMPLEX,
            fontScale=1, color=(0, 0, 255), thickness=2)

        # ---- add the depth image visualization

        if visualize_depth:
            # Apply colormap on depth image (image must be converted to 8-bit per pixel first)
            depth_colormap = cv2.applyColorMap(
                cv2.convertScaleAbs(depth_data*1000., alpha=0.03), cv2.COLORMAP_JET)
            # Stack both images horizontally
            frame = np.hstack((frame, depth_colormap))
            #frame = image_resize(frame, width=1920, height=None) # for Gemini 336L
            frame = self.image_resize(frame, width=1280, height=None) # for Femoto Bolt

        return_frame = frame
        return return_frame, det_results


    def run_od_on_image_and_depth(self,
        frame_cv2,
        depth_data,
        classes=None, conf=0.3,
        visualize=True,
        bbox_thickness=4, text_thickness=2, font_size=2):
        """
            Run object detection inference and visualize in the image.
            Return: the visualization image and the detection results (with each box's center depth)
        """

        # see here for inference arguments
        # https://docs.ultralytics.com/modes/predict/#inference-arguments
        results = self.det_model.predict(
            frame_cv2,
            classes=classes,  # you can specify the classes you want
            # see here for coco class indexes [0-79], 0 is person: https://gist.github.com/AruniRC/7b3dadd004da04c80198557db5da4bda
            #classes=[0, 32], # detect person and sports ball only
            conf=conf, verbose=False)

        # see here for the API documentation of results
        # https://docs.ultralytics.com/modes/predict/#working-with-results
        result = results[0] # we run it on single image
        det_results = []  # should be [bbox, center_xy, class_id, class_name]
        for box in result.boxes:

            center_x = float((box.xyxy[0][0] + box.xyxy[0][2])/2.)
            center_y = float((box.xyxy[0][1] + box.xyxy[0][3])/2.)
            bbox = [x for x in box.xyxy[0]]
            conf = float(box.conf[0].cpu())

            class_id = int(box.cls[0])
            class_name = result.names[int(box.cls[0])]

            # in milimeters
            #depth = depth_data[round(center_y), round(center_x)]
            #point_3d = self.deproject_pixel_to_point([center_x, center_y], depth)
            point_3d = self.camera_obj.deproject_pixel_to_point([center_x, center_y], depth_data)

            det_results.append([bbox, point_3d, class_id, class_name, conf])

            if visualize:
                bbox = [int(x) for x in bbox]
                bbox_color = (0, 255, 0) # BGR
                frame_cv2 = cv2.rectangle(
                        frame_cv2,
                        tuple(bbox[0:2]), tuple(bbox[2:4]),
                        bbox_color, bbox_thickness)

                frame_cv2 = cv2.putText(
                        frame_cv2, "%s:%.2f" % (class_name, conf),
                        (bbox[0], bbox[1] - 10),  # specify the bottom left corner
                        cv2.FONT_HERSHEY_PLAIN, font_size,
                        bbox_color, text_thickness)



        return frame_cv2, det_results

    def run_tracking_on_image_and_depth(self,
        frame_cv2,
        depth_data,
        classes=None, conf=0.3,
        visualize=True,
        bbox_thickness=4, text_thickness=2, font_size=2):
        """
            Run object detection inference and visualize in the image.
            Return: the visualization image and the detection results (with each box's center depth)
        """

        # see here for inference arguments
        # https://docs.ultralytics.com/modes/predict/#inference-arguments
        results = self.det_model.track(
            frame_cv2,
            tracker="bytetrack.yaml",
            classes=classes,  # you can specify the classes you want
            # see here for coco class indexes [0-79], 0 is person: https://gist.github.com/AruniRC/7b3dadd004da04c80198557db5da4bda
            #classes=[0, 32], # detect person and sports ball only
            conf=conf, verbose=False,
            iou=0.5, #NMS. Lower values result in fewer detections by eliminating overlapping boxes
            persist=True)

        # see here for the API documentation of results
        # https://docs.ultralytics.com/modes/predict/#working-with-results
        result = results[0] # we run it on single image
        det_results = []  # should be [bbox, center_xy, class_id, class_name]

        # Get the boxes and track IDs for ploting the lines
        boxes = result.boxes.xywh.cpu()
        # only visualize when there are tracks
        if result.boxes.id is not None:
            boxes_xyxy = result.boxes.xyxy.cpu()
            track_ids = result.boxes.id.int().cpu().tolist()
            confs = result.boxes.conf.float().cpu().tolist()
            classes = result.boxes.cls.int().cpu().tolist()

            for box, box_xyxy, track_id, cls_id, conf in zip(boxes, boxes_xyxy, track_ids, classes, confs):
                center_x, center_y, w, h = box
                center_x, center_y = float(center_x), float(center_y)
                x1, y1, x2, y2 = box_xyxy

                bbox = [x1, y1, x2, y2]

                class_id = cls_id
                class_name = result.names[cls_id]

                # in meters
                #depth = depth_data[round(center_y), round(center_x)]
                #point_3d = self.deproject_pixel_to_point([center_x, center_y], depth)
                point_3d = self.camera_obj.deproject_pixel_to_point([center_x, center_y], depth_data)

                det_results.append([bbox, point_3d, class_id, class_name, conf])

                if visualize:
                    bbox = [int(x) for x in bbox]
                    bbox_color = (0, 255, 0) # BGR
                    frame_cv2 = cv2.rectangle(
                            frame_cv2,
                            tuple(bbox[0:2]), tuple(bbox[2:4]),
                            bbox_color, bbox_thickness)

                    frame_cv2 = cv2.putText(
                            frame_cv2, "%s:%.2f" % (class_name, conf),
                            (bbox[0], bbox[1] - 10),  # specify the bottom left corner
                            cv2.FONT_HERSHEY_PLAIN, font_size,
                            bbox_color, text_thickness)



        return frame_cv2, det_results
    # ----- the rest are helper functions

    def find_det_class_id(self, class_name):
        target_id = None
        class_names = self.det_model.names
        #print(class_names)  # {0: '3', 1: '2', 2: 's1', 3: '*', ..}
        for i in range(len(class_names)):
            if class_names[i] == class_name:
                target_id = i
                break
        return target_id



    def image_resize(self, image, width = None, height = None, inter = cv2.INTER_AREA):
        # initialize the dimensions of the image to be resized and
        # grab the image size
        dim = None
        (h, w) = image.shape[:2]

        # if both the width and height are None, then return the
        # original image
        if width is None and height is None:
            return image

        # check to see if the width is None
        if width is None:
            # calculate the ratio of the height and construct the
            # dimensions
            r = height / float(h)
            dim = (int(w * r), height)

        # otherwise, the height is None
        else:
            # calculate the ratio of the width and construct the
            # dimensions
            r = width / float(w)
            dim = (width, int(h * r))

        # resize the image
        resized = cv2.resize(image, dim, interpolation = inter)

        # return the resized image
        return resized


printed = False
def print_once(string):
    global printed
    if not printed:
        print(string)
        printed = True

def camera_frame_to_robot_frame(xyz_in_camera):
    # assuming the T_base_to_camera is given. See above
    P_camera = np.array(xyz_in_camera)

    # Convert to homogeneous coordinates
    P_camera_homogeneous = np.append(P_camera, 1)  # [X, Y, Z, 1]

    # Transform to robot base frame
    P_base_homogeneous = T_base_to_camera @ P_camera_homogeneous

    # Convert back to 3D coordinates
    P_base = P_base_homogeneous[:3]  # [X', Y', Z']

    return P_base

def interpolate_se3(start, end, alpha):
    # Interpolate translation linearly
    interp_translation = (1 - alpha) * start.translation + alpha * end.translation

    # Slerp (spherical linear interpolation) for rotation
    start_quat = pin.Quaternion(start.rotation)
    end_quat = pin.Quaternion(end.rotation)
    interp_quat = start_quat.slerp(alpha, end_quat)

    return pin.SE3(interp_quat.matrix(), interp_translation)



# Function to control the robot arm asynchronously
def move_robot_arm_sim_and_real(arm_ik, arm_ctr, start_pose_pin_SE3, target_pose_pin_SE3):

    # need this to tell main thread not to accept new command
    global has_reach_ee_pose
    has_reach_ee_pose = False


    start_pose = start_pose_pin_SE3
    print("moving to ", target_pose_pin_SE3)
    target_pose = target_pose_pin_SE3

    # visualize the target pose in browser
    arm_ik.vis.viewer["R_ee_target"].set_transform(target_pose.homogeneous)

    in_seconds = 1.0

    # now we start to control the arm

    time_gap = 0.01
    max_steps = int(in_seconds / time_gap)

    for step in range(max_steps):
        # Normalize step to [0, 1] range for interpolation
        alpha = (step + 1) / max_steps  # Progress forward only

        # Interpolate left end-effector smoothly
        target_tmp = interpolate_se3(start_pose, target_pose, alpha)

        current_lr_arm_q  = arm_ctr.get_current_right_arm_q()
        current_lr_arm_dq = arm_ctr.get_current_right_arm_dq()
        # both list of 7
        sol_q, sol_tauff = arm_ik.solve_ik_right_wrist(target_tmp.homogeneous, current_lr_arm_q, current_lr_arm_dq)

        arm_ctr.ctrl_dual_arm(sol_q, sol_tauff)

        time.sleep(time_gap)

    # need to check the final position of the arm and see whether it has reach target pose


    # Update kinematics to get the latest pose (update joint position and frame position)
    pin.framesForwardKinematics(arm_ik.reduced_robot.model,
                                arm_ik.reduced_robot.data,
                                sol_q) # use the last q solution to get the final pose

    ## Update the data object to reflect the new frames
    # 必须要更新这个，否则data.oMf没有这个新的frame
    #  self.reduced_robot.data = pin.Data(self.reduced_robot.model)
    assert len(arm_ik.reduced_robot.model.frames) == len(arm_ik.reduced_robot.data.oMf)

    final_pose = arm_ik.reduced_robot.data.oMf[arm_ik.R_hand_id]
    arm_ik.vis.viewer["R_ee"].set_transform(final_pose.homogeneous) # visualize the green ball as the current final pose


    # Compare position
    position_error = np.linalg.norm(final_pose.translation - target_pose.translation)

    # Compare orientation (convert to quaternions and compute difference)
    final_quat = R.from_matrix(final_pose.rotation).as_quat()
    target_quat = R.from_matrix(target_pose.rotation).as_quat()
    orientation_error = 1 - np.dot(final_quat, target_quat) ** 2  # Quaternion difference

    print(f"Position error: %.6f, Orientation error: %.6f" % (position_error, orientation_error))

    # in meters
    position_tol = 1e-2 # <1 cm error
    orientation_tol = 5e-3 #
    if position_error <= position_tol and orientation_error <= orientation_tol:
        print("✅ Target pose reached successfully!")
    else:
        print("❌ Target pose NOT reached!")



if __name__ == "__main__":

    args = parser.parse_args()


    # -----------   定义右手初始姿态
    #urdf_path = args.urdf
    down_target = np.zeros(7)
    # G1_29_JointIndex.kRightElbow
    down_target[3] = 1.57
    # G1_29_JointIndex.kRightShoulderRoll
    down_target[1] = -0.4

    # 如果想初始姿态，手下垂，即right_elbow_joint == 1.57 ，right shoulder_roll == -0.4 (外摆一点否则手碰腿)

    # assuming our robot ee is started at zero pose
    # get this from (g1) junweil@home-lab:~/projects/humanoid_teleop$ python g1_realrobot/urdf_viewer_compute_ft.py avp_teleoperate/assets/g1/g1_body29_inspired_hand.urdf
    start_ee_pose = np.array([[ 1.91593295e-04,  9.99393210e-01, -3.48306690e-02,  4.48461099e-01],
                             [-9.99999980e-01,  1.93566882e-04,  5.32902719e-05, -1.41273801e-01],
                             [ 5.99999999e-05,  3.48306581e-02,  9.99393227e-01,  1.25002439e-01],
                             [ 0.00000000e+00,  0.00000000e+00,  0.00000000e+00,  1.00000000e+00]])

    # 如果想初始姿态，手下垂，即right_elbow_joint == 1.57 ，right shoulder_roll == -0.4 (外摆一点否则手碰腿)
    start_ee_pose = np.array([[1.97862783e-04,  3.57053978e-02,  9.99362339e-01,  3.59265958e-02],
                     [-9.21037606e-01, -3.89218761e-01,  1.40884334e-02, -3.81347009e-01],
                     [ 3.89473605e-01, -9.20453084e-01,  3.28090022e-02, -2.78446472e-01],
                     [ 0.00000000e+00,  0.00000000e+00,  0.00000000e+00,  1.00000000e+00]])
    start_ee_pose = pin.SE3(start_ee_pose[:3, :3], start_ee_pose[:3, 3])

    # -------------------------

    arm_ik = G1_29_ArmIK(urdf=args.urdf, visualization=True, start_q=down_target)
    # visualize the target pose and the robot's actual pose in browser
    arm_ik.vis.viewer["R_ee_target/sphere"].set_object(g.Sphere(0.01), g.MeshLambertMaterial(color=0xff0000))
    arm_ik.vis.viewer["R_ee/sphere"].set_object(g.Sphere(0.01), g.MeshLambertMaterial(color=0x00FF00))

    arm_ctr = G1_29_ArmController(args.network_name)
    # the total time required for arms velocity to gradually increase to its maximum value
    arm_ctr.speed_gradual_max(t=1.0)

    # 把右手放初始位置，其他不管
    #arm_ctr.ctrl_right_arm_go_home()
    arm_ctr.ctrl_right_arm_go_down()
    #sys.exit()

    target_ee_pose = None
    last_ee_pose = None
    # Initialize threading objects
    robot_ctr_thread = None

    try:

        depth_det_camera_model = DetDepthModel(
            args.det_model,
            camera_type=args.camera_type,
            is_realsense=args.is_realsense,
            det_target_class=args.target_btn_class,
            det_all=args.det_all,
            use_tracking=args.use_tracking)


        target_det_is_init = False

        global stop_update_target_sphere
        stop_update_target_sphere = False # when arm is moving ,this should not be updated and meshcat might fail

        while True:
            # get one frame and run the detection
            # visualize all detections
            frame, det_results = depth_det_camera_model.run_od_and_return_frame(
                visualize_box=True, visualize_depth=False)

            # the frame will be empty when just start the program
            if frame is None:
                continue

            if not target_det_is_init:
                target_det = None
                target_det_is_init = True

            if not args.keep_last:
                target_det = None # initialize the target every frame
                target_ee_pose = None

            det_results = sorted(det_results, key=lambda x:x[4], reverse=True)
            for bbox, point_3d, class_id, class_name, conf in det_results:
                # save the button_up results
                if class_name == args.target_btn_class:
                    target_xyz_in_camera_frame_in_mm = point_3d
                    # mm to meters
                    target_xyz_in_camera_frame = [o*0.001 for o in point_3d]
                    target_det = (target_xyz_in_camera_frame, bbox, class_name, conf)
                    break

            # so we have detected a target button, visualize it
            if target_det is not None:
                bbox_thickness = 4
                text_thickness = 2
                font_size = 2
                target_xyz, bbox, class_name, conf = target_det
                center_x = float((bbox[0] + bbox[2])/2.)
                center_y = float((bbox[1] + bbox[3])/2.)
                bbox = [int(x) for x in bbox]
                bbox_color = (255, 0, 0) # BGR
                frame = cv2.rectangle(
                        frame,
                        tuple(bbox[0:2]), tuple(bbox[2:4]),
                        bbox_color, bbox_thickness)

                frame = cv2.putText(
                        frame, "%s:%.2f" % (class_name, conf),
                        (bbox[0], bbox[1] - 10),  # specify the bottom left corner
                        cv2.FONT_HERSHEY_PLAIN, font_size,
                        bbox_color, text_thickness)

                # we visualize the coordinate in Piper arm frame
                frame = cv2.putText(
                    frame,
                    "cf: [%.3f, %.3f, %.3f]" % tuple(target_xyz),
                    (round(center_x)+40, round(center_y)-50), cv2.FONT_HERSHEY_SIMPLEX,
                    fontScale=1.3, color=(0, 255, 0), thickness=4)

                # we compute the point in robot frame
                target_xyz_in_robot_frame = camera_frame_to_robot_frame(target_xyz)
                frame = cv2.putText(
                    frame,
                    "rf: [%.3f, %.3f, %.3f]" % tuple(target_xyz_in_robot_frame),
                    (round(center_x)+40, round(center_y)-10), cv2.FONT_HERSHEY_SIMPLEX,
                    fontScale=1.3, color=(0, 255, 0), thickness=4)

                # 要机器人手指ee朝着给定点的方向。ee x-axis朝右，y-axis朝前，z-axis朝上
                # 所以要ee对着给定点的话，ee的y-axis要变成robot base的x-axis, ee的x-axis的反方向是robot base的y-axis
                robot_target_rotation = np.array([[0, 1., 0.],
                                                [-1.,0.,0.],
                                                [0.,0.,1.]])
                target_ee_pose = pin.SE3(robot_target_rotation, np.array(target_xyz_in_robot_frame))

                # we visualize the target in the robot frame in the meshcat as well
                if not stop_update_target_sphere:

                    arm_ik.vis.viewer["R_ee_target"].set_transform(target_ee_pose.homogeneous)


            frame = image_resize(frame, width=900, height=None)
            cv2.imshow("frame", frame)

            pressedKey = cv2.waitKey(1) & 0xFF
            if pressedKey == ord('q'):
                break
            elif pressedKey == ord('g'): # now we command the arm to go to current ee_target pose
                if target_det is not None:

                    # Start the arm movement in a new thread
                    # make sure the previous thread is finished
                    if robot_ctr_thread is None or not robot_ctr_thread.is_alive():

                        if last_ee_pose is None:
                            last_ee_pose = start_ee_pose

                        # Make a copy of target_xyz to pass to the thread
                        target_ee_pose_copy = copy.deepcopy(target_ee_pose)
                        last_ee_pose_copy = copy.deepcopy(last_ee_pose)

                        stop_update_target_sphere = True
                        robot_ctr_thread = threading.Thread(
                            target=move_robot_arm_sim_and_real,
                            args=(arm_ik, arm_ctr, last_ee_pose_copy, target_ee_pose_copy))
                        robot_ctr_thread.start()
                        # now this become the last ee pose
                        last_ee_pose = target_ee_pose
                    else:
                        print("Arm is not ready for next move! skipping..")

            elif pressedKey == ord('h'):
                # go back to zero position
                # move the arm back to start pose
                # make sure the previous thread is finished
                if robot_ctr_thread is None or not robot_ctr_thread.is_alive():
                    if last_ee_pose is not None and last_ee_pose != start_ee_pose:

                        # position, orientation_quaterion
                        target_ee_pose = start_ee_pose

                        # Make a copy of target_xyz to pass to the thread
                        target_ee_pose_copy = copy.deepcopy(target_ee_pose)
                        last_ee_pose_copy = copy.deepcopy(last_ee_pose)

                        robot_ctr_thread = threading.Thread(target=move_robot_arm_sim_and_real,
                                args=(arm_ik, arm_ctr, last_ee_pose_copy, target_ee_pose_copy))
                        robot_ctr_thread.start()

                        # now this become the last ee pose
                        last_ee_pose = target_ee_pose
                    else:
                        print("Arm is not ready for next move! skipping..")
                else:
                    print(robot_ctr_thread.is_alive())


    #except Exception as e:
    #    print(e)

    finally:
        # Wait for the movement thread to finish if it's still running
        if robot_ctr_thread is not None and robot_ctr_thread.is_alive():
            robot_ctr_thread.join()

        # release window
        depth_det_camera_model.camera_obj.pipeline.stop()
        cv2.destroyAllWindows()
