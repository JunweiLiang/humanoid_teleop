import argparse
#from lerobot.common.datasets.lerobot_dataset import LeRobotDataset
from lerobot.datasets.lerobot_dataset import LeRobotDataset

# 解析命令行参数
parser = argparse.ArgumentParser(description='Calculate LeRobot dataset statistics')
parser.add_argument('repo_id', type=str, help='Dataset repo_id or local path (e.g., /path/to/dataset or username/dataset_name)')
args = parser.parse_args()

# 加载本地数据集
# 注意：数据集的实际路径应该是包含meta和data文件夹的目录
dataset = LeRobotDataset(repo_id=args.repo_id)

# 这个 num_frames 就是公式里的 Total Samples
print(f"Total samples (frames): {dataset.num_frames}")
print(f"Number of episodes: {dataset.num_episodes}")
print(f"Average frames per episode: {dataset.num_frames / dataset.num_episodes:.2f}")
