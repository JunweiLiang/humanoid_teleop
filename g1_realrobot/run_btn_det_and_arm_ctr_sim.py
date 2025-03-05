# coding=utf-8

import cv2
import sys
import argparse
import time
import datetime
import numpy as np

from ultralytics import YOLO

import threading  # run the arm control async

from calibrate_intrinsics_depthcam import DepthCamera


parser = argparse.ArgumentParser()

parser.add_argument("det_model", default="combtn59.pt")
parser.add_argument("urdf")

#
parser.add_argument("--is_realsense", action="store_true", help="if not then orbbec")
parser.add_argument("--camera_type", default="d455")

parser.add_argument("--ee_link_name", default="ee_link")

parser.add_argument("--det_conf", type=float, help="confidence score threshold", default=0.3)
parser.add_argument("--target_btn_class", default="(")
parser.add_argument("--det_all", action="store_true", help="do all detection results instead of just target class")
parser.add_argument("--keep_last", action="store_true", help="keep the detected location from before")
parser.add_argument("--use_tracking", action="store_true")

parser.add_argument("--delta_x", default=0., type=float, help="adding more +x (meters) to the camera frame to arm frame conversion")
parser.add_argument("--delta_y", default=0., type=float, help="adding more +y (meters) to the camera frame to arm frame conversion")
parser.add_argument("--delta_z", default=0., type=float, help="adding more +z (meters) to the camera frame to arm frame conversion")
parser.add_argument("--set_x", default=-100., type=float, help="setting this to be non -100 will overwrite any computation")
parser.add_argument("--set_y", default=-100., type=float, help="setting this to be non -100 will overwrite any computation")
parser.add_argument("--set_z", default=-100., type=float, help="setting this to be non -100 will overwrite any computation")


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


class DetDepthModel:
    def __init__(self, det_model_path, camera_type="d435", is_realsense=True,
            det_conf=0.3, xyz_delta=(0., 0., 0.),
            det_all=False, det_target_class="(",
            use_tracking=False,
            set_xyz=None):
        # initialize the detection model and the depth camera

        # initialize the object detection model
        # this will auto download the YOLOv9 checkpoint
        # see here for all the available models: https://docs.ultralytics.com/models/yolov9/#performance-on-ms-coco-dataset
        self.det_model = YOLO(det_model_path)
        self.det_conf = det_conf
        self.det_all = det_all
        self.det_target_class=det_target_class
        self.set_xyz = set_xyz
        self.use_tracking = use_tracking


        self.camera_obj = DepthCamera(
            is_realsense=is_realsense, camera_type=camera_type)

        # for FPS computation
        self.frame_count = 0
        self.start_time = time.time()
        assert len(xyz_delta) == 3
        self.xyz_delta = xyz_delta

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

                # we visualize the coordinate in Piper arm frame
                # visualize in the outer loop
                """
                piper_point = self.camera_frame_to_arm_frame(point_3d)
                frame_cv2 = cv2.putText(
                    frame_cv2,
                    "[%d, %d, %d]mm" % (piper_point[0], piper_point[1], piper_point[2]),
                    (round(center_x)+40, round(center_y)-50), cv2.FONT_HERSHEY_SIMPLEX,
                    fontScale=1.3, color=(0, 255, 0), thickness=4)
                """

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

                    # we visualize the coordinate in Piper arm frame
                    # visualize in the outer loop
                    """
                    piper_point = self.camera_frame_to_arm_frame(point_3d)
                    frame_cv2 = cv2.putText(
                        frame_cv2,
                        "[%d, %d, %d] mm" % (piper_point[0], piper_point[1], piper_point[2]),
                        (round(center_x)+40, round(center_y)-50), cv2.FONT_HERSHEY_SIMPLEX,
                        fontScale=1.3, color=(0, 255, 0), thickness=4)
                    """

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

    def camera_frame_to_arm_frame(self, xyz_in_camera):
        # https://www.orbbec.com/documentation/femto-bolt-coordinate-systems
        # in femoto bolt, the aligned frames are on the RGB camera
        # for gemini 336l: https://www.orbbec.com/docs/g330-coordinate-systems/
        #   the origin is on the right camera on gemini 336l
        # the xyz are in meters
        # this is the transform from zero positioned arm's camera to the arm base frame
        # the end effector offset is [0.05, 0, 0.2]
        initial_transform = [0.02, 0, 0.25]
        # the end effector zero position at the begining
        # default it should be all zeros
        xyz_zero_pos = [0., 0., 0.]
        x_in_arm_frame = xyz_in_camera[2] + initial_transform[0] + xyz_zero_pos[0] + self.xyz_delta[0]
        y_in_arm_frame = -xyz_in_camera[0] + initial_transform[1] + xyz_zero_pos[1] + self.xyz_delta[1]
        z_in_arm_frame = -xyz_in_camera[1] + initial_transform[2] + xyz_zero_pos[2] + self.xyz_delta[2]
        if self.set_xyz is not None:
            # overwrite if set
            # sometimes the depth is just not right
            if self.set_xyz[0] != -100.:
                x_in_arm_frame = self.set_xyz[0]
            if self.set_xyz[1] != -100.:
                y_in_arm_frame = self.set_xyz[1]
            if self.set_xyz[2] != -100.:
                z_in_arm_frame = self.set_xyz[2]
        return [
            x_in_arm_frame,
            y_in_arm_frame,
            z_in_arm_frame,
        ]


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



# Function to control the robot arm asynchronously
def move_robot_arm(arm_ctr, piper_ctr, target_xyz_arm):

    # assuming our target rotation to be leveled
    roll = 0
    pitch = 0
    yaw = 0

    # Compute inverse kinematics solution
    solution_q, succeed, err = arm_ctr.solve_pink(np.array([roll, pitch, yaw] + target_xyz_arm))

    if not succeed:
        # we do not exit even if ik is not converged
        print("warning, ik compute not converged. err:%s > 0.001" % err)

    print("joint pos", solution_q)
    target_j6_degrees = np.degrees(solution_q).tolist()
    print("pos degrees: ", target_j6_degrees)

    # now we start to control the arm

    # 零位
    piper_ctr.to_zero(speed=80)

    # execute the command in k second
    piper_ctr.to_j6(target_j6_degrees, 6.0, speed=40)

    piper_ctr.to_zero(speed=80)

if __name__ == "__main__":
    args = parser.parse_args()

    #urdf_path = args.urdf
    # the xyz overwrites for the button. Use when z is not accurate for example
    set_xyz = [args.set_x, args.set_y, args.set_z]

    #arm_ctr = ArmControl(urdf=urdf_path, ee_link_name=args.ee_link_name)

    #zero_j6_degrees = [0, 0, 0, 0, 0, 0]

    #piper_ctr = PiperControl(print_msg=False, zero_pos=zero_j6_degrees)

    # 先零位，使能机械臂
    #piper_ctr.to_zero(speed=80)

    # Initialize threading objects
    robot_ctr_thread = None
    #lock = threading.Lock()

    try:

        depth_det_camera_model = DetDepthModel(
            args.det_model,
            camera_type=args.camera_type,
            is_realsense=args.is_realsense,
            det_target_class=args.target_btn_class,
            det_all=args.det_all,
            set_xyz=set_xyz,
            use_tracking=args.use_tracking,
            xyz_delta=(args.delta_x, args.delta_y, args.delta_z))


        target_xyz_is_init = False
        while True:
            # get one frame and run the detection
            frame, det_results = depth_det_camera_model.run_od_and_return_frame(
                visualize_box=True, visualize_depth=False)

            # the frame will be empty when just start the program
            if frame is None:
                continue

            if not target_xyz_is_init:
                target_xyz = None
                target_xyz_det = None
                target_xyz_is_init = True

            if not args.keep_last:
                target_xyz = None # initialize the target every frame
                target_xyz_det = None

            det_results = sorted(det_results, key=lambda x:x[4], reverse=True)
            for bbox, point_3d, class_id, class_name, conf in det_results:

                # save the button_up results
                if class_name == args.target_btn_class:
                    target_xyz_in_camera_frame_in_mm = point_3d
                    # mm to meters
                    target_xyz_in_camera_frame = [o*0.001 for o in point_3d]
                    target_xyz_det = target_xyz_in_camera_frame
                    # now we convert the button coordinates in camera frame
                    # to the arm world frame, so we can use it to compute ik
                    #target_xyz = depth_det_camera_model.camera_frame_to_arm_frame(target_xyz_in_camera_frame)
                    target_xyz_det = (bbox, class_name, conf)
                    break

            # visualize the target_xyz_in_camera frame again if Not None
            if target_xyz is not None:
                bbox_thickness = 4
                text_thickness = 2
                font_size = 2
                bbox, class_name, conf = target_xyz_det
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
                    "[%.3f, %.3f, %.3f]" % (target_xyz[0], target_xyz[1], target_xyz[2]),
                    (round(center_x)+40, round(center_y)-50), cv2.FONT_HERSHEY_SIMPLEX,
                    fontScale=1.3, color=(0, 255, 0), thickness=4)

            cv2.imshow("frame", frame)

            pressedKey = cv2.waitKey(1) & 0xFF
            if pressedKey == ord('q'):
                break
            elif pressedKey == ord('g'):
                if target_xyz is not None:

                    # Start the arm movement in a new thread
                    # make sure the previous thread is finished
                    if robot_ctr_thread is None or not robot_ctr_thread.is_alive():

                        print("ok, will move to button %s" % target_xyz)

                        # Make a copy of target_xyz to pass to the thread
                        target_xyz_copy = target_xyz[:]

                        #robot_ctr_thread = threading.Thread(target=move_robot_arm, args=(arm_ctr, piper_ctr, target_xyz_copy,))
                        #robot_ctr_thread.start()
                    else:
                        print("Arm is not ready for next move! skipping..")


    except Exception as e:
        print(e)

    finally:
        # Wait for the movement thread to finish if it's still running
        if robot_ctr_thread is not None and robot_ctr_thread.is_alive():
            robot_ctr_thread.join()

        # release window
        depth_det_camera_model.camera_obj.pipeline.stop()
        cv2.destroyAllWindows()
