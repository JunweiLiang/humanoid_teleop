# note on VLA

## Diffusion vs. Flow Matching
+ `https://diffusionflow.github.io/`
+ 这两个的前向过程其实是类似的，不是一个更curve一个更straight
+ diffusion models and Gaussian flow matching are equivalent
+ diffusion: destroy a datapoint by missing it with gaussian noise over time
    + 去噪过程，给定随机gaussian noise, 用一个网络预测sample，这个过程是deterministic
+ Flow matching: 推理过程是data point 和噪音的 线性组合

## Gr00T 1.6
Blog: `https://research.nvidia.com/labs/gear/gr00t-n1_6/`. Key notes:
+ 2B VLM + 32-layer DiT
+ co-training with pretraining data during post-training
+ predict relative actions
+ state regularization?
+ Pretrained statistics vs. post-training statistics?
+ Iterative DAgger: Iterative DAgger (Dataset Aggregation) for Vision-Language-Action (VLA) models is a powerful way to fix "distribution shift"
    + 实机实验，收集失败的数据，当要失败的states，人工重新收集该states下的训练数据，重新训练
+ Test-time and train-time RTC provide performance boosts to motion smoothness and robustness during asynchronous rollouts.
    + Test-Time Real time chunking: 下一轮推理的时候，获取机器要执行的action，加入到当前的states，作为下一轮推理的输入，保证动作平滑
        + 问题是会增加计算开销
        + Pi0 Test-Time RTC: NeurIPS'25 paper: `https://www.pi.website/download/real_time_chunking.pdf`
            + 可以支持300ms的推理延迟，一般整个prediction horizon才1秒50Hz
            + 如何评测平滑度：看关节的速度、加速度是否有曲线陡峭
            + 如何评测延迟：关节的position曲线，对比变化的时间
            + 可以用于任意 diffusion-based / flow-based model
            + prediction horizon H: 50 步
            + execution horizon s, s ~= H/2
            + conditional flow matching model:
                + sampled random noise -> NN 输出 flow velocity fields, 然后从0 -> 1 去噪
            + target 50Hz意味20ms latency, 4090推理 3B-pi0模型都要47ms
            + 每个timestep chunk就是20ms.预测了50步，假设inference delay是d=4 80ms，
                + 所以第1步到第4步都是用之前的action, prefix;
                + 步4 - 步10，这时候有上一次的推理action chunk，也有新的action chunk，原来的action随时间用指数下降融合新的action chunk
                    + 融合算法用in-painting, 从flow matching的velocity vector field 入手
                + 步11-步15就是execution horizon, 全靠新的action chunk执行，
                + inference delay是有可能变化的，推理过程需要记录inference delay(可以包含网络延迟等)

    + Train-Time RTC: 训练的时候，action观测+ prefix (将要执行的动作)，然后再输出action
        + pi paper: `https://arxiv.org/pdf/2512.05964`
        + 微信公众号: `https://mp.weixin.qq.com/s/e1Ph46lg780IZx0ubrupkg` 翻译得很差别看
        + Gr00T用的是双系统架构，去解决延迟问题，结构就比较复杂
        + 关键的几个variable，H prediction horizon=50步，s= execution horizon，真正执行的步数，变化的，d 是 inference delay，比如4步，才能拿到新的 H 步推理; d 也是变化的
        + 训练中，d 随机采样，这样 50 步里面，有d步是用ground truth action不需要flow matching loss
            + 模拟实验，设置s=max(d, 1)，这样可以把d 加大，对比实验
            + pi0.6 真机实验，用H100服务器，5 denoising step，推理延迟平均108ms，也就是d=5

+ 使用人类data - by Pi: https://www.physicalintelligence.company/research/human_to_robot
    + 用人手数据和机器人数据一起finetune; 手腕相机在手掌下面
    + 结论：pretraining 要足够diverse，然后human to robot提升才明显
    + 可以实现对于类似的新任务，只提供人类数据，就能训练出机器人做这个任务



+ Gr00T 数据采集
    + for a task, video/state/action, 用 Huggingface LeRobot V2格式
        + 数据准备说明：`https://github.com/NVIDIA/Isaac-GR00T/blob/main/getting_started/data_preparation.md`



+ Gr00T 推理架构
    + 输入输出
        + video: B, T, H, W, 3; state: B, T, D (关节数, float); language: B, 1
         output - action: (B, T, D); joint positions in radians, velocities in rad/s; not normalized, 可以直接机器人执行

    + 可以分成 Server-Client
    ```
        Server on a GPU machine
        policy client -> connect to server via network
        # Use just like a regular policy
        observation = get_observation()  # Your observation in Policy API format
        action, info = policy.get_action(observation)
    ```
    + ReplayPolicy 接口，可以直接重放训练的数据,用来调试 (同样开启一个server, 给定一个数据集路径就行)
    + Gr00T WBC任务专门有个说明：`https://github.com/NVIDIA/Isaac-GR00T/tree/main/examples/GR00T-WholeBodyControl`, 有仿真测试
        + 模型说明:

            + RoboCasa (数据集) -> RoboSuite v1.5 (环境) -> Mujoco
            + GR00T-WholeBodyControl-Balance.onnx, GR00T-WholeBodyControl-Walk.onnx
        + 安装: follow: `https://github.com/NVIDIA/Isaac-GR00T?tab=readme-ov-file#installation-guide`
        ```
            (base) junweil@office-precognition:~/projects/gr00t$ git clone --recurse-submodules https://github.com/NVIDIA/Isaac-GR00T
            # 要用uv
            conda deactivate
            # 安装uv
            curl -LsSf https://astral.sh/uv/install.sh | sh
            # 重启shell就有了; 创建uv环境然后安装 dependancies
                # 先要装好CUDA12.4

                    (base) junweil@office-precognition:~$ conda install -c "nvidia/label/cuda-12.4" cuda-toolkit

                    (base) junweil@office-precognition:~$ $CONDA_PREFIX/bin/nvcc --version
                        nvcc: NVIDIA (R) Cuda compiler driver
                        Copyright (c) 2005-2025 NVIDIA Corporation
                        Built on Fri_Feb_21_20:23:50_PST_2025
                        Cuda compilation tools, release 12.8, V12.8.93
                    # 不知道为啥还是装的cuda 12.8

                    # conda 出现了错误，可能因为装过mamba,要删除
                    python -m pip uninstall conda-libmamba-solver libmambapy -y

                    # 把conda 装的cuda 路径 export出来
                    (base) junweil@office-precognition:~/projects/gr00t$ export CUDA_HOME=$CONDA_PREFIX
                    (base) junweil@office-precognition:~/projects/gr00t$ export PATH=$CONDA_PREFIX/bin:$PATH
                    (base) junweil@office-precognition:~/projects/gr00t$ export LD_LIBRARY_PATH=$CONDA_PREFIX/lib:$LD_LIBRARY_PATH
                    (base) junweil@office-precognition:~/projects/gr00t$ conda deactivate
                    junweil@office-precognition:~/projects/gr00t$ nvcc --version
                    nvcc: NVIDIA (R) Cuda compiler driver
                    Copyright (c) 2005-2025 NVIDIA Corporation
                    Built on Fri_Feb_21_20:23:50_PST_2025
                    Cuda compilation tools, release 12.8, V12.8.93
                    Build cuda_12.8.r12.8/compiler.35583870_0

            junweil@office-precognition:~/projects/gr00t/Isaac-GR00T$ uv sync --python 3.10
            junweil@office-precognition:~/projects/gr00t/Isaac-GR00T$ uv pip install -e .

            # 然后setup wbc eval环境，根据这里: https://github.com/NVIDIA/Isaac-GR00T/tree/main/examples/GR00T-WholeBodyControl#2-evaluate-checkpoint

                $ sudo apt-get install libegl1-mesa-dev libglu1-mesa

                junweil@office-precognition:~/projects/gr00t/Isaac-GR00T$ bash gr00t/eval/sim/GR00T-WholeBodyControl/setup_GR00T_WholeBodyControl.sh
                    # 中间还有可能报错网络问题，要重新跑整个bash

                        # 这个example的环境装在example下，需要这样source:
                            junweil@office-precognition:~/projects/gr00t/Isaac-GR00T$ source gr00t/eval/sim/GR00T-WholeBodyControl/GR00T-WholeBodyControl_uv/.venv/bin/activate

                        # 这个测试没报错

python - <<'PY'
import os
os.environ.setdefault("MUJOCO_GL", "egl")
os.environ.setdefault("PYOPENGL_PLATFORM", "egl")
import gymnasium as gym, robocasa, robosuite
import gr00t_wbc.control.envs.robocasa.sync_env
print("Imports OK:", robosuite.__version__)
env = gym.make("gr00tlocomanip_g1_sim/LMBottlePnP_G1_gear_wbc", enable_render=True)
print("Env OK:", type(env))
PY


        ```
        + 跑release的模型, readme: `https://github.com/NVIDIA/Isaac-GR00T/tree/main/examples/GR00T-WholeBodyControl`
        ```
            # 0. 下载模型：https://huggingface.co/nvidia/GR00T-N1.6-G1-PnPAppleToPlate

                junweil@office-precognition:~/projects/gr00t/Isaac-GR00T$ source gr00t/eval/sim/GR00T-WholeBodyControl/GR00T-WholeBodyControl_uv/.venv/bin/activate
                    $ uv add huggingface_hub

                (.venv) junweil@office-precognition:~/projects/gr00t/Isaac-GR00T$ uv run huggingface-cli download nvidia/GR00T-N1.6-G1-PnPAppleToPlate   --local-dir nvidia/GR00T-N1.6-G1-PnPAppleToPlate   --local-dir-use-symlinks False

                    # 模型就下载到 ~/projects/gr00t/Isaac-GR00T/nvidia/GR00T-N1.6-G1-PnPAppleToPlate

                # 还有一些dependancies

                    uv pip install dm-tree
                    uv pip install albumentations
                    uv pip install peft==0.17.1
                    uv pip install flash-attn==2.7.4.post1
                        lmdb==1.7.5
                        torch==2.7.0
                        torchvision==0.22.0

            # 1. server
                (.venv) junweil@office-precognition:~/projects/gr00t/Isaac-GR00T$ python gr00t/eval/run_gr00t_server.py     --model-path nvidia/GR00T-N1.6-G1-PnPAppleToPlate     --embodiment-tag UNITREE_G1     --use-sim-policy-wrapper

            # 2. client
                junweil@office-precognition:~/projects/gr00t/Isaac-GR00T$ source gr00t/eval/sim/GR00T-WholeBodyControl/GR00T-WholeBodyControl_uv/.venv/bin/activate

                (.venv) junweil@office-precognition:~/projects/gr00t/Isaac-GR00T$ python gr00t/eval/rollout_policy.py     --n_episodes 10     --max_episode_steps=1440     --env_name gr00tlocomanip_g1_sim/LMPnPAppleToPlateDC_G1_gear_wbc     --n_action_steps 20     --n_envs 5 --policy_client_host 127.0.0.1 --policy_client_port 5555

                    Collecting 10 episodes took 223.29983043670654 seconds
                    Video saved to:  /tmp/sim_eval_videos_gr00tlocomanip_g1_sim/LMPnPAppleToPlateDC_G1_gear_wbc_ac20_edf47a70-129a-48be-938a-a03a7407860e
                    results:  ('gr00tlocomanip_g1_sim/LMPnPAppleToPlateDC_G1_gear_wbc', [True, True, True, True, False, False, True, True, True, False], {})
                    success rate:  0.7

        ```

+ 评测
    + Open-loop evaluation: 直接看给定观测，输出的action和ground truth对比, MSE metrics
    + 然后就可以Closed-loop evaluation看成功率

+ 真机RL和 LLM的RL不一样，我们没办法reset，回到上一状态
    + `https://vedder.io/misc/state_of_robot_learning_dec_2025.html`

+ Psi0 WBC
    + `https://github.com/physical-superintelligence-lab/Psi0`
```

```
+ SIMPLE 仿真WBC环境，by Psi ppl; based on Isaac Sim 4.5 + MuJoCo 3.3
    + `https://github.com/physical-superintelligence-lab/SIMPLE`
```
    # 使用uv安装环境

        (base) junweil@office-precognition:~$ conda deactivate
            junweil@office-precognition:~$ curl -LsSf https://astral.sh/uv/install.sh | sh
            downloading uv 0.11.6 x86_64-unknown-linux-gnu
            installing to /home/junweil/.local/bin
              uv
              uvx
            everything's installed!

    # 安装！
        junweil@office-precognition:~/projects/psi$ git clone https://github.com/physical-superintelligence-lab/SIMPLE

        # 需要添加本机ssh pub key 到github
            $ cat ~/.ssh/id_ed25519.pub
            GitHub.com -> Settings -> SSH and GPG keys -> new ssh key

        junweil@office-precognition:~/projects/psi/SIMPLE$ git submodule update --init --recursive

            # delete the pypi index url in pyproject.toml file so uv uses 清华园
                # 还要改一下tool.uv如果出现arm架构依赖错误
                    environments = [
                        "sys_platform == 'linux' and platform_machine == 'x86_64' and platform_python_implementation == 'CPython'"
                    ]
            # 先安装CUDA,
                $ wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/cuda-keyring_1.1-1_all.deb
                $ sudo dpkg -i cuda-keyring_1.1-1_all.deb
                $ sudo apt-get update
                $ sudo apt-get install -y cuda-toolkit-12-6
                $ sudo apt-get install -y pybind11-dev
                $ sudo apt-get install -y libgmpxx4ldbl libgmp-dev

                $ vi ~/.bashrc
                export CUDA_HOME=/usr/local/cuda-12.6
                export PATH=$CUDA_HOME/bin:$PATH
                export LD_LIBRARY_PATH=$CUDA_HOME/lib64:$LD_LIBRARY_PATH
                export TORCH_CUDA_ARCH_LIST="8.9"


        junweil@office-precognition:~/projects/psi/SIMPLE$ UV_HTTP_TIMEOUT=3000 GIT_LFS_SKIP_SMUDGE=1 uv sync --all-groups --index-strategy unsafe-best-match

            # 如果一开始网速慢可以添加UV_INDEX_URL="https://pypi.tuna.tsinghua.edu.cn/simple"
            # 但是出现什么nightly 错误，就要删除上述变量

        junweil@office-precognition:~/projects/psi/SIMPLE$ bash scripts/install_curobo.sh
        junweil@office-precognition:~/projects/psi/SIMPLE$ source .venv/bin/activate

            # 测试

                (simple) junweil@office-precognition:~/projects/psi/SIMPLE$ python scripts/test_env.py

                    # 报错，可能env名字不对

                # 列出所有的env
                (simple) junweil@office-precognition:~/projects/psi/SIMPLE$ python scripts/list_env.py

            # 文档
                $ conda deactivate
                junweil@office-precognition:~/projects/psi/SIMPLE$ source .venv/bin/activate
                (simple) junweil@office-precognition:~/projects/psi/SIMPLE$ uv run --group docs sphinx-autobuild docs/source docs/build/html --host 0.0.0.0 --port 8001

                http://office.precognition.team:8001/
```
+ 可视化我们中期采集的数据
```
    # 5个任务的可视化视频:
        https://drive.google.com/drive/folders/120JGNOUmESJtJZ3OTWuyyHOllV9xOLBc
    # 可视化数据例子，move_box

        (tv) junweil@office-precognition:~/projects/humanoid_teleop$ python g1_realrobot/visualize_wbc_episodes.py ~/projects/huawei_data/wbc_task5/move_box/episode_0015/data.json assets/g1/g1_body29_hand14.urdf --fps 60 --image_path ~/projects/huawei_data/wbc_task5/move_box/episode_0015/colors/ --hand_type dex3 --show_states

    # Note
        # 底层用homie locomotion
        # 视频数据用realsense d435 640x480，视角小，数据采集是60fps; 尤其是move_box， states 看起来更准, action不对
        # 每一帧数据包括 (states 下面)
            # left_arm/right_arm -> qpos [7维度] shoulder pyr, elbow, wrist pyr
            # left_ee/right_ee -> qpos [7维度]多个手指
            # waist -> qpos [3维度, yaw, roll, pitch]，应该只有yaw非零
            # leg -> qpos [12维度]， 双腿+脚2
            # actions 下面
                # left_trigger/right_trigger: 0-1
                # loco_cmd: [v_x, v_y, v_yaw, height 1.65 - 0.8]
```
+ 转换中期数据到LeRobot v2 格式
```
    # LeRoBot v2数据格式

    # 参考代码
        # 宇树官方遥操作采的数据转换代码
            # https://github.com/unitreerobotics/unitree_lerobot/tree/main?tab=readme-ov-file#23-%EF%B8%8F-data-conversion

        # Psi也有转换
            https://github.com/physical-superintelligence-lab/Psi0/blob/main/scripts/data/raw_to_lerobot_v2.py

    # 转换华为wbc 5 tasks数据

        (base) junweil@office-precognition:~/projects/huawei_data$ cp -r wbc_task5 wbc_task5_lerobotv2

        # 原来的数据集中可能有缺失的episode，要重新按顺序命名

        (tv) junweil@office-precognition:~/projects/huawei_data$ python ~/projects/humanoid_teleop/g1_realrobot/sort_and_rename_folders.py --data_dir wbc_task5_lerobotv2/move_box/
            close_washer_door/          move_box/                   pick_up_object_from_ground/
            move_and_open_pot/          open_washer_door/

        # convert based on the data.json

            # install the lerobot package (copied from https://github.com/unitreerobotics/unitree_lerobot/unitree_lerobot/lerobot)

            (tv) junweil@office-precognition:~/projects/humanoid_teleop/g1_realrobot/lerobot$ pip install -e .

        # convert to LeRobot v2 and Gr00T complient (就是多一个modality.json)
            # https://github.com/NVIDIA/Isaac-GR00T/blob/main/getting_started/data_preparation.md

        (tv) junweil@office-precognition:~/projects/huawei_data$ python ~/projects/humanoid_teleop/g1_realrobot/convert_unitree_json_to_lerobot.py --raw-dir wbc_task5_lerobotv2/ --repo-id junweiliang/wbc_5tasks --downsample-factor 2 --use-future-state-as-action --valp 0.1 --repo-id-val junweiliang/wbc_5tasks_val0.1

            # LeRobot 会提取jpg 生成mp4文件

            # 要一个小时，数据会存在
                ~/.cache/huggingface/lerobot/junweiliang/wbc_5tasks

                [WARNING] Skipping Episode 168 (wbc_task5_lerobotv2/open_washer_door/episode_0000)
                  Reason: Shape mismatch. State: 29 (expected 43).
                  (This usually means hand tracking data was absent during recording).

                # 分一些到validation里
                  ~/.cache/huggingface/lerobot/junweiliang/wbc_5tasks_val0.1

                # 有一些episode可能手的states 没有录制，没有数据就跳过。lerobot会跳过这个episode

                # 把原始数据的state和action，字段复制补齐，这样两边都是49

                    # raw_state is 43D: Arms(14) + Hands(14) + Waist(3) + Legs(12)
                    # raw_action is 37D: Arms(14) + Hands(14) + Waist(3) + Triggers(2) + Loco(4)

                # 会按照 Gr00T说的，额外生成modality.json，还有旧版的.jsonl meta文件
                    # https://github.com/NVIDIA/Isaac-GR00T/blob/main/getting_started/data_preparation.md


            # 转换完后查看数据集, 原本是5个任务一共281 episode，
                # train set 252
                    (tv) junweil@office-precognition:~/projects/huawei_data$ python ~/projects/humanoid_teleop/g1_realrobot/inspect_lerobot_dataset.py --repo-id junweiliang/wbc_5tasks

                    [Overall Stats]
                    - Total Episodes : 252
                    - Total Frames   : 124560
                    - FPS            : 30

                    [Available Tasks]
                    - Index 0: 'close_washer_door'
                    - Index 1: 'move_and_open_pot'
                    - Index 2: 'move_box'
                    - Index 3: 'open_washer_door'
                    - Index 4: 'pick_up_object_from_ground'

                    [Episodes per Task]
                    - 'close_washer_door': 50 episodes
                    - 'move_and_open_pot': 50 episodes
                    - 'move_box': 49 episodes
                    - 'open_washer_door': 48 episodes
                    - 'pick_up_object_from_ground': 55 episodes

                    [Episode Length Stats (Frames)]
                    - Average: 494.3 frames
                    - Min    : 143 frames
                    - Max    : 1381 frames

                # val set 28 episode

                    (tv) junweil@office-precognition:~/projects/huawei_data$ python ~/projects/humanoid_teleop/g1_realrobot/inspect_lerobot_dataset.py --repo-id junweiliang/wbc_5tasks_val0.1

                    [Episodes per Task]
                    - 'close_washer_door': 4 episodes
                    - 'move_and_open_pot': 7 episodes
                    - 'move_box': 8 episodes
                    - 'open_washer_door': 3 episodes
                    - 'pick_up_object_from_ground': 6 episodes

            # 可视化lerobot 数据

                (tv) junweil@office-precognition:~/projects$ python ~/projects/humanoid_teleop/g1_realrobot/lerobot/src/lerobot/scripts/lerobot_dataset_viz.py --repo-id junweiliang/wbc_5tasks --episode-index 0

                    # 会打开rerun窗口，看到视频，还有各个关节的曲线图


            # gr00T 可能会把全部5个任务一起训练。我们生成数据集的时候挑单个任务,比如关闭洗衣机门，搬箱子，捡起物体

                (tv) junweil@office-precognition:~/projects/huawei_data$ python ~/projects/humanoid_teleop/g1_realrobot/convert_unitree_json_to_lerobot.py --raw-dir wbc_task5_lerobotv2/ --repo-id junweiliang/wbc_close_washer_door --downsample-factor 2 --use-future-state-as-action --valp 0.1 --repo-id-val junweiliang/wbc_close_washer_door_val0.1 --tasks close_washer_door

                (tv) junweil@office-precognition:~/projects/huawei_data$ python ~/projects/humanoid_teleop/g1_realrobot/convert_unitree_json_to_lerobot.py --raw-dir wbc_task5_lerobotv2/ --repo-id junweiliang/wbc_move_box --downsample-factor 2 --use-future-state-as-action --valp 0.1 --repo-id-val junweiliang/wbc_move_box_val0.1 --tasks move_box

                (tv) junweil@office-precognition:~/projects/huawei_data$ python ~/projects/humanoid_teleop/g1_realrobot/convert_unitree_json_to_lerobot.py --raw-dir wbc_task5_lerobotv2/ --repo-id junweiliang/wbc_pick_up_object_from_ground --downsample-factor 2 --use-future-state-as-action --valp 0.1 --repo-id-val junweiliang/wbc_pick_up_object_from_ground_val0.1 --tasks pick_up_object_from_ground

                # 再可视化一下
                    (tv) junweil@office-precognition:~/projects$ python ~/projects/humanoid_teleop/g1_realrobot/lerobot/src/lerobot/scripts/lerobot_dataset_viz.py --repo-id junweiliang/wbc_pick_up_object_from_ground --episode-index 3

                # 格式检查
                    (tv) junweil@office-precognition:~/projects/huawei_data$ python ~/projects/humanoid_teleop/g1_realrobot/inspect_lerobot_dataset.py --repo-id junweiliang/wbc_pick_up_object_from_ground



            # 上述代码得到的数据是LeRobot v3，需要转回v2
                # v3 和v2区别： https://io-ai.tech/platform/guides/Pipeline/LeRobot/LeRobotV2V3Format/
                    # 主要是视频，v2按照episode存， v3弄成大文件
                (tv) junweil@office-precognition:~/projects/wbc_manipulation/Isaac-GR00T$ python scripts/lerobot_conversion/convert_v3_to_v2.py --repo-id junweiliang/wbc_pick_up_object_from_ground

                # 会直接修改原有数据集：/home/junweil/.cache/huggingface/lerobot/junweiliang/wbc_pick_up_object_from_ground

                # 生成v3.0备份：/home/junweil/.cache/huggingface/lerobot/junweiliang/wbc_pick_up_object_from_ground_v3.0/

                # 还缺modality.json

                (tv) junweil@office-precognition:~/.cache/huggingface/lerobot/junweiliang$ cp wbc_move_and_open_pot_v3.0/meta/modality.json wbc_move_and_open_pot/meta/


                # validation
                    (tv) junweil@office-precognition:~/projects/wbc_manipulation/Isaac-GR00T$ python scripts/lerobot_conversion/convert_v3_to_v2.py --repo-id junweiliang/wbc_pick_up_object_from_ground_val0.1

                    (tv) junweil@office-precognition:~/.cache/huggingface/lerobot/junweiliang$ cp wbc_pick_up_object_from_ground_val0.1_v3.0/meta/modality.json wbc_pick_up_object_from_ground_val0.1/meta/

            (tv) junweil@office-precognition:~/.cache/huggingface/lerobot/junweiliang$ ls
                # 一共24， 5个任务合集+分开，每个有3.0/2.1的train+val
                wbc_5tasks                         wbc_move_and_open_pot              wbc_open_washer_door
                wbc_5tasks_v3.0                    wbc_move_and_open_pot_v3.0         wbc_open_washer_door_v3.0
                wbc_5tasks_val0.1                  wbc_move_and_open_pot_val0.1       wbc_open_washer_door_val0.1
                wbc_5tasks_val0.1_v3.0             wbc_move_and_open_pot_val0.1_v3.0  wbc_open_washer_door_val0.1_v3.0
                wbc_close_washer_door              wbc_move_box                       wbc_pick_up_object_from_ground
                wbc_close_washer_door_v3.0         wbc_move_box_v3.0                  wbc_pick_up_object_from_ground_v3.0
                wbc_close_washer_door_val0.1       wbc_move_box_val0.1                wbc_pick_up_object_from_ground_val0.1
                wbc_close_washer_door_val0.1_v3.0  wbc_move_box_val0.1_v3.0           wbc_pick_up_object_from_ground_val0.1_v3.0

            # pack the data, 把全部任务、单个任务都一并打包
                (tv) junweil@office-precognition:~/.cache/huggingface/lerobot$ tar -zcvf lerobot_wbc_datasets_v3+v2_5tasks+5singletask.tgz junweiliang/

```
+ 微调Gr00T N1.6
```
    [04/14/2026] # fork and install
        # https://github.com/JunweiLiang/Isaac-GR00T
        # office 已经安装了uv, CUDA 12.6 在根环境
        junweil@office-precognition:~/projects/wbc_manipulation$ git clone https://github.com/JunweiLiang/Isaac-GR00T

        junweil@office-precognition:~/projects/wbc_manipulation/Isaac-GR00T$ git submodule update --init --recursive

        junweil@office-precognition:~/projects/wbc_manipulation/Isaac-GR00T$ bash scripts/deployment/dgpu/install_deps.sh

        # 下载 N1.6 checkpoint

            $ pip install -U "huggingface_hub[cli]"
            (base) junweil@office-precognition:~/projects/wbc_manipulation$ hf download nvidia/GR00T-N1.6-3B --local-dir ./GR00T-N1.6-3B

        # gpu3 安装
            # 1. 安装uv

                curl -LsSf https://astral.sh/uv/install.sh | sh

            # 2. 安装cuda 12.6
                $ wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/cuda-keyring_1.1-1_all.deb
                $ sudo dpkg -i cuda-keyring_1.1-1_all.deb
                $ sudo apt-get update
                $ sudo apt-get install -y cuda-toolkit-12-6 pybind11-dev libgmpxx4ldbl libgmp-dev

                $ vi ~/.bashrc
export CUDA_HOME=/usr/local/cuda-12.6
export PATH=$CUDA_HOME/bin:$PATH
export LD_LIBRARY_PATH=$CUDA_HOME/lib64:$LD_LIBRARY_PATH

            # 3. gr00t
                junweil@precognition-gpu3:~/projects/wbc_manipulation$ git clone https://github.com/JunweiLiang/Isaac-GR00T
                junweil@precognition-gpu3:~/projects/wbc_manipulation/Isaac-GR00T$ git submodule update --init --recursive

                # 要用清华源
                junweil@precognition-gpu3:~/projects/wbc_manipulation/Isaac-GR00T$ UV_DEFAULT_INDEX="https://pypi.tuna.tsinghua.edu.cn/simple" UV_CONCURRENT_DOWNLOADS=10 UV_HTTP_TIMEOUT=60 bash scripts/deployment/dgpu/install_deps.sh

    # 数据和config note

        # Gr00T 在数据集中有meta/modality.json，说明了lerobot里面的数据的维度和机器人本体 的对应
        # finetune模型需要写一个config 说明如何使用这些数据
            # https://github.com/NVIDIA/Isaac-GR00T/blob/main/getting_started/data_config.md

                # Last 3 frames for video (temporal stacking)
                delta_indices=[-2, -1, 0]

                # 16-step action prediction horizon
                delta_indices=list(range(0, 16))

                modality_keys -> match the ones in modality.json
            1. video:
            2. state:
            3. action:
            4. language:

        # 添加 my_configs/g1_dex3_gripper_homie.py,

        # 2x4090 48GB 测试
            # 单个任务训练

                # 多卡必须torchrun

                junweil@office-precognition:~/projects/wbc_manipulation/Isaac-GR00T$ uv run torchrun --nproc_per_node=2 gr00t/experiment/launch_finetune.py      --base-model-path ../GR00T-N1.6-3B      --dataset-path ~/.cache/huggingface/lerobot/junweiliang/wbc_pick_up_object_from_ground      --embodiment-tag NEW_EMBODIMENT      --modality-config-path my_configs/g1_dex3_gripper_homie.py      --save-total-limit 5      --learning_rate 1e-4      --save-steps 2000      --max-steps 10000      --use-wandb      --warmup_ratio 0.05      --weight_decay 1e-5      --global-batch-size 32      --color-jitter-params brightness 0.3 contrast 0.4 saturation 0.5 hue 0.08      --dataloader-num-workers 6      --output-dir experiments/my_wbc_pick_up_object_from_ground

                # 需要一个wandb账号
                    # https://wandb.ai/authorize?signup=true&ref=models
                    # 需要API key  ~/Desktop/github_projects/wandb_api_key.txt

                # 2x4090, bs=32, s=10k 需要3小时wbc_pick_up_object_from_ground
                    # bs=64,s=10k 需要4小时move_box
                    # bs=128 OOM
                    # dataloader-num-workers 4 比 8要更快 (32 thread CPU, 所以除以8)
                    # GPU温度44度，260/450w, 所以效率比较差
                    # CPU 90%, 内存33GB

                # 看training log: https://wandb.ai/home

                # open-loop 评测

                    # 训练集, 挑10个ep, 看平均的MSE, MAE

                        junweil@office-precognition:~/projects/wbc_manipulation/Isaac-GR00T$ uv run python gr00t/eval/open_loop_eval.py     --dataset-path ~/.cache/huggingface/lerobot/junweiliang/wbc_pick_up_object_from_ground/  --embodiment-tag NEW_EMBODIMENT     --model-path experiments/my_wbc_pick_up_object_from_ground/checkpoint-10000/     --traj-ids 0 1 2 3 4 5 6 7 8 9     --action-horizon 16 --save-plot-path experiments/my_wbc_pick_up_object_from_ground/open_loop_train_ep0-10.jpg

                        INFO:root:Average MSE across all trajs: 0.00018743000691756606
                        INFO:root:Average MAE across all trajs: 0.004905599635094404

                    # validation set, 0-5 ep

                        junweil@office-precognition:~/projects/wbc_manipulation/Isaac-GR00T$ uv run python gr00t/eval/open_loop_eval.py     --dataset-path ~/.cache/huggingface/lerobot/junweiliang/wbc_pick_up_object_from_ground_val0.1/  --embodiment-tag NEW_EMBODIMENT     --model-path experiments/my_wbc_pick_up_object_from_ground/checkpoint-10000/     --traj-ids 0 1 2 3 4 5     --action-horizon 16 --save-plot-path experiments/my_wbc_pick_up_object_from_ground/open_loop_val_ep0-5.jpg --steps 1000

                        INFO:root:Average MSE across all trajs: 0.0024767746217548847
                        INFO:root:Average MAE across all trajs: 0.01650149933993816


                    # 可视化一下, 还有看上面的关节推理plot

                    (tv) junweil@office-precognition:~/projects$ python ~/projects/humanoid_teleop/g1_realrobot/lerobot/src/lerobot/scripts/lerobot_dataset_viz.py --repo-id junweiliang/wbc_pick_up_object_from_ground --episode-index 3

        # gr00t 官方wbc 的finetune config
            export NUM_GPUS=8

            torchrun --nproc_per_node=$NUM_GPUS --master_port=29500 \
                gr00t/experiment/launch_finetune.py \
                --base_model_path  nvidia/GR00T-N1.6-3B \
                --dataset_path examples/GR00T-WholeBodyControl/PhysicalAI-Robotics-GR00T-X-Embodiment-Sim/unitree_g1.LMPnPAppleToPlateDC \
                --embodiment_tag UNITREE_G1 \
                --num_gpus $NUM_GPUS \
                --output_dir /tmp/g1_finetune \
                --save_total_limit 5 \
                --max_steps 10000 \
                --warmup_ratio 0.05 \
                --weight_decay 1e-5 \
                --learning_rate 1e-4 \
                --use_wandb \
                --global_batch_size 1024 \
                --dataloader_num_workers 6 \
                --color_jitter_params brightness 0.3 contrast 0.4 saturation 0.5 hue 0.08

        # gpu3获取数据

            (tv) junweil@office-precognition:~/.cache/huggingface/lerobot$ scp lerobot_wbc_datasets_v3+v2_5tasks+5singletask.tgz  junweil@gpu3.precognition.team:~/

            # 数据放在
                (base) junweil@precognition-gpu3:~/projects/wbc_manipulation/junweiliang$ ls
                    wbc_5tasks                         wbc_move_and_open_pot              wbc_open_washer_door
                    wbc_5tasks_v3.0                    wbc_move_and_open_pot_v3.0         wbc_open_washer_door_v3.0
                    wbc_5tasks_val0.1                  wbc_move_and_open_pot_val0.1       wbc_open_washer_door_val0.1
                    wbc_5tasks_val0.1_v3.0             wbc_move_and_open_pot_val0.1_v3.0  wbc_open_washer_door_val0.1_v3.0
                    wbc_close_washer_door              wbc_move_box                       wbc_pick_up_object_from_ground
                    wbc_close_washer_door_v3.0         wbc_move_box_v3.0                  wbc_pick_up_object_from_ground_v3.0
                    wbc_close_washer_door_val0.1       wbc_move_box_val0.1                wbc_pick_up_object_from_ground_val0.1
                    wbc_close_washer_door_val0.1_v3.0  wbc_move_box_val0.1_v3.0           wbc_pick_up_object_from_ground_val0.1_v3.0

            # 训练！

                junweil@precognition-gpu3:~/projects/wbc_manipulation/Isaac-GR00T$ uv run torchrun --nproc_per_node=2 gr00t/experiment/launch_finetune.py      --base-model-path ../GR00T-N1.6-3B      --dataset-path ../junweiliang/wbc_close_washer_door      --embodiment-tag NEW_EMBODIMENT      --modality-config-path my_configs/g1_dex3_gripper_homie.py      --save-total-limit 3      --learning_rate 1e-4      --save-steps 2000      --max-steps 10000      --use-wandb      --warmup_ratio 0.05      --weight_decay 1e-5      --global-batch-size 32      --color-jitter-params brightness 0.3 contrast 0.4 saturation 0.5 hue 0.08      --dataloader-num-workers 6  --output-dir experiments/mygpu3_wbc_close_washer_door

                # 2xA6000, b=32,s=10k, pick_up_object_from_ground也要3小时，和2x4090差不多，但是效率比较高，270w/300w

                # open loop eval, train/val

                    junweil@precognition-gpu3:~/projects/wbc_manipulation/Isaac-GR00T$ uv run python gr00t/eval/open_loop_eval.py     --dataset-path ~/projects/wbc_manipulation/junweiliang/wbc_close_washer_door_val0.1  --embodiment-tag NEW_EMBODIMENT     --model-path experiments/mygpu3_wbc_close_washer_door/checkpoint-10000/     --traj-ids 0 1 2 3 4 5     --action-horizon 16 --save-plot-path experiments/mygpu3_wbc_close_washer_door/open_loop_val_ep0-5.jpg


            # 8卡, batch_size=128, (256/512 OOM), s=10k
                bs=64,2xGPU, ok
                bs=128,2xGPU, OOM, bs=128,8xGPU, OOM
                bs=256, 8xGPU, gradient-accumulation-steps 4, export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True OOM
                bs=128, 2xGPU, --gradient-accumulation-steps 8 OOM??

                # bs=64, 2卡，训练5task, dataworker=6, 10k step, (worker=4会经常要等shard)
                    #  CPU利用率44%, 内存使用40GB

                junweil@precognition-gpu3:~/projects/wbc_manipulation/Isaac-GR00T$ uv run torchrun --nproc_per_node=2 gr00t/experiment/launch_finetune.py      --base-model-path ../GR00T-N1.6-3B      --dataset-path ../junweiliang/wbc_5tasks      --embodiment-tag NEW_EMBODIMENT      --modality-config-path my_configs/g1_dex3_gripper_homie.py      --save-total-limit 3      --learning_rate 1e-4      --save-steps 2000      --max-steps 10000      --use-wandb      --warmup_ratio 0.05      --weight_decay 1e-5      --global-batch-size 64 --color-jitter-params brightness 0.3 contrast 0.4 saturation 0.5 hue 0.08      --dataloader-num-workers 6  --output-dir experiments/mygpu3_wbc_5tasks_bs64_s10k

                # 训练5 tasks, open loop 测试 0-5, 100-5, 200-5 的episode
                    # validation 测试 0 1 8 9 12 13 19 20 24 25

                        junweil@precognition-gpu3:~/projects/wbc_manipulation/Isaac-GR00T$ uv run python gr00t/eval/open_loop_eval.py     --dataset-path ~/projects/wbc_manipulation/junweiliang/wbc_5tasks_val0.1  --embodiment-tag NEW_EMBODIMENT     --model-path experiments/mygpu3_wbc_5tasks_bs64_s10k/checkpoint-10000/     --traj-ids 0 1 8 9 12 13 19 20 24 25     --action-horizon 16 --save-plot-path experiments/mygpu3_wbc_5tasks_bs64_s10k/open_loop_val_5tasks.jpg

                    # 查看validation episode数量:

                        (tv) junweil@office-precognition:~/projects/huawei_data$ python ~/projects/humanoid_teleop/g1_realrobot/inspect_lerobot_dataset.py --repo-id junweiliang/wbc_5tasks_val0.1

                        [Episodes per Task]
                        - 'Unknown Task (Index close_washer_door)': 4 episodes
                        - 'Unknown Task (Index move_and_open_pot)': 7 episodes
                        - 'Unknown Task (Index move_box)': 8 episodes
                        - 'Unknown Task (Index open_washer_door)': 3 episodes
                        - 'Unknown Task (Index pick_up_object_from_ground)': 6 episodes

                    # 图像：
                        junweiliang@work_laptop:~/Downloads$ scp -r junweil@gpu3.precognition.team:~/projects/wbc_manipulation/Isaac-GR00T/experiments/mygpu3_wbc_5tasks_bs64_s10k/*.jpg .

            # [04/17/2026] 观察：单卡batch_size 64可以跑，但是8卡128 都OOM，肯定有bug, gradient accumulation也不work。后续用N1.7的code

            # gpu3 单卡跑：
                junweil@precognition-gpu3:~/projects/wbc_manipulation/Isaac-GR00T$ CUDA_VISIBLE_DEVICES=2 uv run torchrun --nproc_per_node=1 --master_port=29501 gr00t/experiment/launch_finetune.py      --base-model-path ../GR00T-N1.6-3B      --dataset-path ../junweiliang/wbc_move_and_open_pot      --embodiment-tag NEW_EMBODIMENT      --modality-config-path my_configs/g1_dex3_gripper_homie.py      --save-total-limit 3      --learning_rate 1e-4      --save-steps 2000      --max-steps 10000      --use-wandb      --warmup_ratio 0.05      --weight_decay 1e-5      --global-batch-size 64      --color-jitter-params brightness 0.3 contrast 0.4 saturation 0.5 hue 0.08      --dataloader-num-workers 6  --output-dir experiments/mygpu3_wbc_move_and_open_pot_bs64_s10k
```
+ Gr00t N1.7
```

     # 下载 N1.7 checkpoint

        $ pip install -U "huggingface_hub[cli]"
            (base) junweil@office-precognition:~/projects/wbc_manipulation$ hf download nvidia/GR00T-N1.6-3B --local-dir ./GR00T-N1.6-3B

    # 用precognitionlab fork
        # https://github.com/precognitionlab/Isaac-GR00T-N1.7
        # 看 Isaac-GR00T-N1.7/note_junwei.md


```
+ Gr00t whole body control (有个decouple WBC，用在 groot的底层控制器，整个repo主要是sonic)
```
    # https://github.com/NVlabs/GR00T-WholeBodyControl/blob/main/docs/source/references/decoupled_wbc.md

    # 安装，用docker
        (base) junweil@office-precognition:~/projects/wbc_manipulation$ git clone https://github.com/NVlabs/GR00T-WholeBodyControl.git

        (base) junweil@office-precognition:~/projects/wbc_manipulation/GR00T-WholeBodyControl/decoupled_wbc$ ./docker/run_docker.sh --install --root

```
+ Psi微调
```
    # 安装 (不fork，因为作者还在努力更新)
        junweil@office-precognition:~/projects/psi$ git clone git@github.com:physical-superintelligence-lab/Psi0.git

        junweil@office-precognition:~/projects/psi/Psi0$ git submodule update --init --recursive

            # third party里面有AMO， XRoboToolKit和他们的环境SIMPLE

        uv venv .venv-psi --python 3.10
        source .venv-psi/bin/activate
        GIT_LFS_SKIP_SMUDGE=1 uv sync --all-groups --index-strategy unsafe-best-match --active
        uv pip install flash_attn==2.7.4.post1 --no-build-isolation


```
