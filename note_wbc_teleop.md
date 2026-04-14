# 整身控制遥操作调研

## Overview
+ \[08/2025\] [集锦](https://mp.weixin.qq.com/s/uUmRHpFk5j0AbjP4t20VMw?scene=1)
+ AVP + Homie，效果不算太好: `https://github.com/jiachengliu3/OpenWBC`
+ AMO, by Xiaolong Wang, 使用AVP,下半身效果不好，走路时踏步。但是下蹲起身比较稳: `https://amo-humanoid.github.io/`
+ OpenWBT，银河通用，使用AVP + joystick，但是下蹲还是不会打开腿的，弯腰看起来比较稳: `https://github.com/GalaxyGeneralRobotics/OpenWBT`
+ CLONE, by Siyuan Huang北京，演示的时候都是有线网线。下半身的policy很稳，能下蹲侧走，但是步态不自然:  `https://humanoid-clone.github.io/`
+ 英伟达Gr00T也有wbc, \[11/2025\]开源。似乎支持用pico motion track控制下半身，文档感觉不够：`https://github.com/NVlabs/GR00T-WholeBodyControl`
+ pico做robotics，有这个库：`https://github.com/XR-Robotics/XRoboToolkit-PC-Service`
+ TWIST2, by Yanjie Ze, 加入了人腿的追踪，用pico 4Ultra + pico motion tracker x2 (TWIST 1 靠动补)

## TWIST2
+ project site: `https://yanjieze.com/TWIST2/#introducing`，代码：`https://github.com/amazon-far/TWIST2`
+ 12/2025, 有人复现了，还是无线控制的;延迟在100ms以内；无需双目头部相机: `https://www.bilibili.com/video/BV1UbSeBNETw/`

+ 先在office machine尝试安装复现sim2sim, 然后再用machine24
```
    1. 安装twist2环境，因为isaacgym需要python3.8

        $ conda create -n twist2 python=3.8
        $ conda activate twist2

        # isaacgym 从官网下载
        junweiliang@work_laptop:~/Downloads$ scp IsaacGym_Preview_4_Package.tar.gz junweil@office.precognition.team:~/Downloads/
        (twist2) junweil@office-precognition:~/projects/twist2$ mv ~/Downloads/isaacgym/ .
        (twist2) junweil@office-precognition:~/projects/twist2$ cd isaacgym/python && pip install -e .

        # 安装
        (twist2) junweil@office-precognition:~/projects/twist2$ git clone https://github.com/amazon-far/TWIST2

        (twist2) junweil@office-precognition:~/projects/twist2/TWIST2$ cd rsl_rl && pip install -e . && cd ..
        $ cd legged_gym && pip install -e . && cd ..
        $ cd pose && pip install -e . && cd ..
        $ pip install "numpy==1.23.0" pydelatin wandb tqdm opencv-python ipdb pyfqmr flask dill gdown hydra-core imageio[ffmpeg] mujoco mujoco-python-viewer isaacgym-stubs pytorch-kinematics rich termcolor zmq
        $ pip install redis[hiredis]
        $ pip install pyttsx3
        $ pip install onnx onnxruntime-gpu
        $ pip install customtkinter

        # redis server
        $ sudo apt update
        $ sudo apt install -y redis-server

        $ sudo systemctl enable redis-server
        $ sudo systemctl start redis-server
        $ sudo vi /etc/redis/redis.conf
            bind 0.0.0.0
            protected-mode no
        $ sudo systemctl restart redis-server

        # 动补数据和isaacgym
        junweiliang@work_laptop:~/Downloads$ scp twist_motion_dataset.zip IsaacGym_Preview_4_Package.tar.gz junweil@office.precognition.team:~/projects/twist2/

        # 底层控制器模型直接在repo里assets/

    2. 安装gmr环境，python3.10

        $ conda create -n gmr python=3.10 -y
        (gmr) junweil@office-precognition:~/projects/twist2$ git clone https://github.com/YanjieZe/GMR.git

        # install GMR
        GMR/$ pip install -e .

    3. 安装XRRobotics

        # 1. 安装QT 6.6.3, which is a GUI tools written in C++
            $ conda activate gmr
            $ pip install aqtinstall
            $ aqt install-qt linux desktop 6.6.3 gcc_64 -O ~/Qt6
            $ aqt install-tool linux desktop tools_cmake -O ~/Qt6
            $ aqt install-qt linux desktop 6.6.3 gcc_64 -m qt5compat -O ~/Qt6
            $ aqt install-qt linux desktop 6.6.3 gcc_64 -m qtvirtualkeyboard -O ~/Qt6
            $ aqt install-qt linux desktop 6.6.3 gcc_64 -m qtwebengine -O ~/Qt6

        # 2. build!

            $ git clone https://github.com/XR-Robotics/XRoboToolkit-PC-Service
            (base) junweil@office-precognition:~/projects/twist2/XRoboToolkit-PC-Service$ vi RoboticsService/qt-gcc.sh

                # Set the path to your Qt installation for GCC 64-bit architecture
                QT_GCC_64=/home/junweil/Qt6/6.6.3/gcc_64/
                export QT6_TOOLS=/home/junweil/Qt6/Tools
                export CMAKE_PREFIX_PATH=$QT_GCC_64:$CMAKE_PREFIX_PATH
                export PATH=/home/junweil/Qt6/6.6.3/gcc_64/bin:$PATH
                export PATH=/home/junweil/Qt6/6.6.3/gcc_64/include:$PATH
                export PATH=/home/junweil/Qt6/Tools/QtCreator/bin:$PATH
                export PATH=/home/junweil/Qt6/Tools/CMake/bin:$PATH

            $ bash RoboticsService/qt-gcc.sh --clean 1

            # 验证安装，在GUI界面跑
                $ export LD_LIBRARY_PATH=$HOME/Qt6/6.6.3/gcc_64/lib:$HOME/projects/twist2/XRoboToolkit-PC-Service/RoboticsService/bin:$LD_LIBRARY_PATH

                (base) junweil@office-precognition:~/projects/twist2/XRoboToolkit-PC-Service$ ./RoboticsService/bin/RoboticsServiceProcess
                release mode
                "/home/junweil/.local/share/PICOBusinessSuitData/log"  not exist!

                "/home/junweil/.local/share/PICOBusinessSuitData/log"  creat success!

                # 没有报错

    4. Build PICO PC Service SDK and Python SDK for PICO streaming

        conda activate gmr

        git clone https://github.com/YanjieZe/XRoboToolkit-PC-Service-Pybind.git
        cd XRoboToolkit-PC-Service-Pybind

        mkdir -p tmp
        cd tmp
        git clone https://github.com/XR-Robotics/XRoboToolkit-PC-Service.git
        cd XRoboToolkit-PC-Service/RoboticsService/PXREARobotSDK
        bash build.sh
        cd ../../../..

        mkdir -p lib
        mkdir -p include
        cp tmp/XRoboToolkit-PC-Service/RoboticsService/PXREARobotSDK/PXREARobotSDK.h include/
        cp -r tmp/XRoboToolkit-PC-Service/RoboticsService/PXREARobotSDK/nlohmann include/nlohmann/
        cp tmp/XRoboToolkit-PC-Service/RoboticsService/PXREARobotSDK/build/libPXREARobotSDK.so lib/
        rm -rf tmp

        # Build the project
        conda install -c conda-forge pybind11
        pip uninstall -y xrobotoolkit_sdk
        python setup.py install

    5. pico安装
        # pico不支持PEAP wifi，所以连接不了校园网，连了实验室precognition_5G

        1. MAC 下载pico sdk: XRoboToolkit-PICO-1.1.1.apk from https://github.com/XR-Robotics/XRoboToolkit-Unity-Client/releases/

            设置，关于本机，软件版本，点击多次，然后左边就会有开发者选项，然后开启usb调试模式，然后关闭永久防护

            On your Pico headset, go to Settings > General > About.


            Scroll down to Software Version and click it 7-10 times quickly until you see a message saying "You are now a developer."

            Go back to Settings, and you should now see a Developer menu.

            Enter the Developer menu and enable USB Debugging.

            # 然后usbc 连接mac, 用adb安装SDK
                # 然后在Mac OS 安装adb，比较简单
                junweiliang@work_laptop:~/Downloads$ wget https://dl.google.com/android/repository/platform-tools-latest-darwin.zip

                # 解压就能用，直接连接usb-c连接quest 3

                    junweiliang@work_laptop:~/Downloads/platform-tools$ ./adb devices

                # 安装SDK到pico上
                    junweiliang@work_laptop:~/Downloads/platform-tools$ ./adb install -g ../XRoboToolkit-PICO-1.1.1.apk
                    * daemon not running; starting now at tcp:5037
                    * daemon started successfully
                    Performing Streamed Install
                    Success

            # 在pico里，资料库，未知来源，就能看到XRobotToolkit

            # 打开该应用，可能还要升级系统，需要半小时
                # 5.14.5.U

            # 关闭自动休眠
                # 设置 -》 显示 -〉 关闭自动灭屏幕，然后需要按电源键才会唤醒

        2. 标定腿部腰部motion tracker

            # 用户名13416415647 密码 12345Ssdlh
            # 资料库 -> 体感追踪器 -> 可以有5个追踪器，脚踝+大腿+腰部
            # 根据提示校准，写入自己的身高。最后可以看具体身体可视化，可能要重新调整地面，重新校准，保证脚尖朝向可以复刻正确


```
### 测试Sim2Sim
```
    # office machine, CPU 7302, 双卡4090 48GB GPU
    (twist2) junweil@office-precognition:~/projects/twist2/TWIST2$ export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/home/junweil/anaconda3/envs/twist2/lib
    (twist2) junweil@office-precognition:~/projects/twist2/TWIST2$ bash run_motion_server.sh
        bash: /home/junweil/anaconda3/envs/twist2/lib/libtinfo.so.6: no version information available (required by bash)
        Importing module 'gym_38' (/home/junweil/projects/twist2/isaacgym/python/isaacgym/_bindings/linux-x86_64/gym_38.so)
        Setting GYM_USD_PLUG_INFO_PATH to /home/junweil/projects/twist2/isaacgym/python/isaacgym/_bindings/linux-x86_64/usd/plugInfo.json
        Robot type:  unitree_g1_with_hands
        Motion file:  /home/junweil/projects/twist2/TWIST2/assets/example_motions/0807_yanjie_walk_001.pkl
        Steps:  1
        [MotionLib] Loading motions: 100%|██████████████████████████████████████████| 1/1 [00:01<00:00,  1.79s/it]
        Total number of sub-motions: 0
        Loaded 1 motions with a total length of 13.891s.
        [Motion Server] Streaming for 694 steps at dt=0.020 seconds...
        [Motion Server] Exiting...Interpolating to default mimic_obs...


    (twist2) junweil@office-precognition:~/projects/twist2/TWIST2$ bash sim2sim.sh

        === Policy Execution FPS Results (steps 1-1000) ===
        Average Policy FPS: 62.05
        Max Policy FPS: 63.39
        Min Policy FPS: 53.29
        Std Policy FPS: 1.06
        Expected FPS (from decimation): 100.00

    # machine24 上重新安装一次
    # machine24 Ultra 7 265K CPU + 4070 TI Super 16 GB

        === Policy Execution FPS Results (steps 1-1000) ===
        Average Policy FPS: 66.23
        Max Policy FPS: 70.13
        Min Policy FPS: 56.42
        Std Policy FPS: 2.30
        Expected FPS (from decimation): 100.00

        # zeyanjie电脑才40 FPS

    # sim2sim.sh 会打开一个mujuco窗口，机器人会站着。redis server发送站立的指令，给locomotion controller。

    # 保持sim2sim.sh的程序运行，然后在另外一个terminal，可以开启motion example发送预设的动作指令
        (twist2) junweil@ai-precog-machine24:~/projects/twist2/TWIST2$ bash run_motion_server.sh
        # 这时候会有一段走路的动作序列发送过去

        # 可以开启pico 遥操作
            # 1. 开启XR service
                (base) junweil@ai-precog-machine24:~/projects/twist2/TWIST2$ export LD_LIBRARY_PATH=$HOME/Qt6/6.6.3/gcc_64/lib:$HOME/projects/twist2/XRoboToolkit-PC-Service/RoboticsService/bin:$LD_LIBRARY_PATH
                (base) junweil@ai-precog-machine24:~/projects/twist2/TWIST2$ cd ../XRoboToolkit-PC-Service
                (base) junweil@ai-precog-machine24:~/projects/twist2/XRoboToolkit-PC-Service$ ./RoboticsService/bin/RoboticsServiceProcess
                release mode

            # 2. 电脑wifi连接到precognition_5G, pico 也连到这个wifi

                电脑wifi IP地址是192.168.56.89. pico 的IP是192.168.56.*
                    电脑里跑sim2sim.sh，开启仿真服务器，然后teleop.sh (注意可能要改miniconda路径为anaconda)，开启遥操作接收

                pico中打开XRobotToolkit，输入上面的电脑 IP连接成功，然后选择full body track，5 num motion tracker，
                然后点send，就可以在电脑上看到pico retargeted后的G1。然后右手手柄点开始，就可以发送到sim服务器

                感觉下半身很不稳，单腿站立不可能: https://github.com/amazon-far/TWIST2/issues/23

```
### 代码解读
```
    1. XRoboToolkit: https://xr-robotics.github.io/
        在VR的OpenXR 标准上建立的，
        XR Client在pico上跑的app，发送人体数据90Hz as JSON object 到 XRoboToolkit-PC-Service
        XRoboToolkit-PC-Service 再发送控制给 Robot Controller
```
### 测试Sim2Real
```
```
