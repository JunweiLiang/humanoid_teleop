# codng=utf-8
# test G1's arm service, arm_sdk high-level
import argparse
import time
from robot_arm_high_level_v3 import G1_Highlevel_Controller
import logging_mp
logger_mp = logging_mp.get_logger(__name__)
logging_mp.basic_config(level=logging_mp.INFO)
parser = argparse.ArgumentParser()
parser.add_argument("gesture_data_path", help="path to the gesture json")
parser.add_argument("g1_network")

"""
# 这个mapping需要与system prompt 对应
    func_mapping = {
        "往前走一步": self.g1_ctr.move_forward,
        "往左走一步": self.g1_ctr.move_backward,
        "往右走一步": self.g1_ctr.move_right_lateral,
        "向左转": self.g1_ctr.move_turn_left,
        "向右转": self.g1_ctr.move_turn_right,
        "挥手": self.g1_ctr.wave_hand,
        "握手": self.g1_ctr.shake_hand_up,
        "放下手": self.g1_ctr.release_arm,
        "鼓掌": self.g1_ctr.clap,
        "比心": self.g1_ctr.heart,
        "抬起右手": self.g1_ctr.hand_up,
    }
"""

if __name__ == "__main__":
    args = parser.parse_args()

    highlevel_ctr = G1_Highlevel_Controller(
        args.g1_network, args.gesture_data_path)

    logger_mp.info("setting walk mode..")
    highlevel_ctr.set_run_walk()  # 走跑运控
    #highlevel_ctr.set_normal_walk() # 主运控，更稳一点，但是走路不拟人
    logger_mp.info("set walk mode returned")# 马上返回
    time.sleep(1)

    input("confirm g1 low wave..")
    logger_mp.info("starting g1 low wave..")
    highlevel_ctr.low_wave_hand()# 不会马上返回
    logger_mp.info("Low wave returned.")
    time.sleep(1)

    input("confirm g1 custom gesture")
    logger_mp.info("trying custom gesture")
    highlevel_ctr.left_welcome()
    logger_mp.info("left welcome exited.")
    time.sleep(1)

    input("confirm g1 low wave..")
    logger_mp.info("starting g1 low wave..")
    highlevel_ctr.low_wave_hand()# 不会马上返回
    logger_mp.info("Low wave returned.")
    time.sleep(1)

    logger_mp.info("setting run walk mode..")
    highlevel_ctr.set_run_walk()  # 走跑运控
    logger_mp.info("set run walk mode returned")# 马上返回
    time.sleep(1)

    input("confirm g1 turn left")
    logger_mp.info("starting g1 turn left..")
    highlevel_ctr.move_turn_left()# 不会马上返回
    logger_mp.info("g1 turn left returned.")

    logger_mp.info("whole test exited")
