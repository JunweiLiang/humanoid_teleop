
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
