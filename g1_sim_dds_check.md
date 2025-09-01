## 仿真中开启宇树DDS然后获取状态
+ 实现效果：Sim中跑宇树运控，pin/meshcat可视化读取到的状态: [dex3](https://drive.google.com/file/d/1azKWRwq-ApD4E_hA0MjAKqBg_QR5yuz6/view?usp=drive_link), [因时](https://drive.google.com/file/d/1OkjY6kyPn0A8_i2puokOvYh_r_st5-PM/view?usp=drive_link)
```
    # [08/28/2025] 使用宇树最新的 Isaac lab 环境，看看DDS的话题发布如何
    # 需要安装环境Sim 5.0：
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

        # 1. 下载模型！！

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


        # 以后想再unitree sim中加底层运控:
            https://github.com/unitreerobotics/unitree_sim_isaaclab/blob/main/action_provider/action_provider_wh_dds.py
            https://github.com/unitreerobotics/unitree_sim_isaaclab/issues/40

            # 他们好像 直接用isaac sim去读机器人的状态，不是用rt/这些DDS的

            # 仿真中，从Isaaclab里读机器人状态，写到DDS rt/lowstate
                https://github.com/unitreerobotics/unitree_sim_isaaclab/blob/f56158f1a18cec783a8d0f863f2871757b8b2fe9/dds/g1_robot_dds.py#L72
```
