import os
import json
import argparse
import pandas as pd
from pathlib import Path

def inspect_lerobot_dataset(repo_id):
    # Resolve the path to the hidden Hugging Face cache
    base_dir = Path(os.path.expanduser(f"~/.cache/huggingface/lerobot/{repo_id}"))
    meta_dir = base_dir / "meta"

    if not meta_dir.exists():
        print(f"Directory not found: {meta_dir}")
        return

    print("="*60)
    print(f"📊 DATASET INSPECTION: {repo_id}")
    print("="*60)

    # ==========================================
    # GR00T COMPLIANCE CHECK
    # ==========================================
    print("\n🛡️ GR00T COMPLIANCE CHECK")
    print("-" * 30)
    compliance_passed = True

    # 1. Check required meta files (JSONL requirement)
    print("[1. Meta Directory Structure]")
    required_meta = ["info.json", "modality.json", "episodes.jsonl", "tasks.jsonl"]
    for req in required_meta:
        if (meta_dir / req).exists():
            print(f"  ✅ Found {req}")
        else:
            print(f"  ❌ Missing {req}")
            compliance_passed = False
            # Check if parquet exists instead
            if req in ["episodes.jsonl", "tasks.jsonl"] and (meta_dir / req.replace(".jsonl", ".parquet")).exists():
                print(f"     ⚠️ Note: Found {req.replace('.jsonl', '.parquet')} instead. GR00T strictly requires .jsonl.")

    # 2. Check modality.json schema & dimensions
    print("\n[2. modality.json Schema & Slicing]")
    modality_path = meta_dir / "modality.json"
    if modality_path.exists():
        try:
            with open(modality_path, "r") as f:
                modality = json.load(f)
            for key in ["state", "action", "video", "annotation"]:
                if key in modality:
                    print(f"  ✅ Contains '{key}' definition")
                else:
                    print(f"  ❌ Missing '{key}' definition")
                    compliance_passed = False

            # --- Check if modality slicing maxes out at 49D ---
            state_slices = modality.get("state", {})
            max_end = 0
            for k, v in state_slices.items():
                if isinstance(v, dict) and "end" in v:
                    max_end = max(max_end, v["end"])

            if max_end == 49:
                print(f"  ✅ Modality slices correctly end at index 49 (Full 49D space mapped)")
            else:
                print(f"  ⚠️ Modality slices end at index {max_end}. Expected 49 for the Dex3 WBC configuration.")
                compliance_passed = False

        except Exception as e:
            print(f"  ❌ Failed to parse modality.json: {e}")
            compliance_passed = False

    # 3. Check data parquet schema (Sample the first episode)
    print("\n[3. Data Parquet Schema & Dimensions]")
    data_dir = base_dir / "data"
    parquet_files = list(data_dir.rglob("*.parquet"))
    if parquet_files:
        sample_parquet = parquet_files[0]
        try:
            df_sample = pd.read_parquet(sample_parquet)
            required_cols = ["observation.state", "action", "timestamp", "episode_index", "index"]
            for col in required_cols:
                if col in df_sample.columns:
                    print(f"  ✅ Parquet contains '{col}'")
                else:
                    print(f"  ❌ Parquet missing '{col}'")
                    compliance_passed = False

            # --- Check physical array dimensions in the Parquet file ---
            if "observation.state" in df_sample.columns and "action" in df_sample.columns:
                state_dim = len(df_sample.iloc[0]["observation.state"])
                action_dim = len(df_sample.iloc[0]["action"])
                expected_dim = 49

                if state_dim == expected_dim:
                    print(f"  ✅ 'observation.state' array is exactly {state_dim}D")
                else:
                    print(f"  ❌ 'observation.state' array is {state_dim}D (Expected {expected_dim}D)")
                    compliance_passed = False

                if action_dim == expected_dim:
                    print(f"  ✅ 'action' array is exactly {action_dim}D")
                else:
                    print(f"  ❌ 'action' array is {action_dim}D (Expected {expected_dim}D)")
                    compliance_passed = False

        except Exception as e:
            print(f"  ❌ Failed to read sample parquet {sample_parquet.name}: {e}")
            compliance_passed = False
    else:
        print("  ❌ No parquet files found in data/ directory (Did you forget dataset.consolidate()?)")
        compliance_passed = False

    # 4. Check video observations
    print("\n[4. Video Observations]")
    videos_dir = base_dir / "videos"
    if videos_dir.exists():
        mp4_files = list(videos_dir.rglob("*.mp4"))
        if mp4_files:
            print(f"  ✅ Found {len(mp4_files)} .mp4 video files")
        else:
            print("  ❌ No .mp4 files found in videos/ directory")
            compliance_passed = False
    else:
        print("  ❌ videos/ directory not found")
        compliance_passed = False

    print("\n[Compliance Summary]")
    if compliance_passed:
        print("  🎉 PASSED: Dataset structure and 49D tensor shapes meet requirements!")
    else:
        print("  ⚠️ FAILED: Dataset is missing components or has dimensional mismatches. Check the ❌/⚠️ marks above.")

    print("\n" + "="*60)

    # ==========================================
    # GENERAL STATISTICS
    # ==========================================

    # 1. Read info.json for high-level stats
    info_path = meta_dir / "info.json"
    if info_path.exists():
        with open(info_path, "r") as f:
            info = json.load(f)
        print("\n[Overall Stats]")
        print(f"- Total Episodes : {info.get('total_episodes', 'N/A')}")
        print(f"- Total Frames   : {info.get('total_frames', 'N/A')}")
        print(f"- FPS            : {info.get('fps', 'N/A')}")

    # 2. Read tasks (Try jsonl first, fallback to parquet)
    task_dict = {}
    print("\n[Available Tasks]")
    tasks_jsonl = meta_dir / "tasks.jsonl"
    tasks_parquet = meta_dir / "tasks.parquet"

    if tasks_jsonl.exists():
        with open(tasks_jsonl, "r", encoding="utf-8") as f:
            for line in f:
                task_data = json.loads(line)
                task_dict[task_data["task_index"]] = task_data["task"]
        for idx, task_name in task_dict.items():
            print(f"- Index {idx}: '{task_name}'")
    elif tasks_parquet.exists():
        tasks_df = pd.read_parquet(tasks_parquet)
        task_col = next((col for col in ['task', 'tasks', 'instruction', 'goal', 'name'] if col in tasks_df.columns), None)
        if task_col and 'task_index' in tasks_df.columns:
            task_dict = dict(zip(tasks_df['task_index'], tasks_df[task_col]))
            for idx, task_name in task_dict.items():
                print(f"- Index {idx}: '{task_name}'")
    else:
        print("[!] No task metadata found (neither .jsonl nor .parquet).")

    # 3. Read episodes metadata to get the distribution
    episodes_jsonl = meta_dir / "episodes.jsonl"
    episodes_parquet = meta_dir / "episodes.parquet"

    print("\n[Episodes per Task]")
    if episodes_jsonl.exists():
        # Parse JSONL
        counts = {}
        lengths = []
        with open(episodes_jsonl, "r", encoding="utf-8") as f:
            for line in f:
                ep_data = json.loads(line)
                lengths.append(ep_data.get("length", 0))
                # Handle task list
                tasks = ep_data.get("tasks", [])
                for t in tasks:
                    counts[t] = counts.get(t, 0) + 1

        for task_idx, count in counts.items():
            task_name = task_dict.get(task_idx, f"Unknown Task (Index {task_idx})")
            print(f"- '{task_name}': {count} episodes")

        if lengths:
            print("\n[Episode Length Stats (Frames)]")
            print(f"- Average: {sum(lengths)/len(lengths):.1f} frames")
            print(f"- Min    : {min(lengths)} frames")
            print(f"- Max    : {max(lengths)} frames")

    elif episodes_parquet.exists():
        # Fallback to Parquet logic
        episodes_df = pd.read_parquet(episodes_parquet)
        if 'tasks' in episodes_df.columns:
            counts = episodes_df.explode('tasks')['tasks'].value_counts()
        elif 'task_index' in episodes_df.columns:
            counts = episodes_df['task_index'].value_counts()
        else:
            counts = pd.Series()

        for task_idx, count in counts.items():
            task_name = task_dict.get(task_idx, f"Unknown Task (Index {task_idx})")
            print(f"- '{task_name}': {count} episodes")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inspect LeRobot dataset metadata and check GR00T compliance.")
    parser.add_argument(
        "--repo-id",
        type=str,
        default="junweiliang/wbc_5tasks",
        help="The Hugging Face repo ID of the dataset to inspect (e.g., junweiliang/wbc_5tasks)."
    )

    args = parser.parse_args()
    inspect_lerobot_dataset(repo_id=args.repo_id)
