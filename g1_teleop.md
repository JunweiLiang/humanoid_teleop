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

                        # 查明原因了，是CPU太弱了，把 CPU设置到更高频率，hz提升了
                            # office 提升到 10.7 Hz, average loop time 94ms
                                # 去bios里把cpu超线程关了(SMT)，htop看32核心变成16核心，好像快一丢丢，变成91ms, 11 Hz

                            $ sudo apt install cpufrequtils
                            (base) junweil@office-precognition:~$ cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_available_governors
                                conservative ondemand userspace powersave performance schedutil

                            $ cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
                            # 原本是ondemand，改成performance
                                 echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

                            # 对laptop4好像没用

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

            # [07/29/2025] Meta Quest 3 连接学校wifi HKUST(GZ)  需要选择PEAP, M**v2, 然后选择use system certificate, 域名输入nce.hkust-gz.edu.cn, identity输入用户名，匿名框留空，然后输入密码，即可。学校徐智宏教的

        # 开始！
            # office 台式机，连接Dabaicai_4g wifi (本机器192.168.0.227)， 然后开启仿真
                # 连上wifi后，原本校园网可能就连不上网了，需要加设置流量优先级

                    (base) junweil@office-precognition:~$ sudo nmcli connection modify "Wired connection 1" ipv4.route-metric 10 ipv6.route-metric 10
                    (base) junweil@office-precognition:~$ sudo nmcli connection modify "Dabaicai_4g" ipv4.route-metric 100 ipv6.route-metric 100

                    (base) junweil@office-precognition:~$ nmcli -p connection show "Dabaicai_4g" | grep ipv4.route-metric
                    ipv4.route-metric:                      100

            # 开启遥操服务器

                (tv) junweil@office-precognition:~/projects/test2/xr_teleoperate/teleop$ python teleop_hand_and_arm.py --xr-mode=controller  --arm=G1_29 --ee=dex3 --sim --record --motion

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

                # 尝试因时灵巧手, 录制手势

                    # 开启因时手仿真
                        (unitree_sim_env) junweil@precognition-laptop4:~/projects/xr_teleoperate/unitree_sim_isaaclab$ python sim_main.py --device cpu  --enable_cameras  --task  Isaac-PickPlace-RedBlock-G129-Inspire-Joint    --enable_inspire_dds --robot_type g129

                    # 开启遥操作
                        (tv) junweil@precognition-laptop4:~/projects/xr_teleoperate/teleop$ python teleop_hand_and_arm.py --xr-mode=hand --arm=G1_29 --ee=inspire1 --sim --record

                    # quest 3 戴起来，连接对应wifi，打开浏览器到https://192.168.0.219:8012?ws=wss://192.168.0.219:8012
                        # 放下控制器，用手势识别。先终端按r，机器人手应该就会飘起来
                        # 点击VR或者Pass through
                        # 终端按s开始录制手势，s再结束
                        # 尝试了两次，得到json data:
                            (tv) junweil@precognition-laptop4:~/projects/xr_teleoperate/teleop$ ls ./utils/data/
                                episode_0001  episode_0002
                            # 几秒时间就150MB数据，包含RGB和depth. 我们手势只需要data.json (只有RGB数据，60 fps的jpg三个角度的都存下来)
                                junweiliang@work_laptop:~/Downloads$ scp junweil@lt4.precognition.team:/home/junweil/projects/xr_teleoperate/teleop/utils/data/episode_0001/data.json g1_welcome_data.json

                                junweiliang@work_laptop:~/Downloads$ scp junweil@lt4.precognition.team:/home/junweil/projects/xr_teleoperate/teleop/utils/data/episode_0002/data.json g1_geishou_data.json

                            # json格式
                                a["info"]
                                len(a["data"]) -> 952 个数据，60 fps
                                    dict_keys(['idx', 'colors', 'depths', 'states', 'actions', 'tactiles', 'audios', 'sim_state'])
                                    "idx": 0 -> 951
                                    "colors" -> 3个jpg文件名 'colors/000001_color_0.jpg'

                                    a["data"][1]["states"]是当前时间下机器人的状态，actions是sol_q解出来的这时候发送的命令 (给定当下机器人状态，获取遥操作手ee位姿，ik解算)
                                    >>> a["data"][1]["actions"].keys()
                                        dict_keys(['left_arm', 'right_arm', 'left_ee', 'right_ee', 'body']
                                        # 7自由度手臂
                                        >>> a["data"][1]["actions"]["left_arm"]["qpos"]
                                        [-0.8431334523569074, 0.3125219682813758, -0.3504520738550948, 1.1770103578690738, 0.7314618342210563, -0.25334802959393105, 1.2331182185156233]
                                            # 获取qpos各个数字，和URDF joint名字的对应关系
                                            # 这里得到的qpos顺序，就是直接solve_ik的sol_q，from robot_control/robot_arm_id.py
                                                14个顺序：
                                                    Joints in Reduced Robot:
                                                    Joint ID 0: universe
                                                    Joint ID 1: left_shoulder_pitch_joint
                                                    Joint ID 2: left_shoulder_roll_joint
                                                    Joint ID 3: left_shoulder_yaw_joint
                                                    Joint ID 4: left_elbow_joint
                                                    Joint ID 5: left_wrist_roll_joint
                                                    Joint ID 6: left_wrist_pitch_joint
                                                    Joint ID 7: left_wrist_yaw_joint
                                                    Joint ID 8: right_shoulder_pitch_joint
                                                    Joint ID 9: right_shoulder_roll_joint
                                                    Joint ID 10: right_shoulder_yaw_joint
                                                    Joint ID 11: right_elbow_joint
                                                    Joint ID 12: right_wrist_roll_joint
                                                    Joint ID 13: right_wrist_pitch_joint
                                                    Joint ID 14: right_wrist_yaw_joint
                                                    reduced_robot.model.nq:14
                                                可以通过注释visualize_arm_episodes.py查看
                                                    (g1) junweil@office-precognition:~/projects/humanoid_teleop$ python g1_realrobot/visualize_arm_episodes.py ~/Downloads/g1_geishou_data.json assets/g1/g1_body29_hand14.urdf --fps 60

                                        # 因时的手是6自由度
                                        >>> a["data"][1]["actions"]["left_ee"]["qpos"]
                                        [0.9392543494333019, 0.9665400978589515, 0.9799967298529748, 0.8853130570344678, 0.5909996522300536, 0.7740214705733652]
                                        # 但其实URDF中因时手是12自由度，
                                            # xr_teleoperate/assets/inspire_hand/inspire_hand.yml
                                            # 有写宇树如何retarget
                                                robot_hand_inspire.py -> hand_retargeting.py
                                                self.left_inspire_api_joint_names  = [
                                                    'L_pinky_proximal_joint',
                                                    'L_ring_proximal_joint',
                                                    'L_middle_proximal_joint',
                                                    'L_index_proximal_joint',
                                                    'L_thumb_proximal_pitch_joint',
                                                    'L_thumb_proximal_yaw_joint' ]

                                    # 数据没有timestamp的，data frequency在teleop_hand_and_arm.py中设定默认60 fps，这应该是最大值

                            # 遥操作代码解读
                                手部获取这两个信息:
                                    left_hand_pos_array, 75 -> 25x3
                                    OpenXR标准，代码在 teleop/televuer/src/televuer/tv_wrapper.py
                                    进行了坐标转换，从WORLD to HEAD，to WAIST，也就是G1自己的原点
                                    # OpenXR的手的25个id, 包括wrist，用于计算ee IK
                                        # https://registry.khronos.org/OpenXR/specs/1.1/man/html/openxr.html
                                        # 25个点参考这个图: https://docs.unity.cn/Packages/com.unity.xr.hands@1.2/manual/hand-data/xr-hand-data-model.html

                                手部信息在循环中存储到 left_hand_pos_array
                                然后 Inspire_Controller 以最高100 Hz，获取hand_pos_array，
                                    然后retarget到机器手的这个，因时就是12维度， 6x2
                                        dual_hand_state_array, dual_hand_action_array

                                    # teleop/robot_control/robot_hand_inspire.py
                                        # --> retarget 代码在teleop/robot_control/hand_retargeting.py
                                        # 用的是DexPilot 算法：teleop/robot_control/dex-retargeting/src/dex_retargeting/retargeting_config.py -> build(), 用urdf算
                                            # https://github.com/dexsuite/dex-retargeting
                                            # 根据这个config，定义了人手的相对大小: assets/inspire_hand/inspire_hand.xml

                                        # build()的时候只是初始化optimizer，在robot_hand_inspire.py的100Hz loop中跑retarget() function的时候返回robot_qpos
                                            # 自由度的顺序，根据 robot_hand_inspire.py -> hand_retargeting.py 的self.left_inspire_api_joint_names
                                                self.left_inspire_api_joint_names  = [
                                                    'L_pinky_proximal_joint',
                                                    'L_ring_proximal_joint',
                                                    'L_middle_proximal_joint',
                                                    'L_index_proximal_joint',
                                                    'L_thumb_proximal_pitch_joint',
                                                    'L_thumb_proximal_yaw_joint' ]

                # replay!!

                    # 基础知识
                        # 左右手各7自由度，电机角度以弧度为单位，可以正负
                            kPi = 3.141592654   # 180度
                            kPi_2 = 1.57079632  # 90 度
                        # tau 力矩，q 目标角度， dq 角速度，kp位置刚度， kd速度刚度（受到外界力矩，产生的位移/速度）

                    # 本地查看URDF

                        # 宇树3指版本
                            # 单手7个主动自由度，所以叫hand14

                            junweiliang@work_laptop:~/Desktop/github_projects/xr_teleoperate/assets/g1$ python ~/Desktop/github_projects/humanoid_teleop/g1_realrobot/urdf_viewer.py g1_body29_hand14.urdf

                            # humanoid_teleop repo下也有assets/g1/

                            junweiliang@work_laptop:~/Desktop/github_projects/humanoid_teleop/assets/g1$ python ~/Desktop/github_projects/humanoid_teleop/g1_realrobot/urdf_viewer.py g1_body29_hand14.urdf

                            # 宇树g1_comp，23自由度无手
                                junweiliang@work_laptop:~/Desktop/github_projects/humanoid_teleop/assets/g1$ python ~/Desktop/github_projects/humanoid_teleop/g1_realrobot/urdf_viewer.py g1_comp.urdf

                        # 宇树加因时灵巧手
                            # 单手URDF里，12个自由度，4个手指每个2个所以8个，剩4个自由度在拇指
                            # 实机单手只有6自由度，每个手指一个，拇指2个
                                junweiliang@work_laptop:~/Desktop/github_projects/humanoid_teleop/assets/g1$ python ~/Desktop/github_projects/humanoid_teleop/g1_realrobot/urdf_viewer.py g1_body29_inspired_hand.urdf

                        # replay!
                            # 安装环境, office
                                $ conda create -n g1 python=3.10 pinocchio=3.1.0 numpy=1.26.4 -c conda-forge
                                $ pip install meshcat
                                $ pip install casadi

                            # replay
                                (g1) junweil@office-precognition:~/projects/humanoid_teleop$ python g1_realrobot/visualize_arm_episodes.py ~/Downloads/g1_geishou_data.json assets/g1/g1_body29_inspired_hand.urdf --fps 60

                                按s开始暂停， ,.前后10step看

                # 重新再跑一次，我们不需要手腕的 RGB, 而且quest 3可以连接学校的wifi内网
                    # 修改 unitree_sim_isaaclab/tasks/g1_tasks/pick_place_cylinder_g1_29dof_inspire
                        # 或其他对应的task cfg文件

                        # junwei: 不需要wrist camera
                        #left_wrist_camera = CameraPresets.left_dex3_wrist_camera()
                        #right_wrist_camera = CameraPresets.right_dex3_wrist_camera()

                        # 【TODO】有bug，tv过程rgb没有更新图像了，
                        # 修复了加这个：https://github.com/unitreerobotics/xr_teleoperate/issues/111
                            elif not WRIST and args.sim:
                                img_client = ImageClient(tv_img_shape = tv_img_shape, tv_img_shm_name = tv_img_shm.name, server_address="127.0.0.1")
                            # 还有注释掉img_config中的wrist camera



                    # 1. 跑仿真

                        # office [去除两个wrist camera, 从11Hz涨到 14Hz, 71ms loop time]

                            (unitree_sim_env) junweil@office-precognition:~/projects/xr_teleoperate/unitree_sim_isaaclab$ python sim_main.py --device cpu  --enable_cameras  --task  Isaac-PickPlace-RedBlock-G129-Inspire-Joint    --enable_inspire_dds --robot_type g129

                        # laptop4 [去除两个wrist camera, 从17Hz涨到 21Hz, 46ms loop time]
                            # [lt4.precognition.team]

                            (unitree_sim_env) junweil@precognition-laptop4:~/projects/xr_teleoperate/unitree_sim_isaaclab$ python sim_main.py --device cpu  --enable_cameras  --task  Isaac-PickPlace-RedBlock-G129-Inspire-Joint   --enable_inspire_dds --robot_type g129

                            # 有很多红字error，没事

                    # 2. 跑遥操作服务器
                        # 注意 test2/， 这里的才是我们自己的repo

                        (tv) junweil@office-precognition:~/projects/test2/xr_teleoperate/teleop$ python teleop_hand_and_arm.py --xr-mode=hand  --arm=G1_29 --ee=inspire1 --sim --record

                        # 先不要加 --motion
                            # sim中应该不能加motion，机器人是固定的

                        # 原本的代码，dex3/inspire不能用controller，必须用手识别，把人的三指 map到宇树3指
                            # 需要写一个把dex3当作gripper, gripper value和controller的对应关系，可以参考dex1

                    # 3. Quest 3
                        这时候带上quest 3，打开浏览器
                            # https://lt4.precognition.team:8012?ws=wss://lt4.precognition.team:8012
                            # https://office.precognition.team:8012?ws=wss://office.precognition.team:8012
                            # 点刷新， 遥操作服务器终端会显示有websocket连接
                            # 先按r，开始遥操作，这时候仿真中手会飘起来。
                            # 再在VR中点passthrough模式，可以还看到周边环境
                            # 按键盘s 开始录制，s再结束
                            # 要用controller点meta按键，然后浏览器中点“quit”，然后可以摘下Quest 3了
                            # 再在遥操作服务器终端点q退出

                    # 4. replay刚刚的EP

                        (g1) junweil@office-precognition:~/projects/humanoid_teleop$ python g1_realrobot/visualize_arm_episodes.py ~/projects/xr_teleoperate/teleop//utils/data/episode_0002/data.json assets/g1/g1_body29_inspired_hand.urdf --fps 60

                        [08/01/2025] 手指可视化有问题，手指运动方向反了，角度应该也不对
                        [08/02/2025] 已经解决，把角度denormal之后，显示正常了，只不过只记录了6个自由度，握不了拳，在仿真里


            # [08/2025] 修改log
                # 0. 调试记录
                    # 0.1 测试quest 3 controller按钮获取、值范围等
                        (tv) junweil@office-precognition:~/projects/test2/xr_teleoperate/teleop$ python teleop_hand_and_arm.py --xr-mode=controller  --arm=G1_29 --ee=inspire1 --sim --debug_controller
                            # button都是 True/False
                                right_aButton, right_bButton
                                left_aButton (对应左手柄X), left_bButton (对应左手柄Y)

                            # trigger_state 需要完全按下才会触发成True一段时间
                            # trigger_value 0 -> 1之间，完全按下是1.0,
                            # squeeze_ctrl_value 类似

                            # thumbstick_state 需要整个遥杆按下才True
                            # thumbstick_value 零位[0., 0.,]， 值为-1.0 到1.0

                    # 0.2 确认 gripper形态如何对应手指
                        # 宇树3指版本
                            # 单手7个主动自由度，所以叫hand14

                            junweiliang@work_laptop:~/Desktop/github_projects/xr_teleoperate/assets/g1$ python ~/Desktop/github_projects/humanoid_teleop/g1_realrobot/urdf_viewer.py g1_body29_hand14.urdf

                            # MuJoCo tips
                                # 1. pause 仿真，然后点reset，获取零位的状态
                                # 2. Alt + J 可以可视化关节在哪
                                # 3. 具体joint 名称需要对着打印出来的name看, GUI中太短

                            # 关节角度全是0的情况下，拇指对其另外两指的空隙，90度角打开，
                            # 定义 gripper 全打开状态，让拇指微微弯曲，：
                                # right_hand_thumb_1_joint: -0.507
                                # right_hand_thumb_2_joint: -0.628
                                # left_hand_thumb_1_joint: 0.507
                                # left_hand_thumb_2_joint: 0.628
                                # 如[图](./g1_hand14_open.png)
                            # 定义 gripper 全关闭状态, 拇指和两指 指尖在一个平面上:
                                # left_hand_thumb_1_joint: 0.888
                                # left_hand_thumb_2_joint: 0.628
                                # left_hand_middle_0_joint: -0.707
                                # left_hand_middle_1_joint: -0.768
                                # left_hand_index_0_joint: -0.707
                                # left_hand_index_1_joint: -0.768
                                # right_hand_thumb_1_joint: -0.888
                                # right_hand_thumb_2_joint: -0.628
                                # right_hand_middle_0_joint: 0.707
                                # right_hand_middle_1_joint: 0.768
                                # right_hand_index_0_joint: 0.707
                                # right_hand_index_1_joint: 0.768
                                # 如[图](./g1_hand14_close.png)
                        # 宇树5指版本
                            junweiliang@work_laptop:~/Desktop/github_projects/xr_teleoperate/assets/g1$ python ~/Desktop/github_projects/humanoid_teleop/g1_realrobot/urdf_viewer.py g1_body29_inspired_hand.urdf

                                joint id: 41, name: R_thumb_proximal_yaw_joint, limits: [-0.100, 1.300]
                                joint id: 42, name: R_thumb_proximal_pitch_joint, limits: [-0.100, 0.600]
                                joint id: 43, name: R_thumb_intermediate_joint, limits: [0.000, 0.800]
                                joint id: 44, name: R_thumb_distal_joint, limits: [0.000, 1.200]
                                joint id: 45, name: R_index_proximal_joint, limits: [0.000, 1.700]
                                joint id: 46, name: R_index_intermediate_joint, limits: [0.000, 1.700]
                                joint id: 47, name: R_middle_proximal_joint, limits: [0.000, 1.700]
                                joint id: 48, name: R_middle_intermediate_joint, limits: [0.000, 1.700]
                                joint id: 49, name: R_ring_proximal_joint, limits: [0.000, 1.700]
                                joint id: 50, name: R_ring_intermediate_joint, limits: [0.000, 1.700]
                                joint id: 51, name: R_pinky_proximal_joint, limits: [0.000, 1.700]
                                joint id: 52, name: R_pinky_intermediate_joint, limits: [0.000, 1.700]

                            # 定义 gripper 全打开状态，拇指对齐食指方向：
                                # L_thumb_proximal_yaw_joint: 1.3
                                # R_thumb_proximal_yaw_joint: 1.3
                                # 如[图](./g1_inspire_open.png)

                            # 定义 gripper 全关闭状态，以下设置了主动关节，留有些空间，实机为连杆结构，应该拇指尖和食指尖接触：
                                # R_thumb_proximal_yaw_joint: 1.3
                                # R_thumb_proximal_pitch_joint: 0.5 # follow宇树在Inspired_Controller里的设定最大值
                                # R_index_proximal_joint: 0.756
                                # R_middle_proximal_joint: 0.756
                                # R_ring_proximal_joint: 0.756
                                # R_pinky_proximal_joint: 0.756
                                # L的数值也是一样的
                                # 如[图](./g1_inspire_close.png)


                # 1. Quest 3 controller 控制5指手 inspire1
                    # 1.0 开启对应的机器人的仿真
                        (unitree_sim_env) junweil@office-precognition:~/projects/test2/xr_teleoperate/unitree_sim_isaaclab$ python sim_main.py --device cpu  --enable_cameras  --task  Isaac-PickPlace-RedBlock-G129-Inspire-Joint    --enable_inspire_dds --robot_type g129

                    # 1.1 开启遥操作
                        (tv) junweil@office-precognition:~/projects/test2/xr_teleoperate/teleop$ python teleop_hand_and_arm.py --xr-mode=controller  --arm=G1_29 --ee=inspire1 --sim --record

                        # 看到 'r'提示后就可以带上头显了，拿起controller
                            # 点击浏览器刷新，确保前面终端显示已连接websocket
                            # 点击 pass through，开启遥操作数据传输
                            # 把双手摆好，然后右手 B按键开启程序，这时候机器人应该就响应遥操作了
                            # 左手x按键开启数据录制，再按x按键一次结束，按了一次可能要等一会儿才能显示save ***/data.json
                            # 右手A按键结束程序，回零位，这时可以按Meta按键退出VR，再在浏览器上点一次QUIT，就可以摘了

                    # 1.2 可视化刚刚录制的EP
                        (g1) junweil@office-precognition:~/projects/humanoid_teleop$ python g1_realrobot/visualize_arm_episodes.py ~/projects/test2/xr_teleoperate/teleop//utils/data/episode_0014/data.json assets/g1/g1_body29_inspired_hand.urdf --fps 60

                # 2. Quest 3 controller 控制3指手 dex3
                    # 2.0 开启对应机器人的仿真
                        (unitree_sim_env) junweil@office-precognition:~/projects/test2/xr_teleoperate/unitree_sim_isaaclab$ python sim_main.py --device cpu  --enable_cameras  --task  Isaac-PickPlace-RedBlock-G129-Dex3-Joint    --enable_dex3_dds --robot_type g129

                    # 2.1 开启遥操作
                        (tv) junweil@office-precognition:~/projects/test2/xr_teleoperate/teleop$ python teleop_hand_and_arm.py --xr-mode=controller  --arm=G1_29 --ee=dex3 --sim --record

                        --task_dir 任务文件夹

                    # 2.2 可视化刚刚录制的EP
                        (g1) junweil@office-precognition:~/projects/humanoid_teleop$ python g1_realrobot/visualize_arm_episodes.py ~/projects/test2/xr_teleoperate/teleop//utils/data/episode_0022/data.json assets/g1/g1_body29_hand14.urdf --hand_type dex3 --fps 60



            # 实机测试
                # 需要用到 arm_sdk topic。下肢应该只能用主运控. 向 rt/arm_sdk 话题发送 LowCmd 类型的消息
                # 对于电机的底层控制算法，唯一需要的控制目标就是输出力矩。对于机器人，我们通常需要给关节设定位置、速度和力矩，就需要对关节电机进行混合控制。

            # 实机中跑遥操作, 改controller控制？
```

