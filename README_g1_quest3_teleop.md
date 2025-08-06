## Note to run TeleOperation using Quest 3 with or without controller on G1

### Quest 3对比AVP方案的优点
+ 不需要证书配置，任意电脑都可以方便做teleop服务器， 在校园网里也可以
+ 有controller，可以戴着VR开始结束遥操作，可以原地控制机器人移动
+ 可以戴眼镜佩戴
+ 便宜10倍
+ 缺点：可能手的姿态识别没那么准，显示没有AVP高清容易头晕


### 修改记录
+ (08/2025) 在宇树官方代码基础上，添加了controller控制5指手、3指手，可一人实现遥操作；去掉了仿真中的手腕相机，只用头部
+ Quest 3 按键说明: 右手A结束遥操作程序，右手B开始遥操作程序，左手X开始结束EP录制，板机按压下程度对应手关闭程度
+ dex3开合程度修改`xr_teleoperate/teleop/robot_control/robot_hand_unitree.py`，手关闭[图示](./g1_hand14_close.png)，手打开[图示](./g1_hand14_open.png)
+ inspire1开合程度修改`xr_teleoperate/teleop/robot_control/robot_hand_inspire.py`，手关闭[图示](./g1_inspire_close.png)，手打开[图示](./g1_inspire_open.png)
+ (TODO) 添加controller结合locomotion，实现whole-body control遥操作

### 环境安装

需要两个代码库 \[TODO\]: 换到实验室的org下方便大家一起编辑更新
+ 主要代码: `https://github.com/JunweiLiang/xr_teleoperate`
+ EP快速可视化工具等: `https://github.com/JunweiLiang/humanoid_teleop`

0. Quest 3初次配置
```
    # 第一次使用必须要Meta Horizon App，梁老师用iPad搞了个美国区Apple ID，终于可以下载这个app了

        # quest 3 按电源 + 音量变小 按键，可以恢复出厂

    # 第一次setup 需要联网更新，用梁老师的iphone 5G做wifi热点，可以连外网；更新10分钟左右，重启一次。
        # 然后要用Meta Horizon APP配置

    # Meta Quest 3 连接学校wifi HKUST(GZ)  需要选择PEAP, M**v2, 然后选择use system certificate, 域名输入nce.hkust-gz.edu.cn, identity输入用户名，匿名框留空，然后输入密码，即可。
```

0. 用mujoco查看URDF，可以看各种joint名称与弧度限制
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

1. 安装遥操作环境，仿真测试环境，episode 重看环境
```
    # 安装遥操作环境叫tv
    $ git clone https://github.com/JunweiLiang/xr_teleoperate
    $ conda create -n tv python=3.10 pinocchio=3.1.0 numpy=1.26.4 -c conda-forge

    xr_teleoperate/teleop/televuer$ pip install -e .
    xr_teleoperate/teleop/televuer$ openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout key.pem -out cert.pem

    xr_teleoperate/robot_control/dex-retargeting$ pip install -e .

    xr_teleoperate/unitree_sdk2_python$ pip install -e .

    xr_teleoperate$ pip install -r requirements.txt

    # 安装仿真测试环境叫unitree_sim_env
    $ conda create -n unitree_sim_env python=3.10
    $ pip install torch==2.7.0 torchvision==0.22.0 --index-url https://download.pytorch.org/whl/cu128 --extra-index-url https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple

    $ pip install 'isaacsim[all,extscache]==4.5.0' --extra-index-url https://pypi.nvidia.com

    # IsaacLab还要装一下
    xr_teleoperate$ git clone https://github.com/isaac-sim/IsaacLab
    xr_teleoperate/IsaacLab$ ./isaaclab.sh --install

    xr_teleoperate/unitree_sim_isaaclab$ pip install -r requirements.txt

    xr_teleoperate/unitree_sdk2_python$ pip install -e .

    # episode 重看环境叫g1
    $ conda create -n g1 python=3.10 pinocchio=3.1.0 numpy=1.26.4 -c conda-forge
    $ pip install meshcat
    $ pip install casadi
```

2. 用仿真验证遥操作
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

3. 实机验证遥操作
```
```
