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

                # use opencv for the episode replay
                $ pip install numpy==1.26.4 opencv-python==4.10.0.84

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

                        (base) junweil@precognition-laptop4:~/projects/xr_teleoperate$ conda create -n tv python=3.10 pinocchio=3.1.0 numpy=1.26.4 opencv-python==4.10.0.84 -c conda-forge

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

                                    # 25个关节点，是Vuer库的：https://docs.vuer.ai/en/latest/examples/19_hand_tracking.html

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

                # 1. 先确保5指灵巧手可用
                    # 1.1 G1旗舰版，自带了线与485转usb模块在身体背部，用usb-c，连接到PC2,需要在PC2上启动手部服务
                    # 1.2 [08/12/2025] 宇树的线坏了，我们用独立的线和485转usb模块连接遥操作电脑，在遥操作电脑上开启手部服务

                        # laptop2安装与调试

                            # 下载代码 (有两个版本，我们用最新的v1.0.2 from https://support.unitree.com/home/zh/H1_developer/Dexterous_hand)
                                (base) junweil@office-precognition:~/Downloads$ ls h1_inspire_hand_202*
                                    h1_inspire_hand_20240507.zip  h1_inspire_hand_20250325.zip

                                (base) junweil@ai-precognition-laptop2:~/projects/g1_codes$ scp junweil@office.precognition.team:~/Downloads/h1_inspire_hand_2025* .

                            # 安装
                                $ sudo apt update
                                $ sudo apt install build-essential libeigen3-dev libyaml-cpp-dev
                                $ sudo apt install libboost-all-dev libspdlog-dev cmake

                                # 要先安装unitree SDK2 到system 目录 (ROS2)
                                    (base) junweil@ai-precognition-laptop2:~/projects/g1_codes$ git clone https://github.com/unitreerobotics/unitree_sdk2

                                    (base) junweil@ai-precognition-laptop2:~/projects/g1_codes/unitree_sdk2/build$ cmake ..

                                    (base) junweil@ai-precognition-laptop2:~/projects/g1_codes/unitree_sdk2/build$ sudo make install

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

                                (base) junweil@ai-precognition-laptop2:~/projects/g1_codes/h1_inspire_service/build$ cmake .. -DCMAKE_BUILD_TYPE=Release

                                (base) junweil@ai-precognition-laptop2:~/projects/g1_codes/h1_inspire_service/build$ make -j4

                                # 然后laptop2还要按前面说的安装遥操作依赖，tv

                            # 测试，把两只手都usb连到电脑

                                # usb识别到之后才会有 ls /dev/ttyUSB*

                                # 开手的服务器，这时手会合起来，食指没有其他手指那么贴手掌。
                                    # 12V电源不行的，会卡顿
                                    # 24V才行，24V3A是可以的。宇树的人也说要插24V电源 (G1 3个电源口中间那个)

                                (base) junweil@ai-precognition-laptop2:~/projects/g1_codes/h1_inspire_service/build$ sudo ./inspire_hand -s /dev/ttyUSB0

                                    加--network enp2s0?
                                    # 这个service的param, 应该默认两只手连一个usb
                                        ("help,h", "produce help message")
                                        ("serial,s", po::value<std::string>(&serial_port)->default_value("/dev/ttyUSB0"), "serial port")
                                        ("network", po::value<std::string>(&network)->default_value(""), "DDS network interface")
                                        ("namespace", po::value<std::string>(&ns)->default_value("inspire"), "DDS topic namespace")
                                        ;

                                # 另一个terminal，执行下面的，手会开始开合；用于测试的
                                (base) junweil@ai-precognition-laptop2:~/projects/g1_codes/h1_inspire_service/build$ ./h1_hand_example

                            # 开始测试
                                0. laptop2 连接学校校园网，然后有线连接G1，Quest 3连学校校园网
                                    # laptop2 有线连接后，设置有线网络，设置自己为192.168.123.201, netmask 255.255.255.0
                                    # 确保laptop2 全部流量走无线，有线的priority降低
                                        $ nmcli connection show

                                        # 看到有线网和无线网
                                        NAME                  UUID                                  TYPE      DEVICE
                                        HKUSTGZ               391770eb-48df-4888-94e6-6b6a768bc273  wifi      wlo1
                                        g1_wired              8cf798d4-a07d-41d0-b640-83646329a40a  ethernet  enp2s0

                                        # 看看各自的priority

                                            (tv) junweil@ai-precognition-laptop2:~/projects/xr_teleoperate$ nmcli connection show "HKUSTGZ" | grep ipv4.route-metric
                                            ipv4.route-metric:                      -1
                                            (tv) junweil@ai-precognition-laptop2:~/projects/xr_teleoperate$ nmcli connection show "g1_wired" | grep ipv4.route-metric
                                            ipv4.route-metric:                      -1

                                        # 修改，越低的优先越高

                                            sudo nmcli connection modify HKUSTGZ ipv4.route-metric 100
                                            sudo nmcli connection modify g1_wired ipv4.route-metric 200

                                    # 此时laptop2应该可以$ ping 192.168.123.164， PC2

                                1. 开启G1，进入调试模式, 阻尼或零力矩模式下，遥控器按L2+R2进入调试模式;  L2 + B进入阻尼

                                2. PC2上开image server
                                    # 首先，我们需要G1的d435的serial number
                                        进入G1 PC2选择2(noetic)，就是ROS1环境
                                        $ roslaunch realsense2_camera rs_camera.launch
                                        然后看到
                                            [INFO] [1755001723.579841277]: Device Name: Intel RealSense D435I
                                            [INFO] [1755001723.579856477]: Device Serial No: 243222072371

                                        注意config 中的serial number必须是字符串
                                    # 传代码过去
                                        (base) junweil@ai-precognition-laptop2:~/projects/xr_teleoperate$ scp -r teleop/image_server/ unitree@192.168.123.164:~/projects/

                                        # 先确保，image_server.py的 image config，和teleop_hand_and_arm.py一致
                                            config = {
                                                'fps': 30,
                                                'head_camera_type': 'realsense',
                                                'head_camera_image_shape': [720, 1280],  # Head camera resolution
                                                'head_camera_id_numbers': ["243222072371"],
                                                #'wrist_camera_type': 'opencv',
                                                #'wrist_camera_image_shape': [480, 640],  # Wrist camera resolution
                                                #'wrist_camera_id_numbers': [2, 4],
                                            }

                                    # 进入PC2开image server; 确保G1的realsense usbc接入了PC2
                                    # PC2上需要有realsense的包裹，可以直接安装
                                        # PC2设置了无线网络连到实验室的网络(可以连接外网)，有线是在G1里的网络

                                        (base) unitree@ubuntu:~/projects/image_server$ python3.8 -m pip install pyrealsense2 pyzmq logging_mp

                                    # 开始！！
                                        (base) unitree@ubuntu:~/projects/image_server$ python3.8 image_server.py
                                            20:38:32:045094 INFO     {'fps': 30, 'head_camera_type': 'realsense', 'head_camera_image_shape': [720,       image_server.py:141
                                                                     1280], 'head_camera_id_numbers': ['243222072371']}
                                            20:38:32:353138 INFO     [Image Server] Head camera 243222072371 resolution: 720 x 1280                      image_server.py:195
                                            20:38:32:353410 INFO     [Image Server] Image server has started, waiting for client connections...          image_server.py:207


                                # laptop2 测试image server
                                    (tv) junweil@ai-precognition-laptop2:~/projects/xr_teleoperate/teleop/image_server$ python image_client.py
                                    #这时能直接cv2窗口看到realsense视角

                                    # laptop2 测试各个rt/ 的DDS topic 是否ok?

                                # laptop2开启遥控操作程序，

                                    # 先开启手部服务 # 注意这里因时灵巧手必须两只手接一个usb口
                                        (base) junweil@ai-precognition-laptop2:~/projects/g1_codes/h1_inspire_service/build$ sudo ./inspire_hand -s /dev/ttyUSB0 --network enp2s0

                                    (tv) junweil@ai-precognition-laptop2:~/projects/xr_teleoperate/teleop$ python teleop_hand_and_arm.py --xr-mode=controller  --arm=G1_29 --ee=inspire1 --record --network_interface enp2s0


                                        # 这时候G1 会去到零位，因时灵巧手也会张开，终端显示inspire DDS OK

                                        # 这时可以带上Quest 3开始
                                            # Quest 3 中，先确保脸上了校园网HKUSTGZ，然后浏览器打开
                                                # https://lt2.precognition.team:8012?ws=wss://lt2.precognition.team:8012
                                                # 点击浏览器刷新，确保前面终端显示已连接websocket
                                                # 点击 pass through，开启遥操作数据传输
                                                # 把双手摆好，然后右手 B按键开启程序，这时候机器人应该就响应遥操作了
                                                # 左手x按键开启数据录制，再按x按键一次结束，按了一次可能要等一会儿才能显示save ***/data.json
                                                # 右手A按键结束程序，回零位，这时可以按Meta按键退出VR，再在浏览器上点一次QUIT，就可以摘了


                                                # 传输的图像非常卡顿


                                        # replay刚录制的序列, 传回office机器看

                                        # 可以同时看图像
                                        (tv) junweil@office-precognition:~/projects/humanoid_teleop$ python g1_realrobot/visualize_arm_episodes.py ~/Downloads/episode_0001/data.json assets/g1/g1_body29_inspired_hand.urdf --fps 60 --image_path /home/junweil/Downloads/episode_0001/colors/


                                    # Quest 3上退出: 右手A按键结束程序，机器人应该会自动回零位

                                # TODO: 图像的需要优化，image_client 输出延迟显示
                                    # 打开宇树代码里的Unit Test就好了
                                    # 还是要添加一个指标，看看当前有多大延迟
                                    # 30 还是 60 fps?
                                    # 修改image server, 获取图片是一个thread，然后发送图片是另一个thread
                                # TODO: 使用时用运控模式，保证站稳 [Done, 需要给 --motion]
                                # TODO: 遥操作时，quest挂脖子上;
                                    # 把quest3 舒适头套换回原版的头带
                                    # 点pass through之后摘下来，
                                # TODO: Replay加入图像可视化，查看图像和动作要对齐 [Done]
                                # TODO: 修改因时手，初始状态，拇指平一点，类似figure的  [Done]

            # 再次测试！在laptop6安装
                (base) junweil@precognition-laptop6:~/projects$ git clone https://github.com/JunweiLiang/xr_teleoperate

                (base) junweil@precognition-laptop6:~/projects$ conda create -n tv python=3.10 pinocchio=3.1.0 numpy=1.26.4  -c conda-forge

                $ pip install opencv-python==4.10.0.84

                (tv) junweil@precognition-laptop6:~/projects/xr_teleoperate/teleop/televuer$ pip install -e .

                (tv) junweil@precognition-laptop6:~/projects/xr_teleoperate/teleop/televuer$ openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout key.pem -out cert.pem

                $ cd ../robot_control/dex-retargeting/
                $ pip install -e .

                (tv) junweil@precognition-laptop6:~/projects/xr_teleoperate$ pip install -r requirements.txt

                (tv) junweil@precognition-laptop6:~/projects/xr_teleoperate/unitree_sdk2_python$ pip install -e .

                # 安装灵巧手程序

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

                # 开始!
                    0. g1开机，进入主运控
                    0. 传更新的image_server 代码
                        (base) junweil@precognition-laptop6:~/projects/xr_teleoperate$ scp -r teleop/image_server/ unitree@192.168.123.164:~/projects/
                    1. 开启image server
                        (base) unitree@ubuntu:~/projects/image_server$ python3.8 image_server.py
                        # 会显示30 fps

                            # 测试image server
                                (tv) junweil@ai-precognition-laptop6:~/projects/xr_teleoperate/teleop/image_server$ python image_client.py

                                # 这个显示latency 是0， 有点奇怪

                        # image_server要关闭Unit test重新开

                    2. 开始遥操作
                        # 先开启手部服务 # 注意这里因时灵巧手必须两只手接一个usb口
                        (base) junweil@ai-precognition-laptop6:~/projects/xr_teleoperate/h1_inspire_service/build$ sudo ./inspire_hand -s /dev/ttyUSB0 --network enp131s0

                        # 先把面前的桌子移开，避免0位时手臂撞到

                        (tv) junweil@ai-precognition-laptop6:~/projects/xr_teleoperate/teleop$ python teleop_hand_and_arm.py --xr-mode=controller  --arm=G1_29 --ee=inspire1 --record --network_interface enp131s0 --motion


                        # 这时候G1 会去到零位，因时灵巧手也会张开，终端显示inspire DDS OK
                        # 可以移动桌子了

                        # 这时可以带上Quest 3开始
                            # Quest 3 中，先确保脸上了校园网HKUSTGZ，然后浏览器打开
                                # https://lt6.precognition.team:8012?ws=wss://lt6.precognition.team:8012
                                # 点击浏览器刷新，确保前面终端显示已连接websocket
                                # 点击 pass through，开启遥操作数据传输
                                # 把双手摆好，然后右手 B按键开启程序，这时候机器人应该就响应遥操作了
                                # 左手x按键开启数据录制，再按x按键一次结束，按了一次可能要等一会儿才能显示save ***/data.json
                                # 右手A按键结束程序，回零位，这时可以按Meta按键退出VR，再在浏览器上点一次QUIT，就可以摘了

                # 宇树官方把因时的手state获取左右手搞反了
                    https://github.com/unitreerobotics/xr_teleoperate/issues/121

                # [08/14/2025] TODO
                    # 1. 图像传输与存储+states/actions的时间校验
                        # 开机，先确保G1 PC2和遥操作机器的时间同步？-- handshake, 算出时间差
                    # 2. quest 3 挂脖子
                    # 3. 加入腰部3自由度控制


                    # 1. timestamp时间问题
                        两台电脑，即时联网，timestamp是有可能有很大误差的，比如我laptop和office电脑，就有2秒误差
                            junweiliang@work_laptop:~/Desktop/github_projects/humanoid_teleop$ python g1_realrobot/time_sync_test_client.py office.precognition.team
                                Network Latency (RTT): 6.48 ms
                                Server UTC Timestamp: 2025-08-14 21:12:58.341972+00:00
                                Client UTC Timestamp: 2025-08-14 21:12:56.105529+00:00
                                Estimated Time Difference (Client - Server): -2239.68 ms
                                A positive value means the client's clock is ahead of the server's clock.
                                A negative value means the client's clock is behind the server's clock.
                        # 所以获取图片不能用timestamp算

                        # teleop_hand_and_arm.py 的loop逻辑
                            # 会保证不超过 --freq, 默认60 fps
                            # 单个loop里，获取tele_data之后，控制机械臂和手，也获取当前机械臂和手的状态和action，然后copy当前的image
                                # 别的进程一直在更新这个image tensor
                                    # 我需要知道这个image实际延迟有多少
                                        # 所以teleop开启了image server, image client 先去拿到两个电脑的timestamp差值，
                                        # 然后每个image就能计算在本地的 实际时间，算出存储的时候慢了多少

                                # 同时会吧这个image tensor发给XR 设备

                                # teleop/televuer/src/televuer/televuer.py 中可以修改图片的显示在VR 中，显示延迟
                                    # 还修改了VR显示的位置，往下放一点
                                    # 记得重新pip install -e .

                                # 添加了delay 到data.json的每个item中，的"delay"字段，float 秒，

                        ## save episode，修改成等待把图片所有东西都存完，VR假死，等到存好了再反应

                    # 3. --motion用的是另外的DDS topic for control G1
                        kTopicLowCommand_Debug  = "rt/lowcmd" -- 调试模式
                        kTopicLowCommand_Motion = "rt/arm_sdk" --motion
                        以上都是lowcmd，有35个自由度的motor cmd (29个是g1的)
                        kTopicLowState = "rt/lowstate"

        # [08/17/2025] 更新后在laptop6测试
            # 更新Vuer
                (tv) junweil@precognition-laptop6:~/projects/xr_teleoperate/teleop/televuer$ pip install -e .

            1. 先测试新的image server client
                # 发送新的代码到G1
                    (tv) junweil@precognition-laptop6:~/projects/xr_teleoperate$ scp -r teleop/image_server/ unitree@192.168.123.164:~/projects/

                    # 开启g1 server
                        (base) unitree@ubuntu:~/projects/image_server$ python3.8 image_server_timesync.py

                    # laptop6上测试 (会弹出cv2图像界面)
                        (tv) junweil@precognition-laptop6:~/projects/xr_teleoperate/teleop/image_server$ python image_client_timesync.py

                        # 测试了两分钟，从delay从3ms涨到7ms
                        # 有可能出现负的delay，可能是clock drift，都保存下来吧

                2. 开启两只手的controller

                    (base) junweil@precognition-laptop6:~/projects/xr_teleoperate/h1_inspire_service/build$ sudo ./inspire_hand -s /dev/ttyUSB1 --network enp131s0

                    -s /dev/ttyUSB0

                    # 右手食指可能会没响应，这时候需要拔掉手上的线，重新接，重新开controller能恢复
                        # 把手恢复握拳或者张开状态
                            (tv) junweil@precognition-laptop6:~/projects/xr_teleoperate$ h1_inspire_service/build/h1_hand_example

                3. 开启遥操作！
                    # 所以在这个之前，需要在laptop6上开启3个screen
                        # 第一个连着unitree g1，在上面开image_server
                        # 第二三在laptop6上直接连着因时手，开controller

                    (tv) junweil@ai-precognition-laptop6:~/projects/xr_teleoperate/teleop$ python teleop_hand_and_arm.py --xr-mode=controller  --arm=G1_29 --ee=inspire1 --record --network_interface enp131s0 --motion

                    # 右手controller现在控制两只手开合

                    # 戴上VR，刷新浏览器，enter passthrough，图像应该在地板上，然后用就可以了

                    # 图像client会做100次handshake，估计的延迟为10ms以内，然后后面平均延迟也是5ms以内
                        # 存储episode的按钮问题已经解决，按一次3秒不会再触发的。
                        # 但是存储开始和结束，VR中不会有提示，要看电脑屏幕

                    # 发送episode到office 查看，同时显示delay

                        (tv) junweil@office-precognition:~/projects/humanoid_teleop$ python g1_realrobot/visualize_arm_episodes.py ~/Downloads/episode_0012/data.json assets/g1/g1_body29_inspired_hand.urdf --fps 60 --image_path /home/junweil/Downloads/episode_0012/colors/


    # [已解决] 挂脖子使用，需要开developer mode，需要建立一个meta账号，使用ipad的horizon app，还要开duo二次验证，然后建立org, org验证还需要上传护照，名字生日要对，等48小时验证。
        # https://www.reddit.com/r/OculusQuest/comments/17sa8n6/tutorial_quest_3_developer_mode_4_easy_steps/
        # 好像不需要上传护照就行 账号 junweiliang1114@gmail.com ok
            # 在horizon app上开启developer mode

        # 然后在Mac OS 安装adb，比较简单
            junweiliang@work_laptop:~/Downloads$ wget https://dl.google.com/android/repository/platform-tools-latest-darwin.zip

            # 解压就能用，直接连接usb-c连接quest 3

                junweiliang@work_laptop:~/Downloads/platform-tools$ ./adb devices

                List of devices attached
                2G97C5ZH3701J1  unauthorized
                # 需要在VR里点Allow

                junweiliang@work_laptop:~/Downloads/platform-tools$ ./adb devices
                List of devices attached
                2G97C5ZH3701J1  device

                # 关闭识别不到脑袋会休眠
                junweiliang@work_laptop:~/Downloads/platform-tools$ ./adb shell am broadcast -a com.oculus.vrpowermanager.prox_close
                    Broadcasting: Intent { act=com.oculus.vrpowermanager.prox_close flg=0x400000 }
                    Broadcast completed: result=0

                # 这下quest 3放下台面，还会一直显示的，所以后面要一直插着电

                    # 开启?
                        junweiliang@work_laptop:~/Downloads/platform-tools$ ./adb shell am broadcast -a com.oculus.vrpowermanager.automation_disable
                            Broadcasting: Intent { act=com.oculus.vrpowermanager.automation_disable flg=0x400000 }
                            Broadcast completed: result=0
        # 现在可以了，会一直亮屏幕
        # 平时不用，可以按一下电源键，休眠，然后再按一次唤醒，应该没关机的。不用要一直插着电充电

    # [已解决][08/18/2025] 解决因时左右手状态、动作问题，问官方
        https://github.com/unitreerobotics/xr_teleoperate/issues/46
        # 已更新C++程序，解决了！！
            https://github.com/JunweiLiang/xr_teleoperate/tree/main/h1_inspire_service

        # 两个485 USB模块，可以插到一个usb转usbc hub。确保先插右手那就是/dev/ttyUSB0，插上485模块会亮一个绿灯，开启下面服务会有两个绿灯

        (base) junweil@precognition-laptop6:~/projects/xr_teleoperate/h1_inspire_service/build$ sudo ./inspire_hand --serial_left /dev/ttyUSB1 --serial_right /dev/ttyUSB0

        # 测试双手开合，状态获取


    # [08/18/2025] 更新后在laptop6测试,挂脖子，双手灵巧手
            0. 更新Vuer
                (tv) junweil@precognition-laptop6:~/projects/xr_teleoperate/teleop/televuer$ pip install -e .

            1. 先测试新的image server client
                # 发送新的代码到G1
                    (tv) junweil@precognition-laptop6:~/projects/xr_teleoperate$ scp -r teleop/image_server/ unitree@192.168.123.164:~/projects/

                    # 开启g1 server
                        (base) unitree@ubuntu:~/projects/image_server$ python3.8 image_server_timesync.py

                    # laptop6上测试 (会弹出cv2图像界面)
                        (tv) junweil@precognition-laptop6:~/projects/xr_teleoperate/teleop/image_server$ python image_client_timesync.py

                        # 测试了两分钟，从delay从3ms涨到7ms
                        # fps 30


                2. 开启两只手的controller

                    # 如果两只手连PC2的话
                        # 发新代码过去
                            (base) junweil@precognition-laptop6:~/projects/xr_teleoperate$ scp -r h1_inspire_service/ unitree@192.168.123.164:~/projects/
                        # 安装 (如果装过了可以跳过)
                            $ sudo apt install libfmt-dev
                            (base) unitree@ubuntu:~/projects/h1_inspire_service/build$ cmake .. -DCMAKE_BUILD_TYPE=Release

                            (base) unitree@ubuntu:~/projects/h1_inspire_service/build$ make -j4

                        # 开启controller
                            # 先确认左右手连着那个 ttyUSB
                            # 宇树的485转usb模块，有4个口
                                (base) unitree@ubuntu:~/projects/h1_inspire_service/build$ ls /dev/ttyUSB*
                                /dev/ttyUSB0  /dev/ttyUSB1  /dev/ttyUSB2  /dev/ttyUSB3
                            # 好像没有办法。插的是USB1, USB2
                                # 4个口，0-3，
                            # 宇树有线端口是eth0

                            (base) unitree@ubuntu:~/projects/h1_inspire_service/build$ sudo ./inspire_hand --serial_left /dev/ttyUSB2 --serial_right /dev/ttyUSB1 --network eth0

                            # [08/20/2025] 用./h1_hand_example测试，手能持续开合，但是状态获取延迟很高，基本数字10秒更新一次

                            # 这个应该是宇树的线的问题，换成下面单口485的线，正常
                            # 我们目前还是用下面连laptop6的方案吧

                            # 查看该DDS话题
                            (base) unitree@ubuntu:~$ cyclonedds subscribe rt/inspire/state
                            # 对应ROS2话题是 没有 rt

                    # 如果两只手外接到laptop6:
                        (base) junweil@precognition-laptop6:~/projects/xr_teleoperate/h1_inspire_service/build$ sudo ./inspire_hand --serial_left /dev/ttyUSB0 --serial_right /dev/ttyUSB1 --network enp131s0

                        # 右手食指可能会没响应，这时候需要拔掉手上的线，重新接，重新开controller能恢复
                            # 把手恢复握拳或者张开状态
                                (tv) junweil@precognition-laptop6:~/projects/xr_teleoperate$ h1_inspire_service/build/h1_hand_example

                        # 如果确保USB0是左手？从usbc hub上拔掉两个485模块，先插左手的，就一定是USB0


                3. 开启遥操作！
                    # 所以在这个之前，需要在laptop6上开启2个screen
                        # 第一个连着unitree g1，在上面开image_server
                        # 第二个连着unitree g1，在上面开hand controller
                            #在laptop6上直接连着因时手，开controller

                    (tv) junweil@ai-precognition-laptop6:~/projects/xr_teleoperate/teleop$ python teleop_hand_and_arm.py --xr-mode=controller  --arm=G1_29 --ee=inspire1 --record --network_interface enp131s0 --motion

                        # 显示图像延迟还是可能是负的，不知道为啥
                        # 100次handshake，计算出RTT是15ms左右，后面延迟就是负的
                        # 计算出是10ms以内，后面延迟就是正的看起来正常

                    # 戴上VR，刷新浏览器，enter passthrough，图像应该在地板上，这时图像就是实际的图像
                        # 虽然延迟可能看起来只有10几ms，在VR中至少有1秒，那是因为图像是laptop分发到wifi，wifi再给VR. 延迟算的是g1到laptop

                        # passthrough之后，Quest 3 会生成一个安全区域，你应该不能离开这里

                        # 然后可以开始挂脖子，
                        # 一定要尽量把VR挂脖子挂正，VR朝向前方，要挺胸。
                        # 手要放低一点，不然待会G1就会一下子高举手

                        # 原理就是，这里还是假设VR在头上，算的手controller到头的相对距离作为ee

                        # 准备好，就可以按右手 B按键开始了，准备好左手摇杆控制机器人走动，因为手伸长可能导致机器人不平衡

                        # 开始之后，laptop上也有个cv2图像，显示FPS 60左右

                        # 按键左手x开始录制，然后再按结束录制，结束时terminal有提示saved **data.json


                    # 发送episode到office 查看，同时显示delay

                        (tv) junweil@office-precognition:~/projects/humanoid_teleop$ python g1_realrobot/visualize_arm_episodes.py ~/Downloads/episode_0014/data.json assets/g1/g1_body29_inspired_hand.urdf --fps 60 --image_path /home/junweil/Downloads/episode_0014/colors/

                    # 本次测试的视频记录
                        # 挂脖子_遥操作_VR和手部初始位置 推荐(./Quest3挂脖子_遥操作_VR和手部初始位置.png)
                        # 挂脖子_motion_遥操作
                            https://drive.google.com/file/d/1hCdykq-uBqPRdp3XcUvjPylPYShVLrxO/view?usp=drive_link
                        # 挂脖子_motion_出现重心失衡
                            https://drive.google.com/file/d/1FyvRNyYs1ElXgOtgQ7miPv58fGufbS9O/view?usp=drive_link
                        # replay记录
                            https://drive.google.com/file/d/1bJEhA-KcAKJhdJigO7RFXePcQ2NJexHW/view?usp=drive_link

    # [已解决] 添加腰部自由度
        # 0. 查看g1-29dof腰部自由度

            junweiliang@work_laptop:~/Desktop/github_projects/xr_teleoperate/assets/g1$ python ~/Desktop/github_projects/humanoid_teleop/g1_realrobot/urdf_viewer.py g1_body29_hand14.urdf
            id 从0开始, 以下id和宇树的arm7 sdk example一致
            joint id: 12, name: waist_yaw_joint, limits: [-2.618, 2.618]
                # 正的弧度是上往下看(z轴方向往回看)，逆时针，也就是左转腰
                # 感觉 +- 0.6够了，不然就吓人了
            joint id: 13, name: waist_roll_joint, limits: [-0.520, 0.520]
                # 正的弧度是，腰往机器人的右摆， 从x轴的方向（朝前）往机器人看，逆时针转
            joint id: 14, name: waist_pitch_joint, limits: [-0.520, 0.520]
                # 正的弧度是，腰往前磕头， 从y轴的方向（朝机器人左手）往机器人看，逆时针转

            # pitch 和roll特别容易失衡。设置为 +- 0.05就还行。所以干脆就不要了，只保留yaw

        # 1. 先解锁腰部
            https://support.unitree.com/home/zh/G1_developer/waist_fastener
            # 需要手机app连接设置腰部解锁

            # 还要全身标定！不然重启后亮红灯
                https://support.unitree.com/home/zh/G1_developer/quick_start

            # 标定完，腰部应该还是歪的，可以在正常运控下，手机APP里，给腰部横滚、俯仰电机加偏置，我加了4度3度，步态正常了

            # 宇树建议，全身标定的时候，还是要把腰部固定件弄上去

            # 还是重新再标定了，装上腰部固定件标定电机，然后再拆下来，这下一开始腰就正常了，不需要加电机偏移量

        # 2. 开启遥操作，和之前的一样，添加 --use_waist即可

            # 同时也可以不解锁腰部，这样就只能yaw

            # 我们一定是--motion的方式才能控腰部
            # 开启程序前，主运控模式，先让G1走出龙门架，卸下安全绳

            # 确保开始之前，VR一定要水平于地面！！
            # 挂脖子后，双手放到尽量靠近身体的左右两侧开始。我总是开始的时候G1手就伸长了

            # 现在我直接吧pitch roll都设置成0了，腰部只保留左右转

            #  要操作过程中遇到失衡，右手controller按A退出程序，就应该回位了，别慌


        # 3. replay 带上腰部的episode

            (tv) junweil@office-precognition:~/projects/humanoid_teleop$ python g1_realrobot/visualize_arm_episodes.py ~/Downloads/episode_0016/data.json assets/g1/g1_body29_inspired_hand.urdf --fps 60 --image_path /home/junweil/Downloads/episode_0016/colors/ --use_waist


        # 4. replay 状态而不是action

            (tv) junweil@office-precognition:~/projects/humanoid_teleop$ python g1_realrobot/visualize_arm_episodes.py ~/Downloads/episode_0014/data.json assets/g1/g1_body29_inspired_hand.urdf --fps 60 --image_path /home/junweil/Downloads/episode_0014/colors/ --show_states

            # 因时手的states 好像很有问题，都是超过限位的值
            # 身体其他关节states正常

            # [08/22/2025]宇树说，他们的 API有问题，用这个更新的：https://github.com/unitreerobotics/DFX_inspire_service
            # [08/31/2025]我们修复了：https://github.com/precognitionlab/xr_teleoperate_precognitionlab/blob/main/g1_inspire_service/inspire_g1_junwei.cpp

    # [08/30/2025] 更新因时API
        # 官方的还是有问题，需要fork之后修改 https://github.com/JunweiLiang/DFX_inspire_service/blob/master/include/SerialPort.h
            send函数添加
             tcflush(fd_, TCIFLUSH); tcdrain(fd_);

             # 更新到 https://github.com/JunweiLiang/DFX_inspire_service [Done]
                # 这个库只能在 arm64 Jetson上编译
             # 测试左右手
                # 拔掉一只然后看左右手状态输出
                    (base) unitree@ubuntu:~/projects/DFX_inspire_service/build$ sudo ./inspire_g1_junwei --serial_left /dev/ttyUSB1 --serial_right /dev/ttyUSB2

                    (base) unitree@ubuntu:~/projects/DFX_inspire_service/build$ ./hand_example

                    # 宇树的板子，usbc口放右边，电子元件面朝上，usb口上往下0->3

             # 整合到 xr_teleop [Done]

             # 安装2号机，重新测试遥操作，replay看states
                # 先发送最新的代码去PC2
                    (base) junweil@precognition-laptop6:~/projects/xr_teleoperate$ scp -r g1_inspire_service/ unitree@192.168.123.164:~/projects/
                # PC2上开screen开启controller
                    # 先确保，左手线接到ttyUSB1, 右手接到ttyUSB2

                    (base) unitree@ubuntu:~/projects/g1_inspire_service/build$ sudo ./inspire_g1_junwei --serial_left /dev/ttyUSB1 --serial_right /dev/ttyUSB2

                    # 小测试，手应该会开合，读取状态值左右手都为0-1之间
                        (base) unitree@ubuntu:~/projects/g1_inspire_service/build$ ./hand_example

             (tv) junweil@ai-precognition-laptop6:~/projects/xr_teleoperate/teleop$ python teleop_hand_and_arm.py --xr-mode=controller  --arm=G1_29 --ee=inspire1 --record --network_interface enp131s0 --motion --use_waist

             # 宇树原版的摇杆motion control速度是对的。注意用quest 3 的摇杆，你感觉的前进方向，可能不对
                # https://github.com/unitreerobotics/xr_teleoperate/issues/135

                # replay 刚刚因时的states，没问题了，states和图像完全同步，action会meshcat更快

                (tv) junweil@office-precognition:~/projects/humanoid_teleop$ python g1_realrobot/visualize_arm_episodes.py ~/Downloads/episode_0019/data.json assets/g1/g1_body29_inspired_hand.urdf --fps 60 --image_path /home/junweil/Downloads/episode_0019/colors/ --show_states

                # replay video:
                    https://drive.google.com/file/d/1NcZwwz5QGL_tXFJnFkHAeQEQkGaGe7-I/view?usp=sharing

```
## 换成双目相机
```
    # 双目相机，宇树官方说用的下面链接，用125度无畸变镜头，30fps或者60fps都可以，60fps的贵一倍
        # 【淘宝】7天无理由退货 https://e.tb.cn/h.hCJBMeIjD9yKba5?tk=022k4ocp2ja HU108 「200万像素彩色全局曝光双1080P双目同步相机60帧USB2.0测距摄像头」

    # 原理就是，直接能读到 3840x1080 的图像，直接把两张图拼一起。teleop_hand_and_arm.py BINOCULAR的判断，直接从分辨率判断，存图片的时候会存成两个camera 的image

    # 测试遥操作again!!
        # 发代码到pc2
            scp -r teleop/image_server/ unitree@192.168.123.164:~/projects/

        # 使用2560x720
        (base) unitree@ubuntu:~/projects/image_server$ python3.8 image_server_timesync.py --bino

        # laptop上subscribe 检查一下
            # 好像只有12fps
            (tv) junweil@precognition-laptop6:~/projects/xr_teleoperate/teleop/image_server$ python image_client_timesync.py
            # 和摄像头厂家问了知道是摄像头没有锁定帧率，把灯光开最猛之后，2560x720可以达到30fps
            # 后续全部摄像头都让厂家锁帧了

        teleop 也加 --bino即可，会存两张图片。
        Quest 3中看到的是双目影像。已修改televuer双目放地上

        # replay

            (tv) junweil@office-precognition:~/projects/humanoid_teleop$ python g1_realrobot/visualize_arm_episodes.py ~/Downloads/episode_0020/data.json assets/g1/g1_body29_inspired_hand.urdf --fps 60 --image_path /home/junweil/Downloads/episode_0020/colors/ --show_states --bino --use_waist

            # video:
                https://drive.google.com/file/d/1FCq3VrqFD7ZqAbCGKYQuz9zdaDi43Xp8/view?usp=sharing

    # 双目相机60fps降速慢动作效果
        (tv) junweil@precognition-laptop6:~/projects/humanoid_teleop$ python g1_realrobot/save_video_high_speed_cam.py --cam 4 --fps 60 --h 720 --w 2560 --save_video --write_video_fps 15 --write_video_path ~/Downloads/bino_test_video.mp4

        # 亮度够了，网球自由落体还是略有重影
            https://drive.google.com/file/d/1wPgpKeWCHWoakl0P4H713gwwgQ8QTXty/view?usp=drive_link
```
## 更新三指手开合，测试Quest 3s
```
    # 更新开合数值，不然抓不了瓶子
    如[图](./g1_hand14_open_09212025.png)
    如[图](./g1_hand14_close_09212025.png)
    # 添加了三指手 stop_and_go_home()函数，停止的时候手指要回到安全位置以免蹭到大腿

    # Quest 3s与Quest 3对比，
        # Quest 3s是更新的版本，且更便宜 (4k vs. 2.5k RMB含税)。
        # 没有脑门识别，所以可以一直亮着屏幕无需开发者模式才能挂脖子；
        # 手部追踪号称是一样的，3s有红外所以光线暗的时候还会更好；外部摄像头一样的
        # 里面的镜片，比Quest 3差，必须某个角度才会不糊
        # 电池、内存容量就无所谓了

    # Quest 3s配置
        # 设备初始化，以下方法还是连接不上学校wifi。我还是用我的iphone开热点（可以直接连外网），quest3s直接可以更新，需要二十分钟
            # HKUST(GZ)  需要选择PEAP, M**v2, 然后选择use system certificate, 域名输入nce.hkust-gz.edu.cn, identity输入用户名，匿名框留空，然后输入密码，即可。
        # 设备连上外网更新后，还是需要我的美区iPad的Meta Horizon APP,连接同样的手机热点，配对。
        # 搞完更新、初始tutorial后，进入正常的界面，可以连接HKUSTGZ的wifi了，

        # 然后我设置4小时没识别到头部运动才关闭电源（默认一分钟），这个 就一直亮屏幕了，不需要开发者模式adb关闭额头识别
            # 按一下电源进入休眠。最好插着电源

            # 再按一下电源键就启动回来了，同样的浏览器可以拿来做遥操作了

```
## 录取单手，双手的上半身任务, 然后 可视化
```
    # 更新代码，需要预先在episode_writer.py 定义好任务描述
        --task_dir 放nvme
        --task_name can_inserting/can_sorting/unloading/towel_folding/twist_off_bottle_cap
        # 同步任务描述在notion: https://www.notion.so/242b5be14e8280759dfbff089cd6a9c3?source=copy_link#257b5be14e82804390ade8976afe5257

    # 用Quest 3s/Quest 3均可 [上肢动作, 一共收集手臂14+手2+腰1=共17自由度]
        # image_server_timesync.py改成realsense 640x480分辨率, 更新宇树G1 PC2上的代码

        # 0. 开启G1，三指灵巧手会开机自检，张开然后握拳，如果有任意一只手没动，就需要重启/拆背板重新插拔手的线，直到都没问题； 进入主运控，走到桌子旁边;结束退出前需要后退一下以免手撞到桌子。有第二个人帮忙就更好
            # 右手B开启遥操作，A结束遥操作(手臂、手指都会自动复位)
            # 左手遥杆控制行走,注意轻轻推！推一下就复位，以免走太多太快失去平衡
            # 左手 x按键是开启结束episode录制
        # 1. 开启unitree image server
        # 2. 开启遥操作

            (tv) junweil@precognition-laptop6:~/projects/xr_teleoperate/teleop$ python teleop_hand_and_arm.py --xr-mode=controller  --arm=G1_29 --ee=dex3 --record --network_interface enp131s0 --motion --use_waist --task_name can_sorting --task_dir ../data/can_sorting

            # 数据存储到 ../data/can_sorting/episode_0001
                # 包含各个关节状态、action数据，RGB数据，以及trigger 的原始value

        # 3. 仿真replay确认数据质量, 可以查看单双目RGB、收集的states/actions、trigger value
            # 注意，trigger value为1.，手不一定完全合上，尤其是抓住东西的时候

            (tv) junweil@office-precognition:~/projects/humanoid_teleop$ python g1_realrobot/visualize_arm_episodes.py ~/Downloads/data/can_sorting/episode_0001/data.json assets/g1/g1_body29_hand14.urdf --fps 60 --image_path /home/junweil/Downloads/data/can_sorting/episode_0001/colors/ --use_waist --hand_type dex3

            # 桌面任务5，每个50episode数据在office
                (base) junweil@office-precognition:~/projects/huawei_data$ ls
                101_data  desk5_tasks_50ep.tar

                # 可视化
                    (tv) junweil@office-precognition:~/projects/humanoid_teleop$ python g1_realrobot/visualize_arm_episodes.py ~/projects/huawei_data/101_data/can_sorting/episode_0005/data.json assets/g1/g1_body29_hand14.urdf --fps 60 --image_path ~/projects/huawei_data/101_data/can_sorting/episode_0005/colors/ --use_waist --hand_type dex3

                # 可视化样例
                    https://drive.google.com/drive/folders/1MkMhkSa_LnhpYDLptVZQF8Nald4V_Wjs?usp=drive_link


    # 用Quest 3s/Quest 3均可 [整身动作, 一共收集手臂14+手2+腿12+腰1=共29自由度]

        # 宇树主运控

        # homie运控

        # Our  Homie 运控

```
## 录取上半身动作后，实机replay
```
    # 右手指引右边走
        # 先通过replay确认 开始step结束step

            (tv) junweil@office-precognition:~/projects/humanoid_teleop$ python g1_realrobot/visualize_arm_episodes.py ~/Downloads/episode_0021/data.json assets/g1/g1_body29_inspired_hand.urdf --fps 60 --image_path /home/junweil/Downloads/episode_0021/colors/ --show_states --bino --use_waist

        # 开始65， 结束516
        # 录屏：https://drive.google.com/file/d/1hlDVXzAboo24zmspZlIdaFzTn9Lr40Zp/view?usp=drive_link

    # 左手指引左边走
        # replay
            (tv) junweil@office-precognition:~/projects/humanoid_teleop$ python g1_realrobot/visualize_arm_episodes.py ~/Downloads/episode_0022/data.json assets/g1/g1_body29_inspired_hand.urdf --fps 60 --image_path /home/junweil/Downloads/episode_0022/colors/ --show_states --bino --use_waist

            # 开始40 结束439

        # 新手势数据存储，以及预定义一个dict
            junweiliang@work_laptop:~/Downloads$ scp junweil@office.precognition.team:~/Downloads/episode_0022/data.json 0022_data.json
            junweiliang@work_laptop:~/Downloads$ mv 002*.json ~/Desktop/github_projects/large_models/gesture_data

            custom_action = {"left_welcome": {
                "json_name": "0022_data.json",
                "start": 40,
                "end": 439
            },
            "right_welcome": {
                "json_name": "0021_data.json",
                "start": 65,
                "end": 516
            }}

    # large_models 里添加 robot_arm_high_level_v3.py
        # 注意需要给腰比较大的 kp和kd，否则转身的时候容易被重心压弯腰

    # 测试代码，包括测试宇树自带的手势arm service，以及自定义的arm_sdk控制的手势序列

    # 代码和gesture data也放到g1_teleop

        (agent_api) junweil@precognition-laptop6:~/projects/speechvla/MLLMs$ python test_g1_high_level.py gesture_data/ enp131s0

```
## 添加Homie底层控制+腰部遥操作
```
    # [08/28/2025] 使用宇树最新的 Isaac lab 环境，看看DDS的话题发布如何
        # 之前在office电脑安装过(unitree_sim_env)环境，需要重新安装环境Sim 5.0：
            # IsaacSim 4.5 出现 [carb.graphics-vulkan.plugin] VkResult: ERROR_OUT_OF_HOST_MEMORY
                https://github.com/unitreerobotics/unitree_sim_isaaclab/issues/25#issuecomment-3204764808

            (base) junweil@office-precognition:~/projects/unitree_sim_5.0/unitree_sim_isaaclab$ conda create -n unitree_sim5.0_env python=3.11

            # 根据：https://github.com/unitreerobotics/unitree_sim_isaaclab/blob/main/doc/isaacsim5.0_install.md

            (unitree_sim5.0_env) junweil@office-precognition:~/projects/unitree_sim_5.0$ git clone https://github.com/eclipse-cyclonedds/cyclonedds

            cyclonedds$ git checkout 0.10.2
            cyclonedds/build$ cmake ..
            cyclonedds/build$ cmake --build .
            cyclonedds/build$ sudo cmake --build . --target install

            export CYCLONEDDS_HOME=/usr/local/

            # 然后再安装unitree_sdk_python2

            $ pip install onnxruntime
            $ sudo apt install git-lfs

                # 出现
                    OSError: /home/junweil/anaconda3/envs/unitree_sim5.0_env/bin/../lib/libstdc++.so.6: version `GLIBCXX_3.4.30' not found (required by /home/junweil/anaconda3/envs/unitree_sim5.0_env/lib/python3.11/site-packages/omni/libcarb.so)


                (base) junweil@office-precognition:~/projects/unitree_sim_5.0/unitree_sim_isaaclab$ cd /home/junweil/anaconda3/envs/unitree_sim5.0_env/bin/../lib/
                (base) junweil@office-precognition:~/anaconda3/envs/unitree_sim5.0_env/lib$ cp /usr/lib/x86_64-linux-gnu/libstdc++.so.6.0.33 .
                (base) junweil@office-precognition:~/anaconda3/envs/unitree_sim5.0_env/lib$ rm libstdc++.so.6
                (base) junweil@office-precognition:~/anaconda3/envs/unitree_sim5.0_env/lib$ ln -s libstdc++.so.6.0.33 libstdc++.so.6


                conda install -c conda-forge libgcc-ng libstdcxx-ng

            # 1. 下载模型！！locomotion模型

                (unitree_sim5.0_env) junweil@office-precognition:~/projects/unitree_sim_5.0/unitree_sim_isaaclab$ bash fetch_assets.sh

                [08/29/2025]缺失这个，临时解决：
                (base) junweil@office-precognition:~/projects/unitree_sim_5.0/unitree_sim_isaaclab/assets/model$ cp policy1.onnx policy2.onnx

            # 开启motion control sim (Isaac Sim 5.0)
                (unitree_sim5.0_env) junweil@office-precognition:~/projects/unitree_sim_5.0/unitree_sim_isaaclab$ python sim_main.py --device cpu  --enable_cameras  --task Isaac-Move-Cylinder-G129-Dex3-Wholebody --enable_dex3_dds --robot_type g129

                    # teminal 中ctr + C结束，不要点Isaac Sim 叉
                # 机器人会自动往前走
                # 开个键盘控制：
                    (tv) junweil@office-precognition:~/projects/unitree_sim_5.0/unitree_sim_isaaclab$ python send_commands_keyboard.py


            # 2. 检查DDS发布

                # 直接用cyclonedds 读不到任何话题
                    (tv) junweil@office-precognition:~/projects/unitree_sim_5.0/unitree_sim_isaaclab$ DDS_DOMAIN_ID=1 cyclonedds ls

                    (tv) junweil@office-precognition:~/projects/unitree_sim_5.0/unitree_sim_isaaclab$ cyclonedds subscribe rt/lowstate


                     🚨 No types could be discovered over XTypes, no dynamic subsciption possible

                # 写代码吧

                    1. 先开启仿真DDS

                        (unitree_sim5.0_env) junweil@office-precognition:~/projects/unitree_sim_5.0/unitree_sim_isaaclab$ python sim_main.py --device cpu  --enable_cameras  --task Isaac-Move-Cylinder-G129-Dex3-Wholebody --enable_dex3_dds --robot_type g129

                        # 因时手
                            (unitree_sim5.0_env) junweil@office-precognition:~/projects/unitree_sim_5.0/unitree_sim_isaaclab$ python sim_main.py --device cpu  --enable_cameras  --task Isaac-Move-Cylinder-G129-Inspire-Wholebody --enable_inspire_dds --robot_type g129


                    2. 开启状态读取
                        (tv) junweil@office-precognition:~/projects/humanoid_teleop$ python g1_realrobot/check_g1_states.py --sim --hand_type dex3 --max_freq 60

                        # 打印在command line
                            kRightShoulderPitch : q =   0.0211, dq =  -0.0107
                            kRightShoulderRoll  : q =   0.0333, dq =   0.0462
                            kRightShoulderYaw   : q =   0.0809, dq =  -0.0201
                            kRightElbow         : q =   0.0480, dq =   0.0548
                            kRightWristRoll     : q =   0.0130, dq =   0.0286
                            kRightWristPitch    : q =   0.0213, dq =   0.0205
                            kRightWristYaw      : q =   0.0256, dq =   0.0130

                            --- Left Hand (dex3) ---
                            kLeftHandThumb0     : q =  -0.0000
                            kLeftHandThumb1     : q =   0.0001
                            kLeftHandThumb2     : q =   0.0000
                            kLeftHandMiddle0    : q =  -0.0000
                            kLeftHandMiddle1    : q =  -0.0000
                            kLeftHandIndex0     : q =  -0.0000
                            kLeftHandIndex1     : q =  -0.0000

                            --- Right Hand (dex3) ---
                            kRightHandThumb0    : q =  -0.0000
                            kRightHandThumb1    : q =  -0.0001
                            kRightHandThumb2    : q =  -0.0000
                            kRightHandIndex0    : q =  -0.0000
                            kRightHandIndex1    : q =  -0.0000

                        # 加上浏览器meshcat可视化
                            # 因时手

                            (tv) junweil@office-precognition:~/projects/humanoid_teleop$ python g1_realrobot/check_g1_states.py --sim --hand_type inspire1 --max_freq 60 --urdf assets/g1/g1_body29_inspired_hand.urdf --visualize



                    3. 可以使用键盘 控制一下机器人改变一下
                        (tv) junweil@office-precognition:~/projects/unitree_sim_5.0/unitree_sim_isaaclab$ python send_commands_keyboard.py

                # 实机获取state

                    (tv) junweil@precognition-laptop6:~/projects/humanoid_teleop$ python g1_realrobot/check_g1_states.py --hand_type inspire1 --max_freq 60 --urdf assets/g1/g1_body29_inspired_hand.urdf --visualize --network enp131s0

                    # 2号机的右手肘怎么状态不对。
                        视频：https://drive.google.com/file/d/1QWdw0RAkEyE58QR3lO3y4-d6Jh0RVf4T/view?usp=drive_link


            # 以后想再unitree sim中加底层运控:
                https://github.com/unitreerobotics/unitree_sim_isaaclab/blob/main/action_provider/action_provider_wh_dds.py
                https://github.com/unitreerobotics/unitree_sim_isaaclab/issues/40

                # 他们好像 直接用isaac sim去读机器人的状态，不是用rt/这些DDS的

                # 仿真中，从Isaaclab里读机器人状态，写到DDS rt/lowstate
                    https://github.com/unitreerobotics/unitree_sim_isaaclab/blob/f56158f1a18cec783a8d0f863f2871757b8b2fe9/dds/g1_robot_dds.py#L72

    # Homie 的指令input: Vx, Vy + 转向角速度 (yaw) + 身体高度 (0.74m以下，)，4D；输出12 DoF脚 Joint Pos
        # 观测输入: 身体角速度、重力向量，全身关节位置，全身关节速度，还有上一步action
        # 文昊的Homie解释：https://github.com/precognitionlab/HomieDeploy?tab=readme-ov-file#%E6%9C%BA%E5%99%A8%E4%BA%BA%E7%8A%B6%E6%80%81%E6%95%B0%E6%8D%AE%E5%90%8E%E5%A4%84%E7%90%86
        # homie官方是要跑在Jetson PC2上的，要在Jetson上安装pytorch

            # dependencies
                pip install onnxruntime-gpu

        # 1. 先跑起来模型inference仿真测试

            # 开启仿真
                (unitree_sim5.0_env) junweil@office-precognition:~/projects/unitree_sim_5.0/unitree_sim_isaaclab$ python sim_main.py --device cpu  --enable_cameras  --task Isaac-Move-Cylinder-G129-Dex3-Wholebody --enable_dex3_dds --robot_type g129

            # 开启模型推理加可视化 actions, 好像还算合理, 腿是正常走路摆动的，设置max_freq 60 实际Hz在30-50多
                (tv) junweil@office-precognition:~/projects/humanoid_teleop$ python g1_realrobot/locomotion_model.py --model_path homie_deploy_official.onnx --urdf  assets/g1/g1_body29_hand14.urdf --no_control --sim --hand_type dex3 --max_freq 60.0

            #可以使用键盘 控制一下机器人改变一下
                (tv) junweil@office-precognition:~/projects/unitree_sim_5.0/unitree_sim_isaaclab$ python send_commands_keyboard.py

        # 2. 单独跑实机locomotion，
            # laptop5 有线连接2号机，用龙门架。跑100Hz
                # 需要安装tv环境

                # G1开机自检完成后， L2+B进入阻尼，然后L2 + R2进入调试模式，灯应该会边
                # 然后把g1的手放到前面，L2 + A会进入关节0位，然后再L2+B再次进入阻尼模式
                # 脚要触地

            # 先尝试可视化，不控制G1 (注意不加 --sim), 可以看到browser中输出的action

                ~/projects/humanoid_teleop$ python g1_realrobot/locomotion_model.py --model_path homie_deploy_official.onnx --urdf  assets/g1/g1_body29_hand14.urdf --no_control --hand_type dex3 --max_freq 50.0

                # 加--only_calibrate 只做calibrate的动作

                    ~/projects/humanoid_teleop$ python g1_realrobot/locomotion_model.py --model_path homie_deploy_official.onnx --urdf  assets/g1/g1_body29_hand14.urdf --only_calibrate --hand_type dex3 --max_freq 50.0

            # 实机跑，max_freq=100 一开始可能剧烈抖动踏步, 所以max_freq 设置为50.0,然后站稳后就不动了，可以摘掉安全绳

                ~/projects/humanoid_teleop$ python g1_realrobot/locomotion_model.py --model_path homie_deploy_official.onnx --urdf  assets/g1/g1_body29_hand14.urdf --hand_type dex3 --max_freq 50.0

        # 3. teleop关闭手臂控制，先控制 走路和高度设置
            --lock_arm
            左手squeeze_ctr 控制高度1.65- 1.2米

                # 开启运控
                    ~/projects/humanoid_teleop$ python g1_realrobot/locomotion_model.py --model_path homie_deploy_official.onnx --urdf  assets/g1/g1_body29_hand14.urdf --hand_type dex3 --max_freq 50.0


                    # 开启image server

                        (base) unitree@ubuntu:~/projects/image_server$ python3.8 image_server_timesync.py

                # 开启teleop，lock arm
                      (tv) junweil@precognition-laptop6:~/projects/xr_teleoperate/teleop$ python teleop_hand_and_arm_with_loco.py --xr-mode=controller  --arm=G1_29 --ee=dex3 --record --network_interface enp131s0  --lock_arm --task_name move_box --task_dir ../data/move_box

        # 4. teleop 同时控制手臂

            (tv) junweil@precognition-laptop6:~/projects/xr_teleoperate/teleop$ python teleop_hand_and_arm_with_loco.py --xr-mode=controller  --arm=G1_29 --ee=dex3 --record --network_interface enp131s0 --task_name move_box --task_dir ../data/move_box

        # 5. 可视化全身的data episode
            (tv) junweil@office-precognition:~/projects/humanoid_teleop$ python g1_realrobot/visualize_wbc_episodes.py ~/Downloads/data/move_box/episode_0010/data.json assets/g1/g1_body29_hand14.urdf --fps 60 --image_path ~/Downloads/data/move_box/episode_0010//colors/ --hand_type dex3
                # 视频: https://drive.google.com/drive/folders/120JGNOUmESJtJZ3OTWuyyHOllV9xOLBc?usp=drive_link

    # 10/2025 重新调试locomotion_v2, 用宇树遥控器

        # 1. 单独跑实机locomotion，
        # laptop5 有线连接2号机，用龙门架。跑100Hz
            # 需要安装tv环境

            # G1开机自检完成后， L2+B进入阻尼，然后L2 + R2进入调试模式，灯应该会边
            # 然后把g1的手放到前面，L2 + A会进入关节0位，然后再L2+B再次进入阻尼模式
            # 脚要触地

        # 先尝试可视化，不控制G1 可以看到browser中输出的action

            ~/projects/humanoid_teleop$ python g1_realrobot/locomotion_model.py --model_path homie_deploy_official.onnx --urdf  assets/g1/g1_body29_hand14.urdf --no_control --hand_type dex3 --max_freq 50.0

            # 加--only_calibrate 只做calibrate的动作

                ~/projects/humanoid_teleop$ python g1_realrobot/locomotion_model.py --model_path homie_deploy_official.onnx --urdf  assets/g1/g1_body29_hand14.urdf --only_calibrate --hand_type dex3 --max_freq 50.0

```


## 收集数据训练测试
```
    # 对比不同视觉延迟的训练测试效果？没必要，g1分发图像延迟在5ms以内

    # 使用抓红鸟数据集 812_data
        (base) junweil@ai-precog-machine1:/mnt$ tar -zcvf nvme1/junweil/812_data.tgz 812_data/
        (base) junweil@ai-precog-machine1:/mnt$ scp nvme1/junweil/812_data.tgz junweil@office.precognition.team:~/Downloads/

        (tv) junweil@office-precognition:/mnt/ssd1/junweil/embodied_ai/imitation_learning$ tar -zxvf ~/Downloads/812_data.tgz

    # repo
        (base) junweil@office-precognition:/mnt/ssd1/junweil/embodied_ai/imitation_learning$ git clone https://github.com/precognitionlab/Unitree_IL_lerobot unitree_il_lerobot_precognitionlab

        # dependency
            # 可能和之前的tv环境不太兼容的
            (tv) junweil@office-precognition:/mnt/ssd1/junweil/embodied_ai/imitation_learning/unitree_il_lerobot_precognitionlab/unitree_lerobot/lerobot$ pip install -e .

            git submodule update --init --recursive?

    # 处理数据
        (tv) junweil@office-precognition:/mnt/ssd1/junweil/embodied_ai/imitation_learning/unitree_il_lerobot_precognitionlab$ python unitree_lerobot/utils/convert_unitree_json_to_lerobot.py --raw-dir ../812_data/ --repo-id g1/grab_red_bird --robot_type Unitree_G1_Dex3

            # 处理成video?
            # 119 episode，每个七八秒，大概二十分钟搞掂

            # default path saved to

                $ ls ~/.cache/huggingface/lerobot/g1/
                grad_red_bird

    # 训练
        # 可能需要huggingface-cli login，需要下载一些与训练模型
        (tv) junweil@office-precognition:/mnt/ssd1/junweil/embodied_ai/imitation_learning/unitree_il_lerobot_precognitionlab/unitree_lerobot/lerobot$ python lerobot/scripts/train.py --dataset.repo_id=g1/grab_red_bird --policy.type=act
            # 默认用batch_size=64, 10万step，训了11小时，200step 大概一分20秒, 17GB显存, 最后loss 0.038, CPU利用率40%, GPU 100%

            # batch_size=128, 35GB显存， 200 step: 2分52秒

            # [TODO] check why L40 is slow

        # [TODO]训练优化，加tensorboard，数据集如何分割，训练同时validate，等, FP8, DDP等
            # https://github.com/huggingface/lerobot/pull/1246



```

