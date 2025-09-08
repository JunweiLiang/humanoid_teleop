## Put G1 PC2 Jetson Image (ROS1/2, ubuntu 20.04) into a new disk
```
    # ROS1 只支持到Ubuntu 20.04
    # 宇树的PC2有ROS1 +  ROS2
        # https://support.unitree.com/home/zh/G1_developer/FAQ
        # 百度网盘花了9.9下载
        # m3, m12, m13都存了副本
            junweiliang@work_laptop:~/Downloads$ scp /Users/junweiliang/Downloads/nx.img.bz2 junweil@office.precognition.team:~/Downloads/

            junweiliang@work_laptop:~/Downloads$ scp kernel_tegra234-p3767-0000-p3768-0000-a0.dtb junweil@office.precognition.team:~/Downloads/

            # 设备树文件，是给G1 PC2的，应该是启动的时候，让linux知道有哪些I/O之类的

        # 镜像250多个G，要买个nvme 1TB放jetson nano
        $ sudo umount /dev/sde*
        (base) junweil@office-precognition:~/Downloads$ bzip2 -dc nx.img.bz2 | pv | wc -c | numfmt --to=iec-i --suffix=B
         238GiB 0:26:22 [ 154MiB/s] [                               <=>                                                              ]
        239GiB

            # nvme读卡器，1TB的，速度：24 MB/s还会不断降速, 3 小时-4小时?

        $ sync
```
