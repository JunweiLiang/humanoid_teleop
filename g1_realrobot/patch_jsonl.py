import argparse
import json
import os

def patch_episodes_jsonl(file_path):
    if not os.path.exists(file_path):
        print(f"❌ Error: Could not find file at '{file_path}'")
        return

    updated_records = []
    success_count = 0

    print(f"Reading {file_path}...")

    # Read and modify the lines
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue

            try:
                record = json.loads(line)

                # Dynamically calculate the chunk index (LeRobot uses 1000 per chunk)
                ep_idx = record.get("episode_index", 0)
                record["chunk_index"] = ep_idx // 1000

                updated_records.append(json.dumps(record) + "\n")
                success_count += 1

            except json.JSONDecodeError:
                print(f"⚠️ Warning: Could not parse line, skipping: {line.strip()}")
                updated_records.append(line) # Keep the broken line just in case

    # Overwrite the original file with the updated records
    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(updated_records)

    print(f"✅ Successfully added 'chunk_index' to {success_count} episodes in {file_path}!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Patch an existing episodes.jsonl file to include chunk_index.")
    parser.add_argument("--path", type=str, required=True, help="Full path to your episodes.jsonl file")

    args = parser.parse_args()
    patch_episodes_jsonl(args.path)
