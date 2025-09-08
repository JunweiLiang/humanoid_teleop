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

        # 然后插入到G1背板上的nvme，重启设备后，ssh unitree@192.168.123.18 可以连接
            # nvme盘只有200GB可用空间，需要这样扩容：https://support.unitree.com/home/zh/G1_developer/FAQ
        # 复制设备树
            unitree@ubuntu:~$ sudo cp kernel_tegra234-p3767-0000-p3768-0000-a0.dtb /boot/dtb/ -r

        # 把IP弄回到164
            $ sudo vi /etc/netplan/01-network-cfg.yaml
            :set paste
            i
network:
  version: 2
  renderer: networkd
  ethernets:
    eth0:
      dhcp4: no
      addresses:
        - 192.168.123.164/24
      routes:
        - to: default
          via: 192.168.123.1
      nameservers:
        addresses: [8.8.8.8, 1.1.1.1]
            然后保存
            $ sudo netplan apply

        # 安装wifi驱动
            # 需要连外网，apt install一些东西

            # 再安装
            junweiliang@work_laptop:~$ scp Downloads/rtl8852bu-dkms_1.19.14_arm64.deb junweil@lt5.precognition.team:~/Downloads/
            (base) junweil@lt5:~$ scp Downloads/rtl8852bu-dkms_1.19.14_arm64.deb unitree@192.168.123.164:~/


        # 宇树官方一般用 nomachine 可视化连接PC2

        # PC2一开始默认wifi驱动没有。需要安装：
            # https://github.com/morrownr/rtl8852bu-20240418用这里面的方法装也行
            # 不用dpkg了
```
