# coding=utf-8
# simple execise to compute intrinsics and compare with the provided ones

# you can install cv2 with $ pip install opencv-python
import cv2

import sys
import argparse
import numpy as np
import time
import datetime

np.set_printoptions(suppress=True, precision=3)

# pip install pyrealsense2
import pyrealsense2 as rs

# install pyorbbecs through here:
# https://github.com/orbbec/pyorbbecsdk
# need to build a local wheel

from pyorbbecsdk import Pipeline
from pyorbbecsdk import Config
from pyorbbecsdk import OBSensorType
from pyorbbecsdk import OBAlignMode
from pyorbbecsdk import OBFormat

# python -m pip install pupil-apriltags
from pupil_apriltags import Detector

parser = argparse.ArgumentParser()

parser.add_argument("--is_realsense", action="store_true", help="if not then orbbec")
parser.add_argument("--tag_size", default=0.058, help="the actual size in meters")
parser.add_argument("--camera_type", default="gemini", help="gemini,d435,d455,femto")

def image_resize(image, width = None, height = None, inter = cv2.INTER_AREA):
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

def rotation_matrix_to_euler_angles(R):
    """
    Convert a 3x3 rotation matrix to Euler angles (Yaw, Pitch, Roll).
    Assumes Z-Y-X rotation order.
    Returns angles in degrees.
    """
    # Check if R is a valid rotation matrix
    if not (np.allclose(np.dot(R, R.T), np.eye(3), atol=1e-6) and np.isclose(np.linalg.det(R), 1.0)):
        raise ValueError("Input matrix is not a valid rotation matrix")

    # Extract Euler angles
    sy = np.sqrt(R[0, 0] ** 2 + R[1, 0] ** 2)

    singular = sy < 1e-6  # Check for singularity

    if not singular:
        yaw = np.arctan2(R[1, 0], R[0, 0])  # psi
        pitch = np.arcsin(-R[2, 0])         # theta
        roll = np.arctan2(R[2, 1], R[2, 2]) # phi
    else:
        # Gimbal lock case
        yaw = np.arctan2(-R[1, 2], R[1, 1])
        pitch = np.arcsin(-R[2, 0])
        roll = 0

    # Convert to degrees
    yaw = np.degrees(yaw)
    pitch = np.degrees(pitch)
    roll = np.degrees(roll)

    # Z-Y-X
    return yaw, pitch, roll


"""
     [fx  0 cx]
 K = [ 0 fy cy]
     [ 0  0  1]
mtx:
     [[610.86532165   0.         645.99930246]
     [  0.         628.81669956 419.23556542]
     [  0.           0.           1.        ]]
"""

class DepthCamera(object):
    def __init__(self,
        is_realsense=True, camera_type="d435"):

        camera_type_to_size_fps = {
            # size and fps
            # from Intel Realsense
            "d455": {
                # specs: https://www.intelrealsense.com/depth-camera-d455/
                "rgb": (1280, 800, 30),
                "depth": (1280, 720, 30),
                # intrinsics: [ 1280x800  p[648.695 397.299]  f[643.173 642.287]  Inverse Brown Conrady [-0.0565123 0.067672 0.000208852 0.000719325 -0.0218305] ], colordata shape: (800, 1280), depth data shape:(800, 1280, 3)
            },
            "d435": {
                # specs: https://www.intelrealsense.com/depth-camera-d435/
                "rgb": (1920, 1080, 30),
                "depth": (1280, 720, 30),
                # intrinsics: [ 1920x1080  p[933.007 557.696]  f[1367.58 1367.47]  Inverse Brown Conrady [0 0 0 0 0] ], colordata shape: (1080, 1920), depth data shape:(1080, 1920, 3)
            },
            # from Orbbec
            "femto": {
                # specs: https://www.orbbec.com/products/tof-camera/femto-bolt/
                "rgb": (1280, 960, 30),
                "depth": (640, 576, 30),
            },
            "gemini": {
                # specs: https://www.orbbec.com/products/stereo-vision-camera/gemini-336l/
                "rgb": (1280, 800, 30),
                "depth": (1280, 800, 30),
            },
        }

        assert camera_type in camera_type_to_size_fps, "Undefined camera type %s" % camera_type

        # size and fps
        rgb_p = camera_type_to_size_fps[camera_type]["rgb"]
        depth_p = camera_type_to_size_fps[camera_type]["depth"]

        self.is_realsense = is_realsense
        if self.is_realsense:

            # reset the device, so we don't need to unplug -replug
            # https://github.com/IntelRealSense/librealsense/issues/6628#issuecomment-646558144
            ctx = rs.context()
            devices = ctx.query_devices()
            for dev in devices:
                dev.hardware_reset()

            # Configure RealSense pipeline for depth and RGB.
            self.pipeline = rs.pipeline()
            config = rs.config()
            config.enable_stream(rs.stream.color, rgb_p[0], rgb_p[1], rs.format.bgr8, rgb_p[2])
            config.enable_stream(rs.stream.depth, depth_p[0], depth_p[1], rs.format.z16, depth_p[2])
            profile = self.pipeline.start(config)

            depth_sensor = profile.get_device().first_depth_sensor()

            # depth_value * depth_scale -> meters
            self.depth_scale = depth_sensor.get_depth_scale()  # 0.001

            #print("Depth Scale is: " , depth_scale)
            #print("aligning depth frame to RGB frames..") # depth sensor has different extrinsics with RGB sensor
            align_to = rs.stream.color
            self.aligner = rs.align(align_to)

            #self.camera_param = None # will set when load the frame
            self.camera_param = profile.get_stream(rs.stream.color).as_video_stream_profile().get_intrinsics()
        else:

            # example from https://github.com/orbbec/pyorbbecsdk/blob/main/examples/depth_color_sync_align_viewer.py
            self.pipeline = Pipeline()
            config = Config()

            # if msg:failed to open usb device!  error: OB_USB_STATUS_ACCESS
            # https://github.com/orbbec/pyorbbecsdk/blob/main/docs/README_EN.md#faq
            color_profile = self.pipeline.get_stream_profile_list(OBSensorType.COLOR_SENSOR).get_video_stream_profile(
                rgb_p[0], rgb_p[1], OBFormat.RGB, rgb_p[2])
            depth_profile = self.pipeline.get_stream_profile_list(OBSensorType.DEPTH_SENSOR).get_video_stream_profile(
                depth_p[0], depth_p[1], OBFormat.Y16, depth_p[2])


            # color profile : 1920x1080@15_OBFormat.RGB
            # default color profile : 1280x960@30_OBFormat.MJPG
            """
            print("color profile : {}x{}@{}_{}".format(color_profile.get_width(),
                                                   color_profile.get_height(),
                                                   color_profile.get_fps(),
                                                   color_profile.get_format()))
            # default depth profile : 640x576@15_OBFormat.Y16
            print("depth profile : {}x{}@{}_{}".format(depth_profile.get_width(),
                                                   depth_profile.get_height(),
                                                   depth_profile.get_fps(),
                                                   depth_profile.get_format()))
            """

            config.enable_stream(color_profile)
            config.enable_stream(depth_profile)
            # HW_MODE does not work for Femolt Bolt/Gemini 336L
            config.set_align_mode(OBAlignMode.SW_MODE) # align depth to the color image, at 15 fps

            self.pipeline.enable_frame_sync()
            self.pipeline.start(config)

            self.camera_param = self.pipeline.get_camera_param() # intrinsics

            #scale = orbbec_depth_frame.get_depth_scale() # scale is 1.0, the HW are in milimeters
            self.depth_scale = 0.001 # I want them in meters

    def get_data(self):
        depth_data, color_data = None, None
        # return one aligned rgb frame and depth frame in numpy array
        # depth data in mm

        frames = self.pipeline.wait_for_frames(3000) # maximum delay in milliseconds

        if frames is not None:
            if self.is_realsense:
                aligned_frames = self.aligner.process(frames)
                aligned_frames.keep()  #
                depth_frame = aligned_frames.get_depth_frame()
                color_frame = aligned_frames.get_color_frame()

                if self.camera_param is None:
                    self.camera_param = color_frame.profile.as_video_stream_profile().intrinsics
                # Convert images to numpy arrays
                depth_data = np.asanyarray(depth_frame.get_data())
                color_data = np.asanyarray(color_frame.get_data())

            else:
                # unlike realsense, the frames should be aligned by now
                aligned_frames = frames

                depth_frame = aligned_frames.get_depth_frame()
                color_frame = aligned_frames.get_color_frame()

                if depth_frame and color_frame:

                    # Convert images to numpy arrays
                    depth_data = self.get_orbbec_depth_data(depth_frame)
                    color_data = self.get_orbbec_color_data(color_frame)

        return depth_data, color_data

    def get_orbbec_color_data(self, orbbec_color_frame):
        # in BGR order
        width = orbbec_color_frame.get_width()
        height = orbbec_color_frame.get_height()
        color_format = orbbec_color_frame.get_format()

        assert color_format in [OBFormat.RGB]

        if color_format == OBFormat.RGB:
            data = np.asanyarray(orbbec_color_frame.get_data())
            image = np.resize(data, (height, width, 3))
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

        return image

    def get_orbbec_depth_data(self, orbbec_depth_frame):
        # return depth in mm
        width = orbbec_depth_frame.get_width()
        height = orbbec_depth_frame.get_height()
        scale = orbbec_depth_frame.get_depth_scale() # scale is 1.0, the HW are in milimeters

        depth_data = np.frombuffer(orbbec_depth_frame.get_data(), dtype=np.uint16)
        depth_data = depth_data.reshape((height, width))
        depth_data = depth_data.astype(np.float32) * scale

        return depth_data


    def deproject_pixel_to_point(self, xy, depth_data):
        # this is the opposite process of perspective project (3D to 2D), hence "deproject"
        # see slide 23-36 from AIAA 5036 Lecture 4
        #   https://hkust-aiaa5036.github.io/spring2024/lecs.html
        # remember the key formulation: Pc = K Rt Pw (Pc is the pixel coor (homogenous), Pw is the world coor)
        # so Pw = Pc dot K (transposed), supposing we dont care about extrinsics
        depth = depth_data[round(xy[1]), round(xy[0])]  # in milimeters

        if self.is_realsense:
            point_3d = rs.rs2_deproject_pixel_to_point(self.camera_param, xy, depth)
            return point_3d
        else:
            x, y = xy
            fx, fy = self.camera_param.rgb_intrinsic.fx, self.camera_param.rgb_intrinsic.fy
            cx, cy = self.camera_param.rgb_intrinsic.cx, self.camera_param.rgb_intrinsic.cy

            # See Slide 28
            # see also https://stackoverflow.com/questions/38909696/2d-coordinate-to-3d-world-coordinate/38914061#38914061
            x_3d = depth / fx * (x - cx)
            y_3d = depth / fy * (y - cy)

            return [x_3d, y_3d, depth]





if __name__ == "__main__":
    args = parser.parse_args()

    # Assume we are connected to a depth camera
    # lazy import API for specified depth camera

    assert args.camera_type in ["d435", "d455", "gemini", "femto"]
    try:
        camera_obj = DepthCamera(
            is_realsense=args.is_realsense, camera_type=args.camera_type)
    except Exception as e:
        print(e)
        print("camera init failed.")
        sys.exit()

    # prepare some parameters for apriltag

    # camera intrinsics
    # Camera intrinsic parameters (adjust based on your camera calibration)
    if args.is_realsense:
        #print(camera_obj.camera_param.coeffs) # list of 5
        #print(camera_obj.camera_param.fx, camera_obj.camera_param.ppx)
        fx, fy = camera_obj.camera_param.fx, camera_obj.camera_param.fy
        cx, cy = camera_obj.camera_param.ppx, camera_obj.camera_param.ppy
        dist_coeffs = np.array(camera_obj.camera_param.coeffs)
    else:
        fx, fy = camera_obj.camera_param.rgb_intrinsic.fx, camera_obj.camera_param.rgb_intrinsic.fy
        cx, cy = camera_obj.camera_param.rgb_intrinsic.cx, camera_obj.camera_param.rgb_intrinsic.cy
        #<OBCameraDistortion k1=0.073824 k2=-0.100994 k3=0.040822 k4=0.000000 k5=0.000000 k6=0.000000 p1=-0.000142 p2=-0.000074>
        dist_coeffs = camera_obj.camera_param.rgb_distortion
        dist_coeffs = np.array([dist_coeffs.k1, dist_coeffs.k2, dist_coeffs.k3, dist_coeffs.p1, dist_coeffs.p2])

    camera_matrix = np.array([[fx, 0, cx],
                              [0, fy, cy],
                              [0,  0,  1]], dtype=np.float32)  # Replace with your camera intrinsics

    assert len(dist_coeffs) == 5

    # Initialize AprilTag detector
    at_detector = Detector(families="tag36h11", quad_decimate=2.0, refine_edges=True)

    # Define tag size in meters (we need this as the real-world measurement)
    #tag_size = 0.058
    tag_size = args.tag_size

    # here are the visualization options
    # Define 3D box vertices with the tag at the bottom
    half_size = tag_size / 2
    box_height = 0.05  # Height of the 3D box in meters

    # Vertices of the 3D box, tag at the bottom
    box_3d = np.array([
        [-half_size, -half_size, 0],  # Bottom face  (tag's location)
        [ half_size, -half_size, 0],
        [ half_size,  half_size, 0],
        [-half_size,  half_size, 0],
        # if below box_height is +, the 3D box will be extend below the detected tag
        [-half_size, -half_size, -box_height],  # Top face
        [ half_size, -half_size, -box_height],
        [ half_size,  half_size, -box_height],
        [-half_size,  half_size, -box_height]
    ], dtype=np.float32)

    # Define edges of the box for drawing
    box_edges = np.array([
        [0, 1], [1, 2], [2, 3], [3, 0],  # Bottom face
        [4, 5], [5, 6], [6, 7], [7, 4],  # Top face
        [0, 4], [1, 5], [2, 6], [3, 7]   # Vertical edges
    ])


    print("Now we can detect april tag. Q to exit")
    start_time = time.time()
    frame_count = 0
    try:

        while True:

            depth_data, color_data = camera_obj.get_data()

            if depth_data is None or color_data is None:
                continue

            frame_count += 1

            gray = cv2.cvtColor(color_data, cv2.COLOR_BGR2GRAY)

            # Detect AprilTags in the frame
            detections = at_detector.detect(gray, camera_params=(camera_matrix[0, 0], camera_matrix[1, 1],
                                                         camera_matrix[0, 2], camera_matrix[1, 2]),
                                                estimate_tag_pose=True,
                                                tag_size=tag_size)
            frame = color_data
            # visualize the tag
            # the coordinate system: https://github.com/AprilRobotics/apriltag?tab=readme-ov-file#coordinate-system
            # like the one as the depth camera, z axis is out from camera center to lens,
            # y pointed down, x pointed right
            # red line is x axis, green for y, blue for z
            for tag in detections:
                # Get the rotation and translation vectors
                rmat = tag.pose_R  # Already a 3x3 rotation matrix
                tvec = tag.pose_t.flatten()  # Translation vector as 1D array

                # in degrees
                yaw, pitch, roll = rotation_matrix_to_euler_angles(rmat)

                # Transform 3D box coordinates using tag pose
                transformed_points = np.dot(rmat, box_3d.T).T + tvec

                # Project points to 2D image plane
                image_points, _ = cv2.projectPoints(transformed_points, np.zeros(3), np.zeros(3), camera_matrix, dist_coeffs)
                image_points = image_points.reshape(-1, 2).astype(int)

                # Draw edges of the 3D bounding box
                for edge in box_edges:
                    start_point = tuple(image_points[edge[0]])
                    end_point = tuple(image_points[edge[1]])
                    cv2.line(frame, start_point, end_point, (0, 0, 255), 5)

                # Draw tag center and ID
                center = tuple(map(int, tag.center))
                # tvec, translation in meters
                cv2.putText(
                    frame, "ID: %s, xyz: %s" % (tag.tag_id, tvec),
                    center, cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 0, 0), 3)
                # new line
                cv2.putText(
                    frame, "ypr: %d, %d, %d" % (yaw, pitch, roll),
                    (center[0], center[1] + 30), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 0, 0), 3)

                # Draw axes to visualize the pose
                axis = np.float32([[tag_size, 0, 0],
                                   [0, tag_size, 0],
                                   [0, 0, -tag_size]]).reshape(-1, 3)

                # Project 3D points to the image plane
                imgpts, _ = cv2.projectPoints(axis, rmat, tvec, camera_matrix, dist_coeffs)

                # Define the origin and draw lines representing the axes
                origin = tuple(center)
                cv2.line(frame, origin, tuple(imgpts[0].ravel().astype(int)), (0, 0, 255), 3)  # X-axis (red)
                cv2.line(frame, origin, tuple(imgpts[1].ravel().astype(int)), (0, 255, 0), 3)  # Y-axis (green)
                cv2.line(frame, origin, tuple(imgpts[2].ravel().astype(int)), (255, 0, 0), 3)  # Z-axis (blue)

            # Apply colormap on depth image (image must be converted to 8-bit per pixel first)
            # depth data in mm
            depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(depth_data, alpha=0.03), cv2.COLORMAP_JET)

            # Stack both images horizontally
            image = np.hstack((frame, depth_colormap))
            image = image_resize(image, width=1600, height=None)
            #print_once("image shape: %s" % list(image.shape[:2]))

            # put a timestamp for the frame for possible synchronization
            # and a frame index to look up depth data
            date_time = str(datetime.datetime.now())
            image = cv2.putText(
                image, "#%d: %s" % (frame_count, date_time),
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                fontScale=1, color=(0, 0, 255), thickness=2)

            # show the fps
            current_time = time.time()

            fps = frame_count / (current_time - start_time)
            image = cv2.putText(
                image, "FPS: %d" % int(fps),
                (10, 250), cv2.FONT_HERSHEY_SIMPLEX,
                fontScale=1, color=(0, 0, 255), thickness=2)

            # Show the image
            cv2.imshow('RGB and Depth Stream', image)

            # Press 'q' to quit
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break


    finally:
        camera_obj.pipeline.stop()
        cv2.destroyAllWindows()
