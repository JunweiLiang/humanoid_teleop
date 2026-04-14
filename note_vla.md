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

        (tv) junweil@office-precognition:~/projects/huawei_data$ python ~/projects/humanoid_teleop/g1_realrobot/convert_unitree_json_to_lerobot.py --raw-dir wbc_task5_lerobotv2/ --repo-id junweiliang/wbc_5tasks --robot_type Unitree_G1_Dex3



```
