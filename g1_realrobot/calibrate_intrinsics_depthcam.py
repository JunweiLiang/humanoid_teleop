# coding=utf-8
# simple execise to compute intrinsics and compare with the provided ones

# you can install cv2 with $ pip install opencv-python
import cv2

import sys
import argparse
import numpy as np
import time
import datetime


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


parser = argparse.ArgumentParser()

parser.add_argument("--is_realsense", action="store_true", help="if not then orbbec")
parser.add_argument("--camera_type", default="gemini", help="gemini,d435,d455,femto")
parser.add_argument("--save_param_npz", default=None, help=".npz file to save the intrinsics")

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

printed = False
def print_once(string):
    global printed
    if not printed:
        print(string)
        printed = True

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

            self.camera_param = None # will set when load the frame

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
                    self.camera_param = depth_frame.profile.as_video_stream_profile().intrinsics
                # Convert images to numpy arrays
                depth_data = np.asanyarray(depth_frame.get_data())
                color_data = np.asanyarray(color_frame.get_data())

            else:
                # unlike realsense, the frames should be aligned by now
                aligned_frames = frames
                #print("getting frames...")
                depth_frame = aligned_frames.get_depth_frame()
                color_frame = aligned_frames.get_color_frame()

                if depth_frame and color_frame:

                    # Convert images to numpy arrays


                    color_data = self.get_orbbec_color_data(color_frame)
                    #print(color_data.shape)
                    depth_data = self.get_orbbec_depth_data(depth_frame)
                    #print(depth_data.shape)

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

        print(width)
        data = orbbec_depth_frame.get_data()
        print("ok")
        depth_data = np.frombuffer(orbbec_depth_frame.get_data(), dtype=np.uint16, copy=True)
        print(height)
        depth_data = depth_data.reshape((height, width), order='C')
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

    # stuff needed for calibration
    # termination criteria
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
    square_size = 1 # in mm # this does not matter, the intrinsics will be the same
    # prepare object points, like (0,0,0), (1,0,0), (2,0,0) ....,(6,5,0)
    objp = np.zeros((6*7, 3), np.float32)
    objp[:, :2] = np.mgrid[0:7, 0:6].T.reshape(-1, 2)
    #print(self.objp) # (0,0,0), (1,0,0), (2,0,0) ....,(6,5,0)
    # so all object point are square_size apart, which is in mm
    objp *= square_size # now (0,0,0), (1*25,0,0), (2*25,0,0) ....,(6*25,5*25,0)

    # Arrays to store object points and image points from all the images.
    objpoints = [] # 3d point in real world space
    imgpoints = [] # 2d points in image plane.


    print("Now we start the camera stream to calibrate. Place a chessboard in camera view in the next 5 seconds. move it around to cover the field of view of the camera to make it more accurate")
    start_time = time.time()
    frame_count = 0
    try:
        # we take K frames in 5 seconds to capture multiple chessboard image for calibration
        cal_frame_time = 5. # seconds
        cal_frame_gap = 0.05 # seconds
        cal_frame_count = int(cal_frame_time / cal_frame_gap)
        for i in range(cal_frame_count):
            time.sleep(cal_frame_gap)

            # Wait for a coherent pair of frames: depth and color
            # get the numpy data
            depth_data, color_data = camera_obj.get_data()

            if depth_data is None or color_data is None:
                continue

            frame_count += 1
            print_once("intrinsics: %s, colordata shape: %s, depth data shape:%s" % (
                camera_obj.camera_param,
                depth_data.shape,
                color_data.shape))

            # start saving calibration data
            gray = cv2.cvtColor(color_data, cv2.COLOR_BGR2GRAY)
            # Find the chess board corners
            #   this is slow
            # 需要放很近，整个棋盘在1280x800的区域内，才能识别到
            cret, corners = cv2.findChessboardCorners(gray, (7, 6), None)

            img = color_data
            if cret == True:
                #print("found chessboard! %s" % i)
                # found the chessboard
                # so append the world coordinate points (they are the same on the same chessboard)
                objpoints.append(objp)

                corners2 = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
                # get the 2D points
                imgpoints.append(corners)

                # visualize the recognized chessboard
                img = cv2.drawChessboardCorners(img, (7, 6), corners2, cret)

            # Apply colormap on depth image (image must be converted to 8-bit per pixel first)
            # depth data in mm
            depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(depth_data, alpha=0.03), cv2.COLORMAP_JET)

            # Stack both images horizontally
            image = np.hstack((img, depth_colormap))
            image = image_resize(image, width=1280, height=None)
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

        # now that we have capture world coordinate pairs and 2D pairs, do calibration
        if objpoints:
            ret, mtx, distort, rvecs, tvecs = cv2.calibrateCamera(objpoints, imgpoints, gray.shape[::-1], None, None)
            """
                 [fx  0 cx]
             K = [ 0 fy cy]
                 [ 0  0  1]
            mtx:
                 [[610.86532165   0.         645.99930246]
                 [  0.         628.81669956 419.23556542]
                 [  0.           0.           1.        ]]
            """
            # compute the reproj error to get an idea of this calibration
            """ # 这个看不出当前calibration结果的准确度
            mean_error = 0
            for i in range(len(objpoints)):
                imgpoints2, _ = cv2.projectPoints(objpoints[i], rvecs[i], tvecs[i], mtx, distort)
                error = cv2.norm(imgpoints[i], imgpoints2, cv2.NORM_L2)/len(imgpoints2)
                mean_error += error
            print("mean reproj error from %s points: %s" % (len(objpoints), mean_error))
            """

            print("camera param from device: %s" % camera_obj.camera_param)
            print("computed: mtx: %s, distort: %s " % (mtx, distort))
            if args.save_param_npz is not None:
                print("saved camera parameters to %s" % args.save_param_npz)
                np.savez(args.save_param_npz, mtx=mtx, dist=distort, rvecs=rvecs, tvecs=tvecs)
        else:
            print("No chessboard captured!")


    finally:
        camera_obj.pipeline.stop()
        cv2.destroyAllWindows()
