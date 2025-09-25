# Note to run TeleOperation using Quest 3 with or without controller on G1

## Quest 3对比AVP方案的优点
+ 不需要证书配置，任意电脑都可以方便做teleop服务器， 在校园网里也可以
+ 有controller，可以戴着VR开始结束遥操作，可以原地控制机器人移动
+ 可以戴眼镜佩戴
+ 便宜10倍
+ 缺点：可能手的姿态识别没那么准，显示没有AVP高清容易头晕


## 代码修改记录
+ (08/2025) 在宇树官方代码基础上，添加了controller控制5指手、3指手，可一人实现遥操作；去掉了仿真中的手腕相机，只用头部
+ Quest 3 按键说明: 右手A结束遥操作程序，右手B开始遥操作程序，左手X开始结束EP录制，板机按压下程度对应手关闭程度
+ dex3开合程度修改`xr_teleoperate/teleop/robot_control/robot_hand_unitree.py`，手关闭[图示](./g1_hand14_close.png)，手打开[图示](./g1_hand14_open.png)
+ inspire1开合程度修改`xr_teleoperate/teleop/robot_control/robot_hand_inspire.py`，手关闭[图示](./g1_inspire_close.png)，手打开[图示](./g1_inspire_open.png)
+ (08/2025) 修改图传代码，用多线程提高效率，同时显示图传服务器和接收器的延迟（通过初始100次handshake预计网络延迟和对齐时间戳）；延迟记录入数据采集中，未来可以统一时间戳，标准化数据采集
+ (08/2025) 修改Vuer代码，在VR眼睛中图像也显示图像延迟，并把图像固定地板上，保证操作者安全，passthrough可见环境
+ (08/2025) 使用VR头部pose的旋转矩阵，和世界坐标系原点pose对比，作为腰部3自由度的控制。目前只开放了yaw
+ (08/2025) 提供完整的数据replay系统，可以迅速查看数据采集质量，包括states/actions是否正确，图像是否同步，如[replay记录](https://drive.google.com/file/d/1bJEhA-KcAKJhdJigO7RFXePcQ2NJexHW/view?usp=drive_link)
+ (TODO) 添加更稳的locomotion policy，并且能下蹲，腰有两个自由度，实现整身控制遥操作(脚板朝向是否作为参考？)

## 环境安装

需要两个代码库
+ 主要代码基于宇树的修改: `https://github.com/hkustgz-hw/xr_teleoperate_hkustgz-hw`
+ EP快速可视化工具URDF等: `https://github.com/hkustgz-hw/humanoid_teleop_hkustgz-hw`

## 0. Quest 3初次配置
```
    # 第一次使用必须要Meta Horizon App，梁老师用iPad搞了个美国区Apple ID，终于可以下载这个app了

        # quest 3 按电源 + 音量变小 按键，可以恢复出厂

    # 第一次setup 需要联网更新，用梁老师的iphone 5G做wifi热点，可以连外网；更新10分钟左右，重启一次。
        # 然后要用Meta Horizon APP配置

    # Meta Quest 3 连接学校wifi HKUST(GZ)  需要选择PEAP, M**v2, 然后选择use system certificate, 域名输入nce.hkust-gz.edu.cn, identity输入用户名，匿名框留空，然后输入密码，即可。

    # Meta Quest 3 挂脖子使用
        # 初始的设置，只要摘下来，就会睡眠，那是因为有个脑门识别
        # 需要开developer mode，需要用前面的meta账号，使用ipad的horizon app，还要开duo二次验证，然后建立org,
        # 账号 junweiliang1114@gmail.com ok
            # 在horizon app上开启developer mode

        # 然后在Mac OS 安装adb，比较简单
            $ wget https://dl.google.com/android/repository/platform-tools-latest-darwin.zip

            # 解压就能用，直接连接usb-c连接quest 3

                platform-tools$ ./adb devices

                List of devices attached
                2G97C5ZH3701J1  unauthorized
                # 需要在VR里点Allow

                platform-tools$ ./adb devices
                List of devices attached
                2G97C5ZH3701J1  device

                # 关闭识别不到脑袋会休眠
                platform-tools$ ./adb shell am broadcast -a com.oculus.vrpowermanager.prox_close
                    Broadcasting: Intent { act=com.oculus.vrpowermanager.prox_close flg=0x400000 }
                    Broadcast completed: result=0

            # 这下quest 3放下台面，还会一直显示的，所以后面要一直插着电，或者用完，按一下电源键，休眠
            # 可能关机后要重新设置这个

    # [09/2025] Quest 3s与Quest 3对比，
        # Quest 3s是更新的版本，且更便宜 (4k vs. 2.5k RMB含税)。
        # 没有脑门识别，所以可以一直亮着屏幕无需开发者模式才能挂脖子；
        # 手部追踪号称是一样的，3s有红外所以光线暗的时候还会更好；外部摄像头一样的
        # 里面的镜片，比Quest 3差，必须某个角度才会不糊
        # 电池、内存容量就无所谓了

```

## 0. 用mujoco查看URDF，可以看各种joint名称与弧度限制, 以及joint的id 对应表
```
    # 3指手G1

    humanoid_teleop/assets/g1$ python ../../g1_realrobot/urdf_viewer.py g1_body29_hand14.urdf

    # 宇树g1_comp，23自由度无手

    humanoid_teleop/assets/g1$ python ../../g1_realrobot/urdf_viewer.py g1_comp.urdf

    # 宇树加因时灵巧手
        # 单手URDF里，12个自由度，4个手指每个2个所以8个，剩4个自由度在拇指
        # 实机单手只有6主动自由度，每个手指根部一个，拇指2个

    humanoid_teleop/assets/g1$ python ../../g1_realrobot/urdf_viewer.py g1_body29_inspired_hand.urdf
```

## 1. 安装遥操作环境，仿真测试环境，episode 重看环境
```
    # 安装遥操作环境叫tv
    $ git clone https://github.com/precognitionlab/xr_teleoperate_precognitionlab
    $ conda create -n tv python=3.10 pinocchio=3.1.0 numpy=1.26.4 -c conda-forge

    $ pip install opencv-python==4.10.0.84

    xr_teleoperate/teleop/televuer$ pip install -e .
    xr_teleoperate/teleop/televuer$ openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout key.pem -out cert.pem

    xr_teleoperate/teleop/robot_control/dex-retargeting$ pip install -e .

    xr_teleoperate/unitree_sdk2_python$ pip install -e .

    xr_teleoperate$ pip install -r requirements.txt

    # 安装仿真测试环境叫unitree_sim_env (直接跑实机遥操作可不需要安装这个)
    $ conda create -n unitree_sim_env python=3.10
    $ pip install torch==2.7.0 torchvision==0.22.0 --index-url https://download.pytorch.org/whl/cu128 --extra-index-url https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple

    $ pip install 'isaacsim[all,extscache]==4.5.0' --extra-index-url https://pypi.nvidia.com

    # IsaacLab还要装一下
    xr_teleoperate$ git clone https://github.com/isaac-sim/IsaacLab
    xr_teleoperate/IsaacLab$ ./isaaclab.sh --install

    xr_teleoperate/unitree_sim_isaaclab$ pip install -r requirements.txt

    xr_teleoperate/unitree_sdk2_python$ pip install -e .

    # episode 重看环境用tv环境即可
```

## 2. 实机遥操作 (因时5指)
```
    0. 安装灵巧手程序，可在G1的PC2 (jetson环境) 或者laptop6 Ubuntu环境安装，以下以laptop6为例子
        $ sudo apt update
        $ sudo apt install build-essential libeigen3-dev libyaml-cpp-dev libboost-all-dev libspdlog-dev cmake

        # 要先安装unitree SDK2 到system 目录 (ROS2)
            (tv) junweil@precognition-laptop6:~/projects/xr_teleoperate$ git clone https://github.com/unitreerobotics/unitree_sdk2

            (tv) junweil@precognition-laptop6:~/projects/xr_teleoperate/unitree_sdk2/build$ cmake ..

            (tv) junweil@precognition-laptop6:~/projects/xr_teleoperate/unitree_sdk2/build$ sudo make install

        # 还要安装ros2 和ROS2的dds组件
            # ubuntu 24.04对应 jazzy: https://docs.ros.org/en/jazzy/Installation.html

            $ sudo apt install software-properties-common
            $ sudo add-apt-repository universe
            $ sudo apt update && sudo apt install curl -y
            $ export ROS_APT_SOURCE_VERSION=$(curl -s https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest | grep -F "tag_name" | awk -F\" '{print $4}')
            $ curl -L -o /tmp/ros2-apt-source.deb "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ROS_APT_SOURCE_VERSION}/ros2-apt-source_${ROS_APT_SOURCE_VERSION}.$(. /etc/os-release && echo $VERSION_CODENAME)_all.deb" # If using Ubuntu derivates use $UBUNTU_CODENAME
            $ sudo dpkg -i /tmp/ros2-apt-source.deb
            $ sudo apt update
            $ sudo apt install ros-jazzy-desktop

            $ sudo apt install -y ros-jazzy-rmw-cyclonedds-cpp

        (tv) junweil@precognition-laptop6:~/projects/xr_teleoperate/h1_inspire_service/build$ cmake .. -DCMAKE_BUILD_TYPE=Release

        (tv) junweil@precognition-laptop6:~/projects/xr_teleoperate/h1_inspire_service/build$ make -j4

        # 以下程序应该没有报错
            (tv) junweil@precognition-laptop6:~/projects/xr_teleoperate/h1_inspire_service/build$ sudo ./inspire_hand -s /dev/ttyUSB0 --network enp131s0

        # 设置网络，假设有线连接g1, 无线连学校校园网
            $ nmcli connection show
            NAME                  UUID                                  TYPE      DEVICE
            HKUSTGZ               db9409c0-6844-4608-8331-221f0f2fffbb  wifi      wlp132s0f0
            g1_wired              41f76970-8bfd-4c1a-a059-75e169096388  ethernet  enp131s0

            $ nmcli connection show "HKUSTGZ" | grep ipv4.route-metric

            sudo nmcli connection modify HKUSTGZ ipv4.route-metric 100
            sudo nmcli connection modify g1_wired ipv4.route-metric 200

        # [08/30/2025] 此步骤，更改为在G1 PC2上运行更新的因时灵巧手controller，状态获取bug已修复(controller只能在jetson编译)
            # 先发送最新的代码去PC2
                (base) junweil@precognition-laptop6:~/projects/xr_teleoperate$ scp -r g1_inspire_service/ unitree@192.168.123.164:~/projects/
            # PC2上开screen开启controller
                # 先确保，左手线接到ttyUSB1, 右手接到ttyUSB2

                (base) unitree@ubuntu:~/projects/g1_inspire_service/build$ sudo ./inspire_g1_junwei --serial_left /dev/ttyUSB1 --serial_right /dev/ttyUSB2

                # 小测试，手应该会开合，读取状态值左右手都为0-1之间
                    (base) unitree@ubuntu:~/projects/g1_inspire_service/build$ ./hand_example
    1. 开始！
        1.0. 更新Vuer
            (tv) junweil@precognition-laptop6:~/projects/xr_teleoperate/teleop/televuer$ pip install -e .

        1.1 g1开机，进入主运控
        1.2 传更新好的image_server 代码
            (tv) junweil@precognition-laptop6:~/projects/xr_teleoperate$ scp -r teleop/image_server/ unitree@192.168.123.164:~/projects/

        1.3 开启g1 image server，更高效、回传时间戳的版本
            (base) unitree@ubuntu:~/projects/image_server$ python3.8 image_server_timesync.py

            # laptop6上测试 (会弹出cv2图像界面)
                (tv) junweil@precognition-laptop6:~/projects/xr_teleoperate/teleop/image_server$ python image_client_timesync.py

                # 测试了两分钟，从delay从3ms涨到7ms
                # fps 30

       1.4. 开启两只手的controller

            # [08/30/2025] 此步骤，更改为在G1 PC2上运行更新的因时灵巧手controller，状态获取bug已修复
            # 先发送最新的代码去PC2
                (base) junweil@precognition-laptop6:~/projects/xr_teleoperate$ scp -r g1_inspire_service/ unitree@192.168.123.164:~/projects/
            # PC2上开screen开启controller
                # 先确保，左手线接到ttyUSB1, 右手接到ttyUSB2

                (base) unitree@ubuntu:~/projects/g1_inspire_service/build$ sudo ./inspire_g1_junwei --serial_left /dev/ttyUSB1 --serial_right /dev/ttyUSB2

                # 小测试，手应该会开合，读取状态值左右手都为0-1之间
                    (base) unitree@ubuntu:~/projects/g1_inspire_service/build$ ./hand_example

        1.5. 开启遥操作！
            # 所以在这个之前，需要在PC2上开启2个screen
                # 第一个在上面开image_server
                # 第二个连着因时手，开controller

            (tv) junweil@ai-precognition-laptop6:~/projects/xr_teleoperate/teleop$ python teleop_hand_and_arm.py --xr-mode=controller  --arm=G1_29 --ee=inspire1 --record --network_interface enp131s0 --motion

                # 显示图像延迟还是可能是负的，不知道为啥
                # 100次handshake，计算出RTT是15ms左右，后面延迟就是负的
                # 计算出是10ms以内，后面延迟就是正的看起来正常

                # 想要加入腰的yaw控制加 --use_waist; 我们只使用yaw，可以不解锁宇树腰部自由度

            # 戴上VR，刷新浏览器，enter passthrough，图像应该在地板上，这时图像就是实际的图像
                # 虽然延迟可能看起来只有10几ms，在VR中至少有1秒，那是因为图像是laptop分发到wifi，wifi再给VR. 延迟算的是g1到laptop

                # 确保开始之前，VR一定要水平于地面！！passthrough时以此时pose作为世界坐标原点

                # passthrough之后，Quest 3 会生成一个安全区域，你应该不能离开这里

                # 然后可以开始挂脖子，
                # 一定要尽量把VR挂脖子挂正，VR朝向前方，要挺胸。
                # 手要放低一点，而且手要尽量往后放，不然待会G1就会一下子高举手
                # 挂脖子后，双手放到尽量靠近身体的左右两侧开始。我总是开始的时候G1手就伸长了

                # 原理就是，这里还是假设VR在头上，算的手controller到头的相对距离作为ee

                # 准备好，就可以按右手 B按键开始了，准备好左手摇杆控制机器人走动，因为手伸长可能导致机器人不平衡

                # 开始之后，laptop上也有个cv2图像，显示FPS 60左右

                # 按键左手x开始录制，然后再按结束录制，结束时terminal有提示saved **data.json

                # 下半身可以用quest 3 摇杆控制，左手前进后退左平移右平移，右手转向
                    # 注意用quest 3 的摇杆，你感觉的前进方向，可能不对；方向就是不太准，所以速度调低了


            # 发送episode到office 查看，同时显示delay

                (tv) junweil@office-precognition:~/projects/humanoid_teleop$ python g1_realrobot/visualize_arm_episodes.py ~/Downloads/episode_0014/data.json assets/g1/g1_body29_inspired_hand.urdf --fps 60 --image_path /home/junweil/Downloads/episode_0014/colors/

                --use_waist 显示腰
                --show_states 显示状态而不是actions

```

## 本次测试的视频记录
+ [挂脖子_motion_遥操作](https://drive.google.com/file/d/1hCdykq-uBqPRdp3XcUvjPylPYShVLrxO/view?usp=drive_link)
+ [replay记录](https://drive.google.com/file/d/1bJEhA-KcAKJhdJigO7RFXePcQ2NJexHW/view?usp=drive_link)
+ [挂脖子_motion_遥操作_腰部动](https://drive.google.com/file/d/1sagiD02xBwHvVYzteAUjsVSByESEEtXc/view?usp=sharing)
+ [挂脖子_motion_遥操作_腰部动replay](https://drive.google.com/file/d/1PmjV20iV4ybECJlbth3KIku8nzxnlkI_/view?usp=drive_link)
+ [挂脖子_motion_遥操作_腰部动_大幅度pitchroll_失衡](https://drive.google.com/file/d/1JF-ji25cPAFynBxKvj8rMP0JJORWr07W/view?usp=drive_link)


## 3. 实机遥操作 (宇树3指)
```
    0. 在laptop4上安装环境tv
        $ git clone https://github.com/precognitionlab/xr_teleoperate_precognitionlab
        $ conda create -n tv python=3.10 pinocchio=3.1.0 numpy=1.26.4 -c conda-forge

        $ pip install opencv-python==4.10.0.84

        xr_teleoperate/teleop/televuer$ pip install -e .
        xr_teleoperate/teleop/televuer$ openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout key.pem -out cert.pem

        xr_teleoperate/teleop/robot_control/dex-retargeting$ pip install -e .

        xr_teleoperate/unitree_sdk2_python$ pip install -e .

        xr_teleoperate$ pip install -r requirements.txt

        # 设置网络，假设有线连接g1, 无线连学校校园网?
            $ nmcli connection show
            NAME                  UUID                                  TYPE      DEVICE
            HKUSTGZ               db9409c0-6844-4608-8331-221f0f2fffbb  wifi      wlp132s0f0
            g1_wired              41f76970-8bfd-4c1a-a059-75e169096388  ethernet  enp131s0

            $ nmcli connection show "HKUSTGZ" | grep ipv4.route-metric

            sudo nmcli connection modify HKUSTGZ ipv4.route-metric 100
            sudo nmcli connection modify g1_wired ipv4.route-metric 200

    1. 开始！

        1.1 g1开机，进入主运控
        1.2 传更新好的image_server 代码
            (tv) junweil@precognition-laptop4:~/projects/xr_teleoperate$ scp -r teleop/image_server/ unitree@192.168.123.164:~/projects/

        1.3 开启g1 image server，更高效、回传时间戳的版本
            (base) unitree@ubuntu:~/projects/image_server$ python3.8 image_server_timesync.py

            # laptop4上测试 (会弹出cv2图像界面)
                (tv) junweil@precognition-laptop4:~/projects/xr_teleoperate/teleop/image_server$ python image_client_timesync.py

                # 测试了两分钟，delay从3ms涨到7ms
                # fps 30

        1.4. 开启遥操作！
            # 所以在这个之前，需要在laptop4上开启1个screen
                # 第一个连着unitree g1，在上面开image_server

            (tv) junweil@ai-precognition-laptop6:~/projects/xr_teleoperate/teleop$ python teleop_hand_and_arm.py --xr-mode=controller  --arm=G1_29 --ee=dex3 --record --network_interface enp131s0 --motion

                # 想要加入腰的yaw控制加 --use_waist; 我们只使用yaw，可以不解锁宇树腰部自由度

            # 戴上VR，刷新浏览器，enter passthrough，图像应该在地板上，这时图像就是实际的图像
                # 虽然延迟可能看起来只有10几ms，在VR中至少有1秒，那是因为图像是laptop分发到wifi，wifi再给VR. 延迟算的是g1到laptop

                # 确保开始之前，VR一定要水平于地面！！passthrough时以此时pose作为世界坐标原点

                # passthrough之后，Quest 3 会生成一个安全区域，你应该不能离开这里

                # 然后可以开始挂脖子，
                # 一定要尽量把VR挂脖子挂正，VR朝向前方，要挺胸。
                # 手要放低一点，而且手要尽量往后放，不然待会G1就会一下子高举手
                # 挂脖子后，双手放到尽量靠近身体的左右两侧开始。我总是开始的时候G1手就伸长了

                # 原理就是，这里还是假设VR在头上，算的手controller到头的相对距离作为ee

                # 准备好，就可以按右手 B按键开始了，准备好左手摇杆控制机器人走动，因为手伸长可能导致机器人不平衡

                # 开始之后，laptop上也有个cv2图像，显示FPS 60左右

                # 按键左手x开始录制，然后再按结束录制，结束时terminal有提示saved **data.json

                # 下半身可以用quest 3 摇杆控制，左手前进后退左平移右平移，右手转向
                    # 注意用quest 3 的摇杆，你感觉的前进方向，可能不对；方向就是不太准，所以速度调低了


            # 在laptop4上查看刚刚的episode

                $ git clone https://github.com/precognitionlab/humanoid_teleop_precognitionlab

                (tv) junweil@office-precognition:~/projects/humanoid_teleop$ python g1_realrobot/visualize_arm_episodes.py ~/Downloads/episode_0014/data.json assets/g1/g1_body29_inspired_hand.urdf --fps 60 --image_path /home/junweil/Downloads/episode_0014/colors/

                --use_waist 显示腰
                --show_states 显示状态而不是actions

```
4. 用仿真验证遥操作
```
    # 1. Quest 3 controller 控制5指手 inspire1
        # 1.0 开启对应的机器人的仿真
            (unitree_sim_env) xr_teleoperate/unitree_sim_isaaclab$ python sim_main.py --device cpu  --enable_cameras  --task  Isaac-PickPlace-RedBlock-G129-Inspire-Joint    --enable_inspire_dds --robot_type g129

        # 1.1 开启遥操作
            (tv) xr_teleoperate/teleop$ python teleop_hand_and_arm.py --xr-mode=controller  --arm=G1_29 --ee=inspire1 --sim --record

            # 确保Quest 3和电脑都连上了学校校园网
            # 看到 'r'提示后就可以带上头显了，拿起controller
                # 浏览器打开https://lt4.precognition.team:8012?ws=wss://lt4.precognition.team:8012
                # 或点击浏览器刷新，确保前面终端显示已连接websocket
                # 点击 pass through，开启遥操作数据传输
                # 把双手摆好，然后右手 B按键开启程序，这时候机器人应该就响应遥操作了
                # 左手x按键开启数据录制，再按x按键一次结束，按了一次可能要等一会儿才能显示save ***/data.json
                # 右手A按键结束程序，回零位，这时可以按Meta按键退出VR，再在浏览器上点一次QUIT，就可以摘了

        # 1.2 可视化刚刚录制的EP， 按s开始暂停， ,.前后10step看
            (g1) humanoid_teleop$ python g1_realrobot/visualize_arm_episodes.py episode_0014/data.json assets/g1/g1_body29_inspired_hand.urdf --fps 60

    # 2. Quest 3 controller 控制3指手 dex3
        # 2.0 开启对应机器人的仿真
            (unitree_sim_env) xr_teleoperate/unitree_sim_isaaclab$ python sim_main.py --device cpu  --enable_cameras  --task  Isaac-PickPlace-RedBlock-G129-Dex3-Joint    --enable_dex3_dds --robot_type g129

        # 2.1 开启遥操作
            (tv) xr_teleoperate/teleop$ python teleop_hand_and_arm.py --xr-mode=controller  --arm=G1_29 --ee=dex3 --sim --record

        # 2.2 可视化刚刚录制的EP， 按s开始暂停， ,.前后10step看
            (g1) humanoid_teleop$ python g1_realrobot/visualize_arm_episodes.py episode_0022/data.json assets/g1/g1_body29_hand14.urdf --hand_type dex3 --fps 60
```

