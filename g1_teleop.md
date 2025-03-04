# note on getting teleop G1 to work


### Use H2O

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
```

2. Retarget AMASS for G1
```
```
