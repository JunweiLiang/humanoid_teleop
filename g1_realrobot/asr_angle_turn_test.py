# coding=utf-8
# 获取方位角信息，然后控制机器人转向

import numpy as np
import threading
import time
from enum import IntEnum
import argparse
import json
from datetime import datetime
import random
import sys

from unitree_sdk2py.core.channel import ChannelPublisher, ChannelSubscriber, ChannelFactoryInitialize # dds

from unitree_sdk2py.idl.std_msgs.msg.dds_ import String_
from robot_arm_high_level_v3 import G1_Highlevel_Controller

# define the DDS topic names
angle_topic_name = "rt/speaker_angle" # 类型: std_msgs::msg::dds_::String_

parser = argparse.ArgumentParser()
parser.add_argument("--network_interface", default=None)
parser.add_argument("--max_freq", default=50.0, type=float)
parser.add_argument("--enable_robot_ctr", action="store_true", help="enable robot control")
parser.add_argument("--enable_tts", action="store_true", help="enable speaking")
parser.add_argument("--tts_api_url_port", default="office.precognition.team:50000")

class DataBuffer:
    def __init__(self):
        self.data = None
        self.lock = threading.Lock()

    def GetData(self):
        with self.lock:
            return self.data

    def SetData(self, data):
        with self.lock:
            self.data = data


class G1_29_ASR_Watcher:
    def __init__(self,
            network_interface=None,
        ):

        ChannelFactoryInitialize(0, network_interface)

        # start getting hand states
        self.asr_msg = DataBuffer()

        self.ASR_subscriber = ChannelSubscriber(angle_topic_name, String_)
        self.ASR_subscriber.Init()

        self.subscribe_asr_thread = threading.Thread(target=self._subscribe_asr)
        self.subscribe_asr_thread.daemon = True
        self.subscribe_asr_thread.start()

        while not self.asr_msg.GetData():
            time.sleep(0.01)
            print("Waiting to subscribe ASR dds...")
        print("Subscribe dds ok.")


    def _subscribe_asr(self):
        print("thread start")
        while True:
            msg = self.ASR_subscriber.Read()
            if msg is not None:
                asr_data_string = msg.data
                self.asr_msg.SetData(asr_data_string)
            time.sleep(0.01) # 100 Hz to sync the asr angle message


    def get_current_asr_string(self):
        return self.asr_msg.GetData()

def print_with_time(*args, **kwargs):
    timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    print(timestamp, *args, **kwargs)

def compute_optimal_turn(new_angle_deg):
    """
    Computes the optimal turning angle in radians for the robot to face the sound source.

    This function accounts for the microphone array's offset and coordinate system.

    Args:
        new_angle_deg (int): The angle of the sound source from the ASR system,
                           in degrees (0-360). This angle is measured clockwise
                           relative to the forward-right microphone (Mic 0).

    Returns:
        float: The shortest angle for the robot to turn, in radians.
               A positive value indicates a counter-clockwise (left) turn.
               A negative value indicates a clockwise (right) turn.
    """
    # From the code comments, we know:
    # 1. Mic 0 is at -30 degrees relative to the robot's front (to the right).
    # 2. The ASR angle (`new_angle_deg`) increases clockwise (CW).
    # 3. The robot's turn command (`rad`) is positive for a counter-clockwise (CCW) turn.

    # Step 1: Calculate the target angle relative to the robot's front.
    # We start with the offset of Mic 0 (-30 deg) and subtract the ASR angle
    # because it's measured in the opposite (CW) direction of the robot's yaw.
    target_angle_deg = -30.0 - new_angle_deg

    # Step 2: Normalize the angle to the range [-180, 180] to find the shortest turn.
    # The modulo operator (%) gives a result in [0, 360) for a positive divisor.
    normalized_angle = target_angle_deg % 360

    # If the normalized angle is > 180 degrees, turning in the negative
    # direction is shorter.
    if normalized_angle > 180.0:
        optimal_turn_deg = normalized_angle - 360.0
    else:
        optimal_turn_deg = normalized_angle

    # Step 3: Convert the final turning angle from degrees to radians.
    optimal_turn_rad = np.deg2rad(optimal_turn_deg)

    print_with_time(f"ASR angle: {new_angle_deg}°, Robot target: {target_angle_deg:.1f}°, Optimal turn: {optimal_turn_deg:.1f}°, Radians: {optimal_turn_rad:.2f}")

    return optimal_turn_rad

response_texts = [
    "怎么了？",
    "你叫我吗？",
    "干嘛？",
    "你好呀。",
]

if __name__ == "__main__":

    args = parser.parse_args()

    g1_watcher = G1_29_ASR_Watcher(network_interface=args.network_interface)

    highlevel_ctr = None
    tts_client = None
    if args.enable_tts:
        # pip install sounddevice requests
        from tts_class import TTSAgent
        tts_agent = TTSAgent(api_url_port=args.tts_api_url_port)

        tts_agent.send_non_block("我准备好了")

        print_with_time("waitting for TTS to be ready..")
        time.sleep(5)
        print_with_time("Done.")



    if args.enable_robot_ctr:
        highlevel_ctr = G1_Highlevel_Controller(
            args.network_interface, no_dds_init=True) # 前面channelfactory已经init
        print_with_time("setting walk mode..")
        highlevel_ctr.set_run_walk()  # 走跑运控
        #highlevel_ctr.set_normal_walk() # 主运控，更稳一点，但是走路不拟人
        # 马上返回
        time.sleep(2)
        print_with_time("set walk mode returned.")

    # Variable to store the last message to check for changes
    last_asr_message = None

    # remember the time when issued  a turn signal, avoid turning  continuously
    last_ctr_time = time.time()
    ctr_gap = 4. # seconds

    # 执行最多这么久之前的角度命令
    message_old_time = 10.  # seconds

    while True:
        start_time = time.time()

        # Get the latest ASR message string
        current_asr_message = g1_watcher.get_current_asr_string()

        # Check if the message is new and not None
        if current_asr_message is not None and current_asr_message != last_asr_message:
            # Print the new message and update the last_asr_message variable
            print_with_time(f"New ASR Message: '{current_asr_message}'")
            last_asr_message = current_asr_message

            # avoid freq orders
            if start_time - last_ctr_time > ctr_gap:
                try:
                    angle_data = json.loads(current_asr_message)

                    # 0 - 360 degree. 6个麦克风。机器人面前中央，靠右手边第一个麦克风0度，上往下看顺时针到360度
                    new_angle = int(angle_data["angle"])
                    # 发生指令的时间
                    timestamp = float(angle_data["timestamp"])

                    if start_time - timestamp > message_old_time:
                        print_with_time("message too old, ignored ctr")
                    else:
                        if args.enable_robot_ctr:
                            # 发送机器人转身命令。
                            # 机器人正前方是自己的0度，麦克风new_angle应该对应 -30度。
                            """
                                def move_turn_rad(self, rad):
                                    # vx: float, vy: float, vyaw: float, duration
                                    # g1的原点在骨盆pelvis 关节，x往前，y往左手，z往上
                                    # Yaw = rad（正方向）
                                    # 表示 绕 Z 轴逆时针旋转 rad 弧度（从上往下看），
                                    self.sport_client.SetVelocity(0, 0, rad, 1.6)
                            """
                            if args.enable_tts:
                                random_reply_text = random.choice(response_texts)
                                tts_agent.send_non_block(random_reply_text)
                            robot_turn_rad = compute_optimal_turn(new_angle)
                            #highlevel_ctr.move_turn_rad(robot_turn_rad, speed=1.0)
                            last_ctr_time = time.time() # Update the time of the last command

                except json.JSONDecodeError:
                    print_with_time(f"Error decoding JSON: {current_asr_message}")
                except (KeyError, TypeError) as e:
                    print_with_time(f"Error parsing ASR data dictionary: {e}")


        # Ensure consistent frame rate
        current_time = time.time()
        time_elapsed = current_time - start_time
        sleep_time = max(0, (1 / args.max_freq) - time_elapsed)
        time.sleep(sleep_time)
