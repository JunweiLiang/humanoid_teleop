"""
Script Json to Lerobot (Modified for Whole Body Control with Locomotion).

# --raw-dir     Corresponds to the directory of your JSON dataset
# --repo-id     Your unique repo ID on Hugging Face Hub

python unitree_lerobot/utils/convert_unitree_json_to_lerobot.py \
    --raw-dir $HOME/datasets/g1_grabcube_double_hand \
    --repo-id your_name/g1_wbc_dataset \
    --downsample-factor 2 \
    --use-future-state-as-action True
"""

import os
import argparse
import cv2
import tqdm
import json
import glob
import dataclasses
import shutil
import numpy as np
from pathlib import Path
from collections import defaultdict
from typing import Literal

from lerobot.utils.constants import HF_LEROBOT_HOME
from lerobot.datasets.lerobot_dataset import LeRobotDataset

@dataclasses.dataclass
class RobotConfig:
    state_names: list[str]
    action_names: list[str]
    cameras: list[str]
    camera_to_image_key: dict[str, str]
    json_state_data_name: list[str]
    json_action_data_name: list[str]

# Base Arm and Hand joint names
ARM_HAND_JOINTS = [
    "kLeftShoulderPitch", "kLeftShoulderRoll", "kLeftShoulderYaw", "kLeftElbow", "kLeftWristRoll", "kLeftWristPitch", "kLeftWristYaw",
    "kRightShoulderPitch", "kRightShoulderRoll", "kRightShoulderYaw", "kRightElbow", "kRightWristRoll", "kRightWristPitch", "kRightWristYaw",
    "kLeftHandThumb0", "kLeftHandThumb1", "kLeftHandThumb2", "kLeftHandMiddle0", "kLeftHandMiddle1", "kLeftHandIndex0", "kLeftHandIndex1",
    "kRightHandThumb0", "kRightHandThumb1", "kRightHandThumb2", "kRightHandIndex0", "kRightHandIndex1", "kRightHandMiddle0", "kRightHandMiddle1",
]

WAIST_JOINTS = [
    "kWaistYaw",
    "kWaistRoll",
    "kWaistPitch"
]

LEG_JOINTS = [
    # Left leg
    "kLeftHipPitch",
    "kLeftHipRoll",
    "kLeftHipYaw",
    "kLeftKnee",
    "kLeftAnklePitch",
    "kLeftAnkleRoll",

    # Right leg
    "kRightHipPitch",
    "kRightHipRoll",
    "kRightHipYaw",
    "kRightKnee",
    "kRightAnklePitch",
    "kRightAnkleRoll"
]

# height: 1. -> 1.65
LOCO_CMD_NAMES = ["loco_v_x", "loco_v_y", "loco_v_yaw", "loco_height"]
TRIGGER_NAMES = ["left_trigger", "right_trigger"]

G1_WBC_CONFIG = RobotConfig(
    state_names=ARM_HAND_JOINTS + WAIST_JOINTS + LEG_JOINTS, # 28 + 3 + 12 = 43D
    action_names=ARM_HAND_JOINTS + WAIST_JOINTS + TRIGGER_NAMES + LOCO_CMD_NAMES, # 28 + 3 + 2 + 4 = 37D
    cameras=[
        "cam_high",
        # "cam_left_wrist", # Uncomment if using wrist cameras
        # "cam_right_wrist",
    ],
    camera_to_image_key={
        "color_0": "cam_high",
        # "color_1": "cam_left_wrist",
        # "color_2": "cam_right_wrist",
    },
    json_state_data_name=[
        "left_arm.qpos", "right_arm.qpos",
        "left_ee.qpos", "right_ee.qpos",
        "waist.qpos", "leg.qpos"
    ],
    json_action_data_name=[
        "left_arm.qpos", "right_arm.qpos",
        "left_ee.qpos", "right_ee.qpos",
        "waist.qpos", "left_trigger", "right_trigger", "loco_cmd"
    ],
)


@dataclasses.dataclass(frozen=True)
class DatasetConfig:
    use_videos: bool = True
    tolerance_s: float = 0.0001
    image_writer_processes: int = 10
    image_writer_threads: int = 5
    video_backend: str | None = None


DEFAULT_DATASET_CONFIG = DatasetConfig()


class JsonDataset:
    def __init__(self, data_dirs: Path, robot_type: str) -> None:
        """
        Initialize the dataset for loading and processing JSON files containing robot manipulation data.
        """
        assert data_dirs is not None, "Data directory cannot be None"
        self.data_dirs = data_dirs
        self.json_file = "data.json"

        # Initialize paths and cache
        self._init_paths()
        self._init_cache()

        self.json_state_data_name = G1_WBC_CONFIG.json_state_data_name
        self.json_action_data_name = G1_WBC_CONFIG.json_action_data_name
        self.camera_to_image_key = G1_WBC_CONFIG.camera_to_image_key

    def _init_paths(self) -> None:
        self.episode_paths = []
        self.task_paths = []

        for task_path in glob.glob(os.path.join(self.data_dirs, "*")):
            if os.path.isdir(task_path):
                episode_paths = glob.glob(os.path.join(task_path, "*"))
                if episode_paths:
                    self.task_paths.append(task_path)
                    self.episode_paths.extend(episode_paths)

        self.episode_paths = sorted(self.episode_paths)
        self.episode_ids = list(range(len(self.episode_paths)))

    def __len__(self) -> int:
        return len(self.episode_paths)

    def _init_cache(self) -> list:
        self.episodes_data_cached = []
        for episode_path in tqdm.tqdm(self.episode_paths, desc="Loading Cache Json"):
            json_path = os.path.join(episode_path, self.json_file)
            with open(json_path, encoding="utf-8") as jsonf:
                self.episodes_data_cached.append(json.load(jsonf))

        print(f"==> Cached {len(self.episodes_data_cached)} episodes")
        return self.episodes_data_cached

    def _extract_data(self, episode_data: dict, key: str, parts: list[str]) -> np.ndarray:
        result = []
        for sample_data in episode_data["data"]:
            data_array = np.array([], dtype=np.float32)
            for part in parts:
                key_parts = part.split(".")
                qpos = None
                for key_part in key_parts:
                    if qpos is None and key_part in sample_data[key] and sample_data[key][key_part] is not None:
                        qpos = sample_data[key][key_part]
                    else:
                        if qpos is None:
                            # Handle potential None values for triggers/loco cmds if controller wasn't used
                            qpos = 0.0
                        elif isinstance(qpos, dict):
                            qpos = qpos.get(key_part, 0.0)

                if isinstance(qpos, list):
                    qpos = np.array(qpos, dtype=np.float32).flatten()
                else:
                    qpos = np.array([qpos], dtype=np.float32).flatten()
                data_array = np.concatenate([data_array, qpos])
            result.append(data_array)
        return np.array(result)

    def _parse_images(self, episode_path: str, episode_data) -> dict[str, list[np.ndarray]]:
        images = defaultdict(list)
        keys = episode_data["data"][0]["colors"].keys()
        cameras = [key for key in keys if "depth" not in key]

        for camera in cameras:
            image_key = self.camera_to_image_key.get(camera)
            if image_key is None:
                continue

            for sample_data in episode_data["data"]:
                relative_path = sample_data["colors"].get(camera)
                if not relative_path:
                    continue

                image_path = os.path.join(episode_path, relative_path)
                if not os.path.exists(image_path):
                    raise FileNotFoundError(f"Image path does not exist: {image_path}")

                image = cv2.imread(image_path)
                if image is None:
                    raise RuntimeError(f"Failed to read image: {image_path}")

                image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                images[image_key].append(image_rgb)

        return images

    def get_item(self, index: int | None = None) -> dict:
        file_path = np.random.choice(self.episode_paths) if index is None else self.episode_paths[index]
        episode_data = self.episodes_data_cached[index]

        action = self._extract_data(episode_data, "actions", self.json_action_data_name)
        state = self._extract_data(episode_data, "states", self.json_state_data_name)
        episode_length = len(state)
        state_dim = state.shape[1] if len(state.shape) == 2 else state.shape[0]
        action_dim = action.shape[1] if len(action.shape) == 2 else action.shape[0]

        # 改成读文件夹名字作为task name
        #task = episode_data.get("text", {}).get("goal", "teleop task")
        # Extract the parent folder name (e.g., "close_washer_door")
        parent_folder = os.path.basename(os.path.dirname(file_path))

        task = parent_folder
        # ----------

        cameras = self._parse_images(file_path, episode_data)

        # Fallback shapes if cameras are missing
        cam_height, cam_width = 480, 640
        for imgs in cameras.values():
            if imgs:
                cam_height, cam_width = imgs[0].shape[:2]
                break

        data_cfg = {
            "camera_names": list(cameras.keys()),
            "cam_height": cam_height,
            "cam_width": cam_width,
            "state_dim": state_dim,
            "action_dim": action_dim,
        }

        return {
            "episode_index": index,
            "episode_length": episode_length,
            "state": state,
            "action": action,
            "cameras": cameras,
            "task": task,
            "data_cfg": data_cfg,
        }


def create_empty_dataset(
    repo_id: str,
    robot_type: str,
    mode: Literal["video", "image"] = "video",
    *,
    dataset_config: DatasetConfig = DEFAULT_DATASET_CONFIG,
) -> LeRobotDataset:

    state_names = G1_WBC_CONFIG.state_names
    action_names = G1_WBC_CONFIG.action_names
    cameras = G1_WBC_CONFIG.cameras

    features = {
        "observation.state": {
            "dtype": "float32",
            "shape": (len(state_names),),
            "names": [state_names],
        },
        "action": {
            "dtype": "float32",
            "shape": (len(action_names),),
            "names": [action_names],
        },
    }

    for cam in cameras:
        features[f"observation.images.{cam}"] = {
            "dtype": mode,
            "shape": (480, 640, 3), # Matches your 640x480 setting
            "names": ["height", "width", "channel"],
        }

    if Path(HF_LEROBOT_HOME / repo_id).exists():
        shutil.rmtree(HF_LEROBOT_HOME / repo_id)

    # 这里lerobot 会自动加time stamp
    return LeRobotDataset.create(
        repo_id=repo_id,
        fps=30, # Change this to 60 if you want to keep raw FPS, but 30 is standard
        robot_type="Unitree_G1_WBC",
        features=features,
        use_videos=dataset_config.use_videos,
        tolerance_s=dataset_config.tolerance_s,
        image_writer_processes=dataset_config.image_writer_processes,
        image_writer_threads=dataset_config.image_writer_threads,
        video_backend=dataset_config.video_backend,
    )


def populate_dataset(
    dataset: LeRobotDataset,
    raw_dir: Path,
    robot_type: str,
    downsample_factor: int = 2,
    use_future_state_as_action: bool = True,
    start_episode: int = 0
) -> LeRobotDataset:
    json_dataset = JsonDataset(raw_dir, robot_type)

    # Start the loop from where we left off
    for i in tqdm.tqdm(range(start_episode, len(json_dataset))):
        episode_path = json_dataset.episode_paths[i]

        try:
            episode = json_dataset.get_item(i)
            state = episode["state"]
            action = episode["action"]

            # --- 1. PRE-FLIGHT VALIDATION ---
            expected_state_dim = len(G1_WBC_CONFIG.state_names)
            expected_action_dim = len(G1_WBC_CONFIG.action_names)

            if state.shape[-1] != expected_state_dim or action.shape[-1] != expected_action_dim:
                print(f"\n[WARNING] Skipping Episode {i} ({episode_path})")
                print(f"          Reason: Shape mismatch. State: {state.shape[-1]} (expected {expected_state_dim}).")
                print("          (This usually means hand tracking data was absent during recording).")
                continue # Skip this episode completely

            cameras = episode["cameras"]
            task = episode["task"]

            # --- 2. DOWNSAMPLING MODULE ---
            state = state[::downsample_factor]
            action = action[::downsample_factor]
            for cam in cameras.keys():
                cameras[cam] = cameras[cam][::downsample_factor]

            num_frames = len(state)

            # --- 3. ACTION SHIFTING (t = state t+1) ---
            loop_end = num_frames - 1 if use_future_state_as_action else num_frames

            for f_idx in range(loop_end):
                current_state = state[f_idx]

                if use_future_state_as_action:
                    future_state = state[f_idx + 1]
                    future_joints = future_state[:31]
                    current_triggers_loco = action[f_idx][31:]
                    actual_action = np.concatenate([future_joints, current_triggers_loco])
                else:
                    actual_action = action[f_idx]

                frame = {
                    "observation.state": current_state,
                    "action": actual_action,
                }

                for camera, img_array in cameras.items():
                    frame[f"observation.images.{camera}"] = img_array[f_idx]

                frame["task"] = task
                dataset.add_frame(frame)

            dataset.save_episode()

        except Exception as e:
            # Verbose logging so you know exactly which file caused a crash
            print(f"\n[ERROR] Failed to process Episode {i}: {episode_path}")
            print(f"        Exception: {e}")

            # Clear the buffer so the corrupted episode doesn't ruin the next one
            if hasattr(dataset, "clear_episode_buffer"):
                dataset.clear_episode_buffer()
            continue

    return dataset

def generate_modality_json(repo_id: str):
    """
    Generates the GR00T-specific meta/modality.json file.
    This tells GR00T exactly how to slice the 1D state/action vectors.
    """
    meta_dir = HF_LEROBOT_HOME / repo_id / "meta"
    meta_dir.mkdir(parents=True, exist_ok=True)
    """
    When you write your GR00T fine-tuning config YAML later, you can simply
    tell the model to use actions: ["arms", "waist", "triggers", "loco_cmd"].
    GR00T's dataloader will look at modality.json, grab those specific chunks,
    concatenate them, and completely ignore the hands indices without you ever
    having to rewrite the underlying parquet files.
    """
    # Define the precise slicing for your 43D state and 37D action vectors
    modality_config = {
        "state": {
            "arms": {"start": 0, "end": 14},      # 7 left arm + 7 right arm
            "hands": {"start": 14, "end": 28},    # 7 left fingers + 7 right fingers
            "waist": {"start": 28, "end": 31},    # 3 waist joints
            "legs": {"start": 31, "end": 43}      # 12 leg joints
        },
        "action": {
            "arms": {"start": 0, "end": 14},      # 7 left arm + 7 right arm
            "hands": {"start": 14, "end": 28},    # 7 left fingers + 7 right fingers
            "waist": {"start": 28, "end": 31},    # 3 waist joints
            "triggers": {"start": 31, "end": 33}, # left_trigger, right_trigger
            "loco_cmd": {"start": 33, "end": 37}  # vx, vy, vyaw, height
        },
        "video": {
            "cam_high": {
                "original_key": "observation.images.cam_high"
            }
        }
        # "annotation": {} # Omitted since you are using standard LeRobot task_index for now
    }

    modality_path = meta_dir / "modality.json"
    with open(modality_path, "w", encoding="utf-8") as f:
        json.dump(modality_config, f, indent=4)

    print(f"==> Successfully wrote GR00T modality config to {modality_path}")

def json_to_lerobot(
    raw_dir: Path,
    repo_id: str,
    robot_type: str = "Unitree_G1_WBC",
    downsample_factor: int = 2,
    use_future_state_as_action: bool = True,
    resume: bool = False,
    mode: Literal["video", "image"] = "video",
    dataset_config: DatasetConfig = DEFAULT_DATASET_CONFIG,
):
    original_data_fps = 60
    target_fps = original_data_fps // downsample_factor
    repo_path = HF_LEROBOT_HOME / repo_id

    # --- RESUME LOGIC ---
    if resume and repo_path.exists():
        print(f"==> Resuming existing dataset at {repo_id}")
        dataset = LeRobotDataset(repo_id)
        start_episode = dataset.num_episodes
        print(f"==> Found {start_episode} successfully saved episodes. Skipping them.")
    else:
        if repo_path.exists():
            shutil.rmtree(repo_path)

        dataset = create_empty_dataset(
            repo_id,
            robot_type=robot_type,
            mode=mode,
            dataset_config=dataset_config,
        )
        dataset.fps = target_fps
        start_episode = 0

    dataset = populate_dataset(
        dataset,
        raw_dir,
        robot_type=robot_type,
        downsample_factor=downsample_factor,
        use_future_state_as_action=use_future_state_as_action,
        start_episode=start_episode
    )

    # From the GR00T modification earlier
    generate_modality_json(repo_id)



import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert Unitree JSON WBC data to LeRobot Dataset format.")

    parser.add_argument("--raw-dir", type=Path, required=True,
                        help="Corresponds to the directory of your JSON dataset")
    parser.add_argument("--repo-id", type=str, required=True,
                        help="Your unique repo ID on Hugging Face Hub")
    parser.add_argument("--robot-type", type=str, default="Unitree_G1_WBC",
                        help="The type of the robot used in the dataset")
    parser.add_argument("--downsample-factor", type=int, default=2,
                        help="Downsampling factor (60 -> 30)")
    parser.add_argument("--use-future-state-as-action", action="store_true",
                        help="Replace commanded arm/waist joints with the achieved future state")
    parser.add_argument("--resume", action="store_true",
                        help="Resume processing an existing dataset without deleting it")
    parser.add_argument("--mode", type=str, choices=["video", "image"], default="video",
                        help="Store visual data as videos or discrete images")

    args = parser.parse_args()

    json_to_lerobot(
        raw_dir=args.raw_dir,
        repo_id=args.repo_id,
        robot_type=args.robot_type,
        downsample_factor=args.downsample_factor,
        use_future_state_as_action=args.use_future_state_as_action,
        resume=args.resume,
        mode=args.mode
    )
