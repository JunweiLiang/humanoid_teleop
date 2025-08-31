# coding=utf-8
# this code reads the rt/lowstate from the robots using DDS and visualize in browser
# and reads the  hand states as well
# we can only show current q
# dq can be printed out


import numpy as np
import threading
import time
from enum import IntEnum
import argparse

from unitree_sdk2py.core.channel import ChannelPublisher, ChannelSubscriber, ChannelFactoryInitialize # dds
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import ( LowCmd_  as hg_LowCmd, LowState_ as hg_LowState) # idl for g1, h1_2

from unitree_sdk2py.idl.unitree_hg.msg.dds_ import HandState_
from unitree_sdk2py.idl.unitree_go.msg.dds_ import MotorStates_

# for  web browser visualization
from visualize_arm_episodes import G1_29_Vis_WholeBody

# define the DDS topic names
Dex3_Num_Motors = 7
dex3_left_dds_topic = "rt/dex3/left/state"
dex3_right_dds_topic = "rt/dex3/right/state"
Inspire_Num_Motors = 6 # we ignore the rest of the passive DoF
inspire_dds_topic = "rt/inspire/state"

G1_29_Num_Motors = 35
g1_motor_dds_topic = "rt/lowstate"

parser = argparse.ArgumentParser()
parser.add_argument("--urdf", default=None, help="need this for visualization")
parser.add_argument("--visualize", action="store_true", help="visualize using meshcat browser")
parser.add_argument("--sim", action="store_true", help="read DDS from sim")
parser.add_argument("--network_interface", default=None)
parser.add_argument("--hand_type", default="dex3", help="dex3 or inspire1")
parser.add_argument("--max_freq", default=60.0, type=float, help="maximum freq")


class MotorState:
    def __init__(self):
        self.q = None
        self.dq = None

class G1_29_LowState:
    def __init__(self):
        self.motor_state = [MotorState() for _ in range(G1_29_Num_Motors)]

class Dex3_LowState:
    def __init__(self):
        self.motor_state = [MotorState() for _ in range(Dex3_Num_Motors)]

class Inspire1_LowState:
    def __init__(self):
        self.motor_state = [MotorState() for _ in range(Inspire_Num_Motors)]

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


class G1_29_Hand_Watcher:
    def __init__(self,
            simulation_mode = False,
            network_interface=None,
            hand_type="dex3",
        ):

        self.simulation_mode = simulation_mode
        self.hand_type = hand_type

        # initialize lowcmd publisher and lowstate subscriber
        if self.simulation_mode:
            ChannelFactoryInitialize(1)
        else:
            ChannelFactoryInitialize(0, network_interface)

        # start getting hand states
        self.left_hand_state_buffer = DataBuffer()
        self.right_hand_state_buffer = DataBuffer()

        if hand_type == "dex3":
            self.LeftHandState_subscriber = ChannelSubscriber(dex3_left_dds_topic, HandState_)
            self.LeftHandState_subscriber.Init()
            self.RightHandState_subscriber = ChannelSubscriber(dex3_right_dds_topic, HandState_)
            self.RightHandState_subscriber.Init()

        elif hand_type == "inspire1":
            self.HandState_subscriber = ChannelSubscriber(inspire_dds_topic, MotorStates_)
            self.HandState_subscriber.Init()
        else:
            raise Exception("unknown hand: %s" % hand_type)
        # initialize subscribe thread
        self.subscribe_state_thread = threading.Thread(target=self._subscribe_hand_state)
        self.subscribe_state_thread.daemon = True
        self.subscribe_state_thread.start()

        while not self.left_hand_state_buffer.GetData() or not self.right_hand_state_buffer.GetData():
            time.sleep(0.01)
            print("[%s] Waiting to subscribe dds..." % hand_type)
        print("[%s] Subscribe dds ok." % hand_type)

        # start getting G1 states
        self.lowstate_subscriber = ChannelSubscriber(g1_motor_dds_topic, hg_LowState)
        self.lowstate_subscriber.Init()
        self.lowstate_buffer = DataBuffer()

        # initialize subscribe thread
        self.subscribe_thread = threading.Thread(target=self._subscribe_motor_state)
        self.subscribe_thread.daemon = True
        self.subscribe_thread.start()

        while not self.lowstate_buffer.GetData():
            time.sleep(0.1)
            print("[G1_29_ArmController] Waiting to subscribe dds...")
        print("[G1_29_ArmController] Subscribe dds ok.")

    def _subscribe_hand_state(self):
        while True:
            if self.hand_type == "dex3":
                left_hand_msg  = self.LeftHandState_subscriber.Read()
                right_hand_msg = self.RightHandState_subscriber.Read()
                if left_hand_msg is not None and right_hand_msg is not None:
                    left_hand_state = Dex3_LowState()
                    right_hand_state = Dex3_LowState()
                    # Update left hand state
                    for _, id in enumerate(Dex3_1_Left_JointIndex):
                        left_hand_state.motor_state[id].q = left_hand_msg.motor_state[id].q
                    # Update right hand state
                    for _, id in enumerate(Dex3_1_Right_JointIndex):
                        right_hand_state.motor_state[id].q = right_hand_msg.motor_state[id].q

                    self.left_hand_state_buffer.SetData(left_hand_state)
                    self.right_hand_state_buffer.SetData(right_hand_state)

            elif self.hand_type == "inspire1":
                hand_msg  = self.HandState_subscriber.Read()
                if hand_msg is not None:
                    left_hand_state = Inspire1_LowState()
                    right_hand_state = Inspire1_LowState()

                    for idx, id in enumerate(Inspire_Left_Hand_JointIndex):
                        left_hand_state.motor_state[idx].q = hand_msg.states[id].q

                    for idx, id in enumerate(Inspire_Right_Hand_JointIndex):
                        right_hand_state.motor_state[idx].q = hand_msg.states[id].q

                    self.left_hand_state_buffer.SetData(left_hand_state)
                    self.right_hand_state_buffer.SetData(right_hand_state)
            time.sleep(0.002) # max 500 Hz?

    def _subscribe_motor_state(self):
        while True:
            msg = self.lowstate_subscriber.Read()
            if msg is not None:
                lowstate = G1_29_LowState()
                for id in range(G1_29_Num_Motors):
                    lowstate.motor_state[id].q  = msg.motor_state[id].q
                    lowstate.motor_state[id].dq = msg.motor_state[id].dq
                self.lowstate_buffer.SetData(lowstate)
            time.sleep(0.002)


    def get_current_motor_q(self):
        '''Return current state q of all body motors.'''
        return np.array([self.lowstate_buffer.GetData().motor_state[id].q for id in G1_29_JointIndex])
    

class Dex3_1_Left_JointIndex(IntEnum):
    kLeftHandThumb0 = 0
    kLeftHandThumb1 = 1
    kLeftHandThumb2 = 2
    kLeftHandMiddle0 = 3
    kLeftHandMiddle1 = 4
    kLeftHandIndex0 = 5
    kLeftHandIndex1 = 6

class Dex3_1_Right_JointIndex(IntEnum):
    kRightHandThumb0 = 0
    kRightHandThumb1 = 1
    kRightHandThumb2 = 2
    kRightHandIndex0 = 3
    kRightHandIndex1 = 4
    kRightHandMiddle0 = 5
    kRightHandMiddle1 = 6

# Update hand state, according to the official documentation, https://support.unitree.com/home/en/G1_developer/inspire_dfx_dexterous_hand
# the state sequence is as shown in the table below
# ┌──────┬───────┬──────┬────────┬────────┬────────────┬────────────────┬───────┬──────┬────────┬────────┬────────────┬────────────────┐
# │ Id   │   0   │  1   │   2    │   3    │     4      │       5        │   6   │  7   │   8    │   9    │    10      │       11       │
# ├──────┼───────┼──────┼────────┼────────┼────────────┼────────────────┼───────┼──────┼────────┼────────┼────────────┼────────────────┤
# │      │                    Right Hand                                │                   Left Hand                                  │
# │Joint │ pinky │ ring │ middle │ index  │ thumb-bend │ thumb-rotation │ pinky │ ring │ middle │ index  │ thumb-bend │ thumb-rotation │
# └──────┴───────┴──────┴────────┴────────┴────────────┴────────────────┴───────┴──────┴────────┴────────┴────────────┴────────────────┘
class Inspire_Right_Hand_JointIndex(IntEnum):
    kRightHandPinky = 0
    kRightHandRing = 1
    kRightHandMiddle = 2
    kRightHandIndex = 3
    kRightHandThumbBend = 4
    kRightHandThumbRotation = 5

class Inspire_Left_Hand_JointIndex(IntEnum):
    kLeftHandPinky = 6
    kLeftHandRing = 7
    kLeftHandMiddle = 8
    kLeftHandIndex = 9
    kLeftHandThumbBend = 10
    kLeftHandThumbRotation = 11

class G1_29_JointIndex(IntEnum):
    # Left leg
    kLeftHipPitch = 0
    kLeftHipRoll = 1
    kLeftHipYaw = 2
    kLeftKnee = 3
    kLeftAnklePitch = 4
    kLeftAnkleRoll = 5

    # Right leg
    kRightHipPitch = 6
    kRightHipRoll = 7
    kRightHipYaw = 8
    kRightKnee = 9
    kRightAnklePitch = 10
    kRightAnkleRoll = 11

    kWaistYaw = 12
    kWaistRoll = 13
    kWaistPitch = 14

    # Left arm
    kLeftShoulderPitch = 15
    kLeftShoulderRoll = 16
    kLeftShoulderYaw = 17
    kLeftElbow = 18
    kLeftWristRoll = 19
    kLeftWristPitch = 20
    kLeftWristYaw = 21

    # Right arm
    kRightShoulderPitch = 22
    kRightShoulderRoll = 23
    kRightShoulderYaw = 24
    kRightElbow = 25
    kRightWristRoll = 26
    kRightWristPitch = 27
    kRightWristYaw = 28
    
    # not used
    kNotUsedJoint0 = 29
    kNotUsedJoint1 = 30
    kNotUsedJoint2 = 31
    kNotUsedJoint3 = 32
    kNotUsedJoint4 = 33
    kNotUsedJoint5 = 34


def get_inline_print(g1_state, left_hand_state, right_hand_state, hand_type):

    # ANSI escape code to clear the terminal screen and move cursor to the top-left
    output_string = "\033[H\033[J"

    # Format and append G1 motor states
    output_string += "--- G1 Motor States ---\n"
    for joint in G1_29_JointIndex:
        # Skip unused joints for a cleaner output
        if "NotUsed" in joint.name:
            continue
        q = g1_state.motor_state[joint.value].q
        dq = g1_state.motor_state[joint.value].dq
        output_string += f"{joint.name:<20}: q = {q:8.4f}, dq = {dq:8.4f}\n"
    output_string += "\n"

    # Format and append Hand states based on hand type
    output_string += f"--- Left Hand ({hand_type}) ---\n"
    if hand_type == "dex3":
        for joint in Dex3_1_Left_JointIndex:
            q = left_hand_state.motor_state[joint.value].q
            output_string += f"{joint.name:<20}: q = {q:8.4f}\n"
    else: # inspire1
        joint_names = list(Inspire_Left_Hand_JointIndex)
        for idx in range(Inspire_Num_Motors):
            joint_name = joint_names[idx].name
            q = left_hand_state.motor_state[idx].q
            output_string += f"{joint_name:<25}: q = {q:8.4f}\n"
    output_string += "\n"

    output_string += f"--- Right Hand ({hand_type}) ---\n"
    if hand_type == "dex3":
        for joint in Dex3_1_Right_JointIndex:
            q = right_hand_state.motor_state[joint.value].q
            output_string += f"{joint.name:<20}: q = {q:8.4f}\n"
    else: # inspire1
        joint_names = list(Inspire_Right_Hand_JointIndex)
        for idx in range(Inspire_Num_Motors):
            joint_name = joint_names[idx].name
            q = right_hand_state.motor_state[idx].q
            output_string += f"{joint_name:<25}: q = {q:8.4f}\n"
    return output_string

if __name__ == "__main__":

    args = parser.parse_args()

    g1_watcher = G1_29_Hand_Watcher(simulation_mode=args.sim, network_interface=args.network_interface, hand_type=args.hand_type)

    if args.visualize:
        g1_visualizer = G1_29_Vis_WholeBody(urdf=args.urdf, hand_type=args.hand_type, print_urdf_joints=True)

    while True:
        start_time = time.time()

        # Get the latest state data from the buffers
        g1_state = g1_watcher.lowstate_buffer.GetData()
        left_hand_state = g1_watcher.left_hand_state_buffer.GetData()
        right_hand_state = g1_watcher.right_hand_state_buffer.GetData()

        # Continue if any of the buffers are not yet populated
        if not all((g1_state, left_hand_state, right_hand_state)):
            time.sleep(0.01)
            continue

        # print out the g1 motor states and the hand states in the terminal on multiple lines and refresh in place
        output_string = get_inline_print(g1_state, left_hand_state, right_hand_state, hand_type=args.hand_type)

        # Print the entire formatted string at once to the terminal
        print(output_string, end="")

        # Ensure consistent frame rate
        current_time = time.time()
        time_elapsed = current_time - start_time
        sleep_time = max(0, (1 / args.max_freq) - time_elapsed)
        time.sleep(sleep_time)
