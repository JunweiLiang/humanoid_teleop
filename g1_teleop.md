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

### Motion Retargetting

0. 代码方法、预处理数据列表
```
    # 方法
        大部份都基于PHC:
        H2O也是基于PHC:
        HOVER 基于H2O:
    # data
        # 主要来自于
            https://github.com/JunweiLiang/humanoid_amp

        https://huggingface.co/datasets/fleaven/Retargeted_AMASS_for_robotics
            # 下载
                export HF_ENDPOINT=https://hf-mirror.com
                $ pip install huggingface_hub[hf_transfer]
                $ huggingface-cli download fleaven/Retargeted_AMASS_for_robotics --repo-type dataset --local-dir ./Retargeted_AMASS_for_robotics_data

        https://huggingface.co/datasets/ember-lab-berkeley/AMASS_Retargeted_for_G1

        https://huggingface.co/datasets/lvhaidong/LAFAN1_Retargeting_Dataset


```

1. Download and visualize AMASS
```
    # 参考
        https://github.com/NVlabs/HOVER/?tab=readme-ov-file#data-processing
        https://github.com/LeCAR-Lab/human2humanoid?tab=readme-ov-file#amass-dataset-preparation

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
