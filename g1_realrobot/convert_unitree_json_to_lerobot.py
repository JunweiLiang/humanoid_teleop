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
import pandas as pd

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
    # The final LeRobot dataset will still be 49D
    state_names=ARM_HAND_JOINTS + WAIST_JOINTS + LEG_JOINTS + TRIGGER_NAMES + LOCO_CMD_NAMES,
    action_names=ARM_HAND_JOINTS + WAIST_JOINTS + LEG_JOINTS + TRIGGER_NAMES + LOCO_CMD_NAMES,
    cameras=["cam_high"],
    camera_to_image_key={"color_0": "cam_high"},

    # What is ACTUALLY in the JSON "states" dict (43 Dimensions)
    json_state_data_name=[
        "left_arm.qpos", "right_arm.qpos",
        "left_ee.qpos", "right_ee.qpos",
        "waist.qpos", "leg.qpos"
    ],

    # What is ACTUALLY in the JSON "actions" dict (37 Dimensions)
    json_action_data_name=[
        "left_arm.qpos", "right_arm.qpos",
        "left_ee.qpos", "right_ee.qpos",
        "waist.qpos",
        "left_trigger", "right_trigger", "loco_cmd"
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

def generate_jsonl_metadata(repo_id: str):
    """
    Converts LeRobot's default .parquet metadata into the .jsonl format
    strictly required by the GR00T dataloader.
    """
    meta_dir = HF_LEROBOT_HOME / repo_id / "meta"

    # --- 1. Convert tasks.parquet to tasks.jsonl ---
    tasks_parquet = meta_dir / "tasks.parquet"
    if tasks_parquet.exists():
        df_tasks = pd.read_parquet(tasks_parquet)

        # Dynamically find the task column just like our inspection script
        task_col = next((col for col in ['task', 'tasks', 'instruction', 'goal', 'name'] if col in df_tasks.columns), None)

        if task_col and 'task_index' in df_tasks.columns:
            with open(meta_dir / "tasks.jsonl", "w", encoding="utf-8") as f:
                for _, row in df_tasks.iterrows():
                    task_dict = {
                        "task_index": int(row['task_index']),
                        "task": str(row[task_col])
                    }
                    f.write(json.dumps(task_dict) + "\n")
            print(f"==> Successfully generated GR00T tasks.jsonl")

    # --- 2. Convert episodes.parquet to episodes.jsonl ---
    episodes_parquet = meta_dir / "episodes.parquet"
    if episodes_parquet.exists():
        df_episodes = pd.read_parquet(episodes_parquet)

        with open(meta_dir / "episodes.jsonl", "w", encoding="utf-8") as f:
            for _, row in df_episodes.iterrows():
                # Handle how LeRobot stores tasks (could be a list or a single int)
                tasks_val = row.get('tasks', row.get('task_index', [0]))
                if isinstance(tasks_val, (int, np.integer)):
                    tasks_list = [int(tasks_val)]
                else:
                    tasks_list = [int(x) for x in tasks_val]

                episode_dict = {
                    "episode_index": int(row['episode_index']),
                    "tasks": tasks_list,
                    "length": int(row['length'])
                }
                f.write(json.dumps(episode_dict) + "\n")
        print(f"==> Successfully generated GR00T episodes.jsonl")

def create_empty_dataset(
    repo_id: str,
    robot_type: str,
    fps: int = 30,  # <-- Added fps parameter
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
            "shape": (480, 640, 3),
            "names": ["height", "width", "channel"],
        }

    if Path(HF_LEROBOT_HOME / repo_id).exists():
        shutil.rmtree(HF_LEROBOT_HOME / repo_id)

    return LeRobotDataset.create(
        repo_id=repo_id,
        fps=fps, # <-- Pass the variable here instead of hardcoding 30
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

            # --- 3. ACTION SHIFTING AND CROSS-STITCHING ---
            loop_end = num_frames - 1 if use_future_state_as_action else num_frames

            for f_idx in range(loop_end):
                # raw_state is 43D: Arms(14) + Hands(14) + Waist(3) + Legs(12)
                # raw_action is 37D: Arms(14) + Hands(14) + Waist(3) + Triggers(2) + Loco(4)

                # The index where physical upper body ends in raw_action
                upper_body_end = 31 # 14 + 14 + 3

                # 1. BUILD THE 49D STATE
                current_physical_state = state[f_idx] # 43D
                # We pull the high-level commands from the raw ACTION array
                current_commands = action[f_idx][upper_body_end:] # 6D

                current_state_49d = np.concatenate([current_physical_state, current_commands])

                # 2. BUILD THE 49D ACTION
                if use_future_state_as_action:
                    # Future state has Arms, Hands, Waist, and Legs (43D)
                    future_physical_state = state[f_idx + 1]

                    # Stitch future physical joints with current high-level commands
                    actual_action_49d = np.concatenate([future_physical_state, current_commands])
                else:
                    # If not using future state, build action from raw action + current legs
                    current_physical_action = action[f_idx][:upper_body_end] # 31D
                    current_legs = state[f_idx][31:43] # 12D (Extracted from state)

                    actual_action_49d = np.concatenate([current_physical_action, current_legs, current_commands])

                frame = {
                    "observation.state": current_state_49d,
                    "action": actual_action_49d,
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
    meta_dir = HF_LEROBOT_HOME / repo_id / "meta"
    meta_dir.mkdir(parents=True, exist_ok=True)

    # State and Action slices are now perfectly 1:1
    modality_slice = {
        "arms": {"start": 0, "end": 14},
        "hands": {"start": 14, "end": 28},
        "waist": {"start": 28, "end": 31},
        "legs": {"start": 31, "end": 43},
        "triggers": {"start": 43, "end": 45},
        "loco_cmd": {"start": 45, "end": 49}
    }

    modality_config = {
        "state": modality_slice,
        "action": modality_slice,
        "video": {
            "cam_high": {"original_key": "observation.images.cam_high"}
        },
        "annotation": {
            "human.task_description": {"original_key": "task_index"}
        }
    }

    modality_path = meta_dir / "modality.json"
    with open(modality_path, "w", encoding="utf-8") as f:
        json.dump(modality_config, f, indent=4)

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
            fps=target_fps,  # <-- Pass it here!
            mode=mode,
            dataset_config=dataset_config,
        )
        start_episode = 0

    dataset = populate_dataset(
        dataset,
        raw_dir,
        robot_type=robot_type,
        downsample_factor=downsample_factor,
        use_future_state_as_action=use_future_state_as_action,
        start_episode=start_episode
    )

    # Force LeRobot to write the .parquet files to disk
    dataset.consolidate()

    # for Gr00T modality.json
    generate_modality_json(repo_id)

    # And add old jsonl file
    generate_jsonl_metadata(repo_id)


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
