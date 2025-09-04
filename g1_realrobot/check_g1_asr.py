# coding=utf-8
# this code reads the rt/audio_msg from the robots using DDS
# G1 has ASR running:  https://support.unitree.com/home/zh/G1_developer/VuiClient_Service


import numpy as np
import threading
import time
from enum import IntEnum
import argparse

from unitree_sdk2py.core.channel import ChannelPublisher, ChannelSubscriber, ChannelFactoryInitialize # dds

from unitree_sdk2py.idl.std_msgs.msg.dds_ import String_


# define the DDS topic names
g1_asr_topic = "rt/audio_msg" # 类型: std_msgs::msg::dds_::String_


parser = argparse.ArgumentParser()
parser.add_argument("--network_interface", default=None)
parser.add_argument("--max_freq", default=60.0, type=float)


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

        self.ASR_subscriber = ChannelSubscriber(g1_asr_topic, String_)
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
            print("read")
            msg = self.ASR_subscriber.Read() # 卡在这里
            print(msg)
            if msg is not None:

                asr_data_string = msg.data
                self.asr_msg.SetData(asr_data_string)
            time.sleep(0.002)


    def get_current_asr_string(self):
        '''Return current state q of all body motors.'''
        return self.asr_msg.GetData()


if __name__ == "__main__":

    args = parser.parse_args()

    g1_watcher = G1_29_ASR_Watcher(network_interface=args.network_interface)

    # Variable to store the last message to check for changes
    last_asr_message = None

    while True:
        start_time = time.time()

        # Get the latest ASR message string
        current_asr_message = g1_watcher.get_current_asr_string()

        # Check if the message is new and not None
        if current_asr_message is not None and current_asr_message != last_asr_message:
            # Print the new message and update the last_asr_message variable
            print(f"New ASR Message: '{current_asr_message}'")
            last_asr_message = current_asr_message

        # Ensure consistent frame rate
        current_time = time.time()
        time_elapsed = current_time - start_time
        sleep_time = max(0, (1 / args.max_freq) - time_elapsed)
        time.sleep(sleep_time)
