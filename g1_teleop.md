# note on getting teleop G1 to work

### 附加仓库
1. sdk 修改了走跑运控，来自: `https://github.com/JunweiLiang/unitree_sdk2_python`
2. avp_teleop 来自凯伦修改: `https://github.com/JunweiLiang/avp_teleoperate`
```
    https://github.com/Lab317-Kelun/avp_teleoperate/blob/master/README_zh-CN.md
我把代码上传了 Readme里的坑我重点说明了一下 由于遥操需要本地电脑生成证书 在传到AVP 所以用新的电脑都需要重新配置一下 大致跟着步骤走一遍就好了
~/avp_teleoperate/teleop/robot_control 路径下的 robot_arm.py 是对接homie的
robot_arm_no_homie.py是可以直接控制双臂的 当前默认是对接homie的 稍微注意下这里就可以区分开

Step2 运行下面两条命令来显式使能 UDP 多播和添加路由表
sudo ifconfig eno2 multicast
sudo route add -net 224.0.0.0 netmask 240.0.0.0 dev eno2
这里是LCM每次开机前都要配置 文昊这里都了解的
```
3. 控制G1手，视觉识别电梯按钮，按按钮，IK解算, 末端用arm_sdk控制到达指定位姿, [这里](./g1_realrobot/note_test.md)

### 遥操作
```
    # 系统连接：G1-PC2连接路由器，电脑、AR装置 wifi 连接该路由器
    # https://github.com/unitreerobotics/xr_teleoperate/blob/main/README_zh-CN.md

    1. 在office机器测试，quest 3, 仿真中操作g1

        # 安装遥操作环境
            (base) junweil@office-precognition:~/projects$ git clone https://github.com/unitreerobotics/xr_teleoperate

            (base) junweil@office-precognition:~/projects$ conda create -n tv python=3.10 pinocchio=3.1.0 numpy=1.26.4 -c conda-forge

            (tv) junweil@office-precognition:~/projects/xr_teleoperate$ git submodule update --init --depth 1

            (tv) junweil@office-precognition:~/projects/xr_teleoperate$ cd teleop/televuer
            (tv) junweil@office-precognition:~/projects/xr_teleoperate/teleop/televuer$ pip install -e .
            (tv) junweil@office-precognition:~/projects/xr_teleoperate/teleop/televuer$ openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout key.pem -out cert.pem

            $ cd ../robot_control/dex-retargeting/
            $ pip install -e .

            (tv) junweil@office-precognition:~/projects/xr_teleoperate/teleop/robot_control/dex-retargeting$ cd ../../../
            (tv) junweil@office-precognition:~/projects/xr_teleoperate$ pip install -r requirements.txt

            (tv) junweil@office-precognition:~/projects/xr_teleoperate$ git clone https://github.com/unitreerobotics/unitree_sdk2_python.git
            (tv) junweil@office-precognition:~/projects/xr_teleoperate$ cd unitree_sdk2_python/
            (tv) junweil@office-precognition:~/projects/xr_teleoperate/unitree_sdk2_python$ pip install -e .

        # 安装仿真测试环境

            $ conda create -n unitree_sim_env python=3.10
            $ conda activate unitree_sim_env

            $ pip install torch==2.7.0 torchvision==0.22.0 --index-url https://download.pytorch.org/whl/cu128 --extra-index-url https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple

            $ pip install 'isaacsim[all,extscache]==4.5.0' --extra-index-url https://pypi.nvidia.com

                # 确保跑一次isaacsim，[20.856s] Isaac Sim Full App is loaded.
                # 第一次要载入很多东西，像卡死一样

                # 一次性下载完Isaac Sim 的Assets放本地
                    # 根据： https://docs.isaacsim.omniverse.nvidia.com/4.5.0/installation/install_faq.html#isaac-sim-setup-assets-content-pack
                        # 或者这个：https://github.com/unitreerobotics/unitree_sim_isaaclab/issues/5#issuecomment-3076448242

                    # 从这里直接wget 3个包裹

                        $ wget https://download.isaacsim.omniverse.nvidia.com/isaac-sim-assets-1%404.5.0-rc.36%2Brelease.19112.f59b3005.zip
                        $ wget https://download.isaacsim.omniverse.nvidia.com/isaac-sim-assets-2%404.5.0-rc.36%2Brelease.19112.f59b3005.zip
                        $ wget https://download.isaacsim.omniverse.nvidia.com/isaac-sim-assets-3%404.5.0-rc.36%2Brelease.19112.f59b3005.zip

                    # 解压
                        (base) junweil@office-precognition:~/Downloads$ mkdir ~/isaacsim_assets
                        (base) junweil@office-precognition:~/Downloads$ unzip "isaac-sim-assets-1@4.5.0-rc.36+release.19112.f59b3005.zip" -d ~/isaacsim_assets
                        2、3一样

                    # 修改
                        $ vi /home/junweil/anaconda3/envs/unitree_sim_env/lib/python3.10/site-packages/isaacsim/apps/isaacsim.exp.base.kit
[settings]
...
persistent.isaac.asset_root.default = "/home/junweil/isaacsim_assets/Assets/Isaac/4.5/"
exts."isaacsim.asset.browser".folders = [
    "/home/junweil/isaacsim_assets/Assets/Isaac/4.5/Isaac/Robots",
    "/home/junweil/isaacsim_assets/Assets/Isaac/4.5/Isaac/People",
    "/home/junweil/isaacsim_assets/Assets/Isaac/4.5/Isaac/IsaacLab",
    "/home/junweil/isaacsim_assets/Assets/Isaac/4.5/Isaac/Props",
    "/home/junweil/isaacsim_assets/Assets/Isaac/4.5/Isaac/Environments",
    "/home/junweil/isaacsim_assets/Assets/Isaac/4.5/Isaac/Materials",
    "/home/junweil/isaacsim_assets/Assets/Isaac/4.5/Isaac/Samples",
    "/home/junweil/isaacsim_assets/Assets/Isaac/4.5/Isaac/Sensors",
]
                    # 修改
                        $ vi /home/junweil/anaconda3/envs/unitree_sim_env/lib/python3.10/site-packages/omni/data/Kit/Isaac-Sim/4.5/user.config.json


                            原本："http://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/4.5"

                            "persistent": {
                            "isaac": {
                                "asset_root": {
                                    "default": "/home/junweil/isaacsim_assets/Assets/Isaac/4.5",
                                    "cloud": "/home/junweil/isaacsim_assets/Assets/Isaac/4.5",
                                    "nvidia": "/home/junweil/isaacsim_assets/Assets/Isaac/4.5",
                                    "timeout": 5.0
                                }
                            },

                        # 下载的asset不完整, 还需要自己下载一份东西
                            (base) junweil@office-precognition:~/isaacsim_assets/Assets/Isaac/4.5/Isaac/Props$ cd PackingTable/
                            (base) junweil@office-precognition:~/isaacsim_assets/Assets/Isaac/4.5/Isaac/Props/PackingTable$ wget https://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/4.5/Isaac/Props/PackingTable/packing_table.usd



            (unitree_sim_env) junweil@office-precognition:~/projects/xr_teleoperate$ git clone https://github.com/isaac-sim/IsaacLab

            sudo apt install cmake build-essential

            (unitree_sim_env) junweil@office-precognition:~/projects/xr_teleoperate/IsaacLab$ ./isaaclab.sh --install

            (unitree_sim_env) junweil@office-precognition:~/projects/xr_teleoperate$ git clone https://github.com/unitreerobotics/unitree_sim_isaaclab

            (unitree_sim_env) junweil@office-precognition:~/projects/xr_teleoperate/unitree_sim_isaaclab$ pip install -r requirements.txt

            (unitree_sim_env) junweil@office-precognition:~/projects/xr_teleoperate/unitree_sdk2_python$ pip install -e .

            # 开启仿真环境

                (unitree_sim_env) junweil@office-precognition:~/projects/xr_teleoperate/unitree_sim_isaaclab$ CUDA_VISIBLE_DEVICES=1 python sim_main.py --device cpu  --enable_cameras  --task  Isaac-PickPlace-Cylinder-G129-Dex3-Joint --enable_dex3_dds --robot_type g129

                仿真环境启动后，使用鼠标左键在窗口内点击一次以激活仿真运行状态。此时，终端内输出 controller started, start main loop...。

                    # 测GPU显存速度

                        (base) junweil@office-precognition:~/Downloads$ wget https://github.com/GpuZelenograd/memtest_vulkan/releases/download/v0.5.0/memtest_vulkan-v0.5.0_DesktopLinux_X86_64.tar.xz

                        (base) junweil@office-precognition:~/Downloads$ mkdir memtest
                        (base) junweil@office-precognition:~/Downloads$ tar -xf memtest_vulkan-v0.5.0_DesktopLinux_X86_64.tar.xz -C memtest/
                        (base) junweil@office-precognition:~/Downloads$ cd memtest/
                        (base) junweil@office-precognition:~/Downloads/memtest$ ./memtest_vulkan
                        # 4090 48 GB
                            3598 iteration. Passed 30.0220 seconds  written:12127.5GB 840.3GB/sec        checked:13230.0GB 848.7GB/sec
                        # 3090
                            5067 iteration. Passed 30.0538 seconds  written:10275.0GB 737.8GB/sec        checked:12330.0GB 764.6GB/sec
                        # 4090 16GB laptop
                            4171 iteration. Passed 30.0168 seconds  written: 4948.1GB 384.5GB/sec        checked: 6597.5GB 384.7GB/sec
                        # 5090 24GB laptop
                            2659 iteration. Passed 30.0963 seconds  written: 5343.8GB 400.4GB/sec        checked: 6412.5GB 382.8GB/sec


                # 宇树的人说，正常应该占用显存单卡10GB以上，4090显卡24核心32GB RAM（555/cuda12.5），可以达到average 15Hz, average loop time 64 ms
                    # https://github.com/unitreerobotics/unitree_sim_isaaclab/issues/13
                    # 32核心256GB RAM 4090 48GBx2，office, 2.3Hz, average loop time 438 ms [占用4.5GB显存, 575/cuda12.9]
                        # 单卡跑有这些提示，双卡没有
                        2025-07-24 14:03:12 [2,008ms] [Warning] [gpu.foundation.plugin] Skipping NVIDIA GPU due CUDA being in bad state: NVIDIA GeForce RTX 4090
                        2025-07-24 14:03:12 [2,008ms] [Warning] [gpu.foundation.plugin] Please restart your system if CUDA is known to work in your system.
                        2025-07-24 14:03:12 [2,012ms] [Warning] [gpu.foundation.plugin] Skipping NVIDIA GPU due CUDA being in bad state: NVIDIA GeForce RTX 4090
                        2025-07-24 14:03:12 [2,012ms] [Warning] [gpu.foundation.plugin] Please restart your system if CUDA is known to work in your system.

                        # 按宇树的人说，把pickplace_cylinder_g1_29dof_dex3_joint_env_cfg.py
                            # 注释掉3个ObsTerm，速度就涨回来到20Hz了

                    # 12核心48GB RAM 3090，m12, 8.7Hz, average loop time 114 ms [占用4GB显存, 575/cuda12.9]

                    # laptop5, 5090笔记本 24核心64GB RAM, 570/cuda12.8
                        (base) junweil@lt5:~/projects$ git clone https://github.com/unitreerobotics/xr_teleoperate

                        $ conda create -n unitree_sim_env python=3.10
                        $ conda activate unitree_sim_env

                        $ pip install torch==2.7.0 torchvision==0.22.0 --index-url https://download.pytorch.org/whl/cu128 --extra-index-url https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple

                        $ pip install 'isaacsim[all,extscache]==4.5.0' --extra-index-url https://pypi.nvidia.com

                        (unitree_sim_env) junweil@lt5:~/projects/xr_teleoperate$ git clone https://github.com/isaac-sim/IsaacLab

                        (unitree_sim_env) junweil@lt5:~/projects/xr_teleoperate/IsaacLab$ ./isaaclab.sh --install

                        (unitree_sim_env) junweil@lt5:~/projects/xr_teleoperate$ git clone https://github.com/unitreerobotics/unitree_sim_isaaclab

                        (unitree_sim_env) junweil@lt5:~/projects/xr_teleoperate/unitree_sim_isaaclab$ pip install -r requirements.txt

                        (unitree_sim_env) junweil@lt5:~/projects/xr_teleoperate$ git clone https://github.com/unitreerobotics/unitree_sdk2_python.git

                        (unitree_sim_env) junweil@lt5:~/projects/xr_teleoperate/unitree_sdk2_python$ pip install -e .

                        # 测试
                            (unitree_sim_env) junweil@lt5:~/projects/xr_teleoperate/unitree_sim_isaaclab$ python sim_main.py --device cpu  --enable_cameras  --task  Isaac-PickPlace-Cylinder-G129-Dex3-Joint --enable_dex3_dds --robot_type g129

                        # overall 16Hz, average loop time 61 ms [占用4.6GB显存, 570/cuda12.8]
                        # render有雪花，应该要Isaac Sim 5.0才行

                    # laptop4, 4090笔记本, 550/cuda12.4, 32核心32GB RAM
                        # overall 17Hz, average loop time 57 ms [占用5GB显存, 550/cuda12.4]

                # 把代码整理到自己repo

                    # https://github.com/JunweiLiang/xr_teleoperate
                        # IsaacLab还是用官方的git clone吧

                    junweil@office-precognition:~/projects/test2/xr_teleoperate
                        # 按宇树的人说，把pickplace_cylinder_g1_29dof_dex3_joint_env_cfg.py
                            # 注释掉3个ObsTerm，速度就涨回来到20Hz了

                    # 尝试再安装Isaac Sim 5.0
                        # 07/2025 不行，5.0版本还没正式发布，pip 安装不了


                # [07/26/2025] 结论，office的4090不知道什么问题。真正测试还是用laptop4 4090笔记本吧
                    # laptop4安装遥操作环境

                        (base) junweil@precognition-laptop4:~/projects$ git clone https://github.com/JunweiLiang/xr_teleoperate

                        (base) junweil@precognition-laptop4:~/projects/xr_teleoperate$ conda create -n tv python=3.10 pinocchio=3.1.0 numpy=1.26.4 -c conda-forge

                        (tv) junweil@precognition-laptop4:~/projects/xr_teleoperate/teleop/televuer$ pip install -e .

                        (tv) junweil@precognition-laptop4:~/projects/xr_teleoperate/teleop/televuer$ openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout key.pem -out cert.pem

                        $ cd ../robot_control/dex-retargeting/
                        $ pip install -e .

                        (tv) junweil@precognition-laptop4:~/projects/xr_teleoperate$ pip install -r requirements.txt

                        (tv) junweil@precognition-laptop4:~/projects/xr_teleoperate/unitree_sdk2_python$ pip install -e .

                    # 仿真环境换了我们的库后，还要再重新安装, 删除unitree_sim_env，按照上面安装步骤重来
                        # IsaacLab还是要重新git clone官方的




        # 测试仿真中的遥操作！quest 3 可以戴着眼镜佩戴
            # 第一次使用必须要Meta Horizon App，梁老师用iPad搞了个美国区Apple ID，终于可以下载这个app了
                # Meta 账号junweiliang1114@gmail.com dabaicai1114
            # quest 3 按电源+ 音量变小 按键，可以恢复出厂
            # 第一次setup 需要联网更新，用我的iphone 5G做wifi热点，可以连外网；更新10分钟左右，重启一次。
                # 然后要用Meta Horizon APP配置
            # Quest 3 连接 iphone热点成功，无线路由也ok，但是学校网络就是不行，用Horizon APP连也不行


        # 开始！
            # office 台式机，连接Dabaicai_4g wifi (本机器192.168.0.227)， 然后开启仿真
                # 连上wifi后，原本校园网可能就连不上网了，需要加设置流量优先级

                    (base) junweil@office-precognition:~$ sudo nmcli connection modify "Wired connection 1" ipv4.route-metric 10 ipv6.route-metric 10
                    (base) junweil@office-precognition:~$ sudo nmcli connection modify "Dabaicai_4g" ipv4.route-metric 100 ipv6.route-metric 100

                    (base) junweil@office-precognition:~$ nmcli -p connection show "Dabaicai_4g" | grep ipv4.route-metric
                    ipv4.route-metric:                      100

            # 开启遥操服务器

                (tv) junweil@office-precognition:~/projects/xr_teleoperate/teleop$ python teleop_hand_and_arm.py --xr-mode=controller  --arm=G1_29 --ee=dex3 --sim --record --motion

                # quest 3容易死机，有异常就重启quest 3
                # quest 3 打开浏览器
                    https://192.168.0.227:8012?ws=wss://192.168.0.227:8012
                    # 打开之后，终端会显示
                        websocket is connected. id:03003b2f-0cb0-4bee-9211-4eb45f0cfe55
                        default socket worker is up, adding clientEvents
                        Uplink task running. id:03003b2f-0cb0-4bee-9211-4eb45f0cfe55

                    # 终端按r，就开始遥操作


            # 使用laptop4测试
                # laptop4 有线连接校园网，无线连接 Dabaicai_4g wifi (192.168.0.219)
                    # 设置网络priority，全部默认走有线网络
                        $ nmcli connection show
                            NAME                         UUID                                  TYPE      DEVICE
                            Wired campus                 578c5d1c-32e2-3139-97cf-d2dd7ca5988a  ethernet  enp58s0
                            Dabaicai_4g                  e2c84659-1ece-422e-8f92-7ea825fd7679  wifi      wlp59s0f0

                        (base) junweil@precognition-laptop4:~$ sudo nmcli connection modify "Wired campus" ipv4.route-metric 10 ipv6.route-metric 10

                        (base) junweil@precognition-laptop4:~$ sudo nmcli connection modify "Dabaicai_4g" ipv4.route-metric 100 ipv6.route-metric 100


                # 1. 开仿真 # 跑仿真loop (4090 笔记本， 60ms loop time, 17Hz)

                    (unitree_sim_env) junweil@precognition-laptop4:~/projects/xr_teleoperate/unitree_sim_isaaclab$ python sim_main.py --device cpu  --enable_cameras  --task  Isaac-PickPlace-Cylinder-G129-Dex3-Joint --enable_dex3_dds --robot_type g129

                # 2. 开启遥操作服务
                    (tv) junweil@precognition-laptop4:~/projects/xr_teleoperate/teleop$ python teleop_hand_and_arm.py --xr-mode=controller  --arm=G1_29 --ee=dex3 --sim --record

                    # 先不要加 --motion
                    # 原本的代码，dex3不能用controller，必须用手识别，把人的三指 map到宇树3指
                        # 需要写一个把dex3当作gripper, gripper value和controller的对应关系，可以参考dex1


                # 3. Quest 3 连接

                    # quest 3容易死机，有异常就重启quest 3
                    # quest 3 打开浏览器
                        https://192.168.0.219:8012?ws=wss://192.168.0.219:8012
                        # 打开之后，终端会显示
                            websocket is connected. id:03003b2f-0cb0-4bee-9211-4eb45f0cfe55
                            default socket worker is up, adding clientEvents
                            Uplink task running. id:03003b2f-0cb0-4bee-9211-4eb45f0cfe55
                        # 点击Virtual Reality，进入全屏
                        # 把手臂摆在g1零位位置，（最好让别人帮忙按）终端按r，就开始遥操作
                        # 如果手臂没响应，按遥控器的meta按键，退出全屏，再按Virtual Reality，可以遥控手臂
                        # 按遥控器的meta按键，退出，可能quest 3 就会卡住，等一下，或者直接电源键关机

                    # 尝试夹爪，移动g1

                        --xr-mode=hand --ee=dex3 可以用手控制机器人手指动, controller还不行
                        --motion 会报错 send request error，还没用起来

            # 仿真中 录制手势动作，然后replay，mechat中？
            # 实机中replay一下看看

            # 实机中跑遥操作, 改controller控制？
```

### Motion Retargetting

0. 代码方法、预处理数据列表
```
    # 方法
        大部份都基于PHC:
        H2O也是基于PHC:
        HOVER 基于H2O:
    # 别人retarget 好的数据集 data

        # 安装数据集下载工具，下载huggingface
            $ sudo apt install git-lfs
            (retarget) junweil@office-precognition:/mnt/ssd2/junweil/embodied_ai$ git lfs install
            Git LFS initialized.

            # 这样git clone huggingface才不会下载一堆空文件（4.0k 大小）

        # 文档来自
            https://github.com/JunweiLiang/humanoid_amp

                (retarget) junweil@office-precognition:/mnt/ssd2/junweil/embodied_ai/humanoid_amp/motions$ python motion_viewer.py --file G1_walk.npz --render-scene

                    # 可以可视化每个关节的运动情况

        # LAFAN1
            https://huggingface.co/datasets/lvhaidong/LAFAN1_Retargeting_Dataset

                (base) junweil@office-precognition:/mnt/ssd2/junweil/embodied_ai$ git clone https://huggingface.co/datasets/lvhaidong/LAFAN1_Retargeting_Dataset

            # 数据集stats，宇树官方弄的，retargetting考虑了防止foot slippage
                5个subject, 40个csv sequence, 30 fps, 29 DOF + 1 ? (xyzQxQyQzQw)

                # 原始数据有77个sequence: https://github.com/ubisoft/ubisoft-laforge-animation-dataset

            # 可视化
                $ conda create -n retarget python=3.10
                $ conda install pinocchio -c conda-forge
                $ pip install numpy rerun-sdk==0.22.0 trimesh

                # 在rerun 窗口播放查尔斯舞蹈

                    (retarget) junweil@office-precognition:/mnt/ssd2/junweil/embodied_ai/LAFAN1_Retargeting_Dataset$ python rerun_visualize.py --file_name dance1_subject2 --robot_type g1

        # AMASS
            https://huggingface.co/datasets/ember-lab-berkeley/AMASS_Retargeted_for_G1

                (base) junweil@office-precognition:/mnt/ssd2/junweil/embodied_ai$ git clone https://huggingface.co/datasets/ember-lab-berkeley/AMASS_Retargeted_for_G1

                # 可视化
                    # 需要mujuco下的g1 xml

                        (retarget) junweil@office-precognition:/mnt/ssd2/junweil/embodied_ai$ git clone https://github.com/unitreerobotics/unitree_mujoco

                    $ pip install mujuco tqdm plotly matplotlib
                    $ pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128

                    # 可视化跳远动作，开启mujoco窗口
                        (retarget) junweil@office-precognition:/mnt/ssd2/junweil/embodied_ai/AMASS_Retargeted_for_G1/scripts$ python mujoco_player.py --file-type auto --model ../../unitree_mujoco/unitree_robots/g1/g1_29dof.xml ../g1/CMU/01/01_01_poses_120_jpos.npz
                            Loaded Stage2 file with 688 frames at 30.0 fps
                            Playing frames 0-688 (22.93s)
                            Playback: ██████████⚫███████████████████████████████████████ 5.0s/22.9ss



                # 以上数据集包含 下面数据集
                https://huggingface.co/datasets/fleaven/Retargeted_AMASS_for_robotics

                # 下载
                    # 如果下载不了再试试这个： export HF_ENDPOINT=https://hf-mirror.com
                    $ pip install huggingface_hub[hf_transfer]
                    $ huggingface-cli download fleaven/Retargeted_AMASS_for_robotics --repo-type dataset --local-dir ./Retargeted_AMASS_for_robotics_data

                    # huggingface-cli 下载多个小文件会出错
                    # 用git下, 注意要设置好git lfs

                    (base) junweil@office-precognition:/mnt/ssd2/junweil/embodied_ai$ git clone https://huggingface.co/datasets/fleaven/Retargeted_AMASS_for_robotics


```

1. Download and visualize AMASS
```
    # 参考
        https://github.com/NVlabs/HOVER/?tab=readme-ov-file#data-processing
        https://github.com/LeCAR-Lab/human2humanoid?tab=readme-ov-file#amass-dataset-preparation
        https://github.com/ZhengyiLuo/PHC/blob/master/docs/retargeting.md
            # 备份: https://github.com/JunweiLiang/PHC/blob/master/docs/retargeting.md

    # 要开浏览器一个个AMASS子集合下载
        https://amass.is.tue.mpg.de/download.php

        # 下载全部 SMPL + H G的.tar.vz2包
        # 还下载了一个瑜伽的.zip数据集，cvpr 2023

        # on home-lab
        junweiliang@work_laptop:~/Downloads$ scp -r amass/ junweil@10.13.3.209:/mnt/nvme1/junweil/embodied_ai

        # on machine10
        (base) junweil@home-lab:/mnt/nvme1/junweil/embodied_ai$ scp -r amass/ junweil@m10.precognition.team:/mnt/ssd1/junweil

    # motion data (*.tar.bz2) in office machine
        (base) junweil@office-precognition:/mnt/ssd1/junweil/embodied_ai/amass$

        # 解压缩
        for file in *.tar.bz2; do
            tar -xvjf "$file"
        done

    # SMPL data
        (base) junweil@office-precognition:/mnt/ssd1/junweil/embodied_ai$ unzip SMPL_python_v.1.1.0.zip

```

2. Retarget AMASS for G1
```
```

3. Train my own motion tracker for G1
```
```
