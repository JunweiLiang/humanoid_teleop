import os
import json
import argparse
import pandas as pd
from pathlib import Path

def inspect_lerobot_dataset(repo_id):
    # Resolve the path to the hidden Hugging Face cache
    meta_dir = Path(os.path.expanduser(f"~/.cache/huggingface/lerobot/{repo_id}/meta"))

    if not meta_dir.exists():
        print(f"Directory not found: {meta_dir}")
        return

    print("="*50)
    print(f"📊 DATASET INSPECTION: {repo_id}")
    print("="*50)

    # 1. Read info.json for high-level stats
    info_path = meta_dir / "info.json"
    if info_path.exists():
        with open(info_path, "r") as f:
            info = json.load(f)
        print("\n[Overall Stats]")
        print(f"- Total Episodes : {info.get('total_episodes', 'N/A')}")
        print(f"- Total Frames   : {info.get('total_frames', 'N/A')}")
        print(f"- FPS            : {info.get('fps', 'N/A')}")

    # 2. Read tasks.parquet to get the task mapping
    tasks_path = meta_dir / "tasks.parquet"
    task_dict = {}
    if tasks_path.exists():
        tasks_df = pd.read_parquet(tasks_path)
        print("\n[Available Tasks]")

        # Dynamically find the column containing the task string
        task_col = None
        for col in ['task', 'tasks', 'instruction', 'goal', 'name']:
            if col in tasks_df.columns:
                task_col = col
                break

        if task_col and 'task_index' in tasks_df.columns:
            task_dict = dict(zip(tasks_df['task_index'], tasks_df[task_col]))
            for idx, task_name in task_dict.items():
                print(f"- Index {idx}: '{task_name}'")
        else:
            print(f"[!] Could not map tasks automatically.")
            print(f"    Available columns in tasks.parquet: {tasks_df.columns.tolist()}")
            print("    Raw data preview:")
            print(tasks_df.head())

    # 3. Read episodes metadata to get the distribution
    episodes_path = meta_dir / "episodes.parquet"
    if not episodes_path.exists():
        episodes_path = meta_dir / "episodes"

    if episodes_path.exists():
        try:
            episodes_df = pd.read_parquet(episodes_path)
            print("\n[Episodes per Task]")

            # In LeRobot V2, the episodes metadata usually maps to tasks via a list
            if 'tasks' in episodes_df.columns:
                # Explode the lists so we can count them easily
                exploded = episodes_df.explode('tasks')
                counts = exploded['tasks'].value_counts()
            elif 'task_index' in episodes_df.columns:
                counts = episodes_df['task_index'].value_counts()
            else:
                counts = pd.Series()
                print("Could not find task mapping in episodes.")

            for task_idx, count in counts.items():
                task_name = task_dict.get(task_idx, f"Unknown Task (Index {task_idx})")
                print(f"- '{task_name}': {count} episodes")

            # Print episode length statistics
            if 'length' in episodes_df.columns:
                print("\n[Episode Length Stats (Frames)]")
                print(f"- Average: {episodes_df['length'].mean():.1f} frames")
                print(f"- Min    : {episodes_df['length'].min()} frames")
                print(f"- Max    : {episodes_df['length'].max()} frames")

        except Exception as e:
            print(f"\n[!] Could not parse episodes data: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inspect LeRobot dataset metadata.")
    parser.add_argument(
        "--repo-id",
        type=str,
        default="junweiliang/wbc_5tasks",
        help="The Hugging Face repo ID of the dataset to inspect (e.g., junweiliang/wbc_5tasks)."
    )

    args = parser.parse_args()
    inspect_lerobot_dataset(repo_id=args.repo_id)
