### Note on Visuaizing and Replaying TeleOperation Episode

### Install
```
    # Some known dependancies
    $ conda create -n tv python=3.10 pinocchio=3.1.0 numpy=1.26.4 -c conda-forge
    $ pip install numpy==1.26.4 opencv-python==4.10.0.84
    $ pip install meshcat
```

### Replay TeleOp Episodes
See example video [here](../teleop_replay_example.mp4)
```
    # for dex3 hand G1, suppose the data is collected using Unitree's JSON format, and a single view RGB

    (tv) $ python g1_realrobot/visualize_arm_episodes.py episode_24/data.json assets/g1/g1_body29_hand14.urdf --fps 60 --image_path episode_24/colors/ --hand_type dex3
```
