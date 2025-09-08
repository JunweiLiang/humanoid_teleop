# note on the whole ASR - VLM - TTS Agent

### [06/2025] 摄像头麦克风扬声器一体机测试
+ 代码流程逻辑图 [start_vlm_speech_g1_agent_v3.py](./vlm_speech_agent_pipeline_v3.drawio.png)
```
    # 硬件：摄像头、麦克风、扬声器一体机:
        【淘宝】https://e.tb.cn/h.6VsKYN9TxryaLUI?tk=kqu0eDgCv2j CA381 「台式电脑外置摄像头超清4K音响麦克风一体笔记本考研会议网课直播」
    # 或者笔记本电脑自带的应该也可以

        $ conda activate asr

        (asr) junweil@home-lab:~/projects/asr/MLLMs$ python start_vlm_speech_g1_agent_v3.py --cam_num 0 --mic_id 0 --speaker_id 0 --api_url_port m10.precognition.team:8888 --tts_model_path ../CosyVoice/pretrained_models/CosyVoice2-0.5B --prompt_audio_path test_audio/laopo2.wav --tts_voice_type 4 --show_video --fps 30 --h 720 --w 1280 --asr_thres 0.6


```

### 4090笔记本安装 - [想要在自己机器部署看这里，主要是 TTS需要6GB显存]
```
        (base) junweil@precognition-laptop4:~/projects/asr$ git clone https://github.com/JunweiLiang/MLLMs

        $ conda create -n asr python=3.10


        (asr) junweil@precognition-laptop4:~/projects/asr/MLLMs/streaming_sensevoice$ pip install -r requirements.txt
        (asr) junweil@precognition-laptop4:~/projects/asr/MLLMs/streaming_sensevoice$ pip install -r requirements-ws-demo.txt
        $ conda install -y -c conda-forge pynini==2.1.5
        $ conda install -c nvidia cuda-compiler==12.1
        $ pip install pygame

        $ wget https://pypi.nvidia.com/tensorrt-cu12-libs/tensorrt_cu12_libs-10.0.1-py2.py3-none-manylinux_2_17_x86_64.whl#sha256=ad3b0af25d8b9f215ff877d6f565afbd084728294a1ee16c3b7f7729dcbfdff4
        $ pip install tensorrt_cu12_libs-10.0.1-py2.py3-none-manylinux_2_17_x86_64.whl

        (asr) junweil@precognition-laptop4:~/projects/asr/MLLMs/cosyvoice$ pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host=mirrors.aliyun.com

            # 下载模型 TTS/ASR
            (asr) junweil@precognition-laptop4:~/projects/asr/MLLM
            >>> from modelscope import snapshot_download
            >>> snapshot_download('iic/CosyVoice2-0.5B', local_dir='pretrained_models/CosyVoice2-0.5B')
            >>> snapshot_download('iic/SenseVoiceSmall', local_dir='pretrained_models/SenseVoiceSmall')

            # more dependancies
                $ sudo apt-get install libportaudio2
                $ sudo apt install ffmpeg
                $ pip install opencv-python openai

                # 解决： OSError: cannot load library 'libportaudio.so.2': /home/junweil/anaconda3/envs/asr/bin/../lib/libstdc++.so.6: version `GLIBCXX_3.4.32' not found (required by /lib/x86_64-linux-gnu/libjack.so.0)

                    (asr) junweil@precognition-laptop4:~/projects/asr/MLLMs$ cd ~/anaconda3/envs/asr/lib
                    (asr) junweil@precognition-laptop4:~/anaconda3/envs/asr/lib$ cp /usr/lib/x86_64-linux-gnu/libstdc++.so.6.0.33 .
                    (asr) junweil@precognition-laptop4:~/anaconda3/envs/asr/lib$ rm libstdc++.so.6
                    (asr) junweil@precognition-laptop4:~/anaconda3/envs/asr/lib$ ln -s libstdc++.so.6.0.33 libstdc++.so.6

        # [06/2025]用vllm, TTS加速很多
            # 复制原本环境，再安装vllm==v0.9
            $ conda create -n asr_vllm --clone asr
            $ pip install vllm==v0.9.0 -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host=mirrors.aliyun.com

            # 注意这个模型跟之前的不一样，需要用 CosyVoice/pretrained_models/CosyVoice2-0.5B
```

### [05/22/2025] 用2x4090 48GB 挂32B模型
```
    # 安装vllm

        (base) junweil@ai-precog-machine11:~$ conda create -n vllm python=3.12 -y
        conda activate vllm
        pip install vllm
            # 安装了 vllm==0.8.5.post1, torch==2.6.0, cuda==12.4

    # get 32B model

        (base) junweil@ai-precog-machine11:/mnt/ssd1/junweil/vlm$ scp -r junweil@10.13.3.209:/mnt/nvme2/junweil/deepseek/Qwen2.5-VL-32B-Instruct .

    # Run!
        # FP8 32B
        # takes 40GB/48GB memory
        (vllm) junweil@ai-precog-machine11:/mnt/ssd1/junweil/vlm$ CUDA_VISIBLE_DEVICES=2,3 vllm serve Qwen2.5-VL-32B-Instruct/ --port 8888 --host 0.0.0.0 --limit-mm-per-prompt image=30,video=0 --max-model-len 65536 --gpu-memory-utilization 0.85 --tensor-parallel-size 2 --max_num_seqs 16 --dtype bfloat16 --chat-template MLLMs/chat_template_byjunwei.jinja --quantization fp8

    # eval
        pip install evalscope[perf] -U
        pip install gradio

        [这个4090限制了350/450w功率]
        (vllm) junweil@ai-precog-machine11:~$ evalscope perf  --url "http://127.0.0.1:8888/v1/chat/completions" --number 20 --api openai --dataset openqa  --stream --model Qwen2.5-VL-32B-Instruct/ --parallel 1
             # 1 个并行请求
                # Time-To-First-Token 99% 0.0583 second, Throughput 41 token/s，总平均Throughput 41 token/s
            # 10 个并行请求
                # Time-To-First-Token 99% 0.1192 second, Throughput 27 - 34 token/s，总平均Throughput 192.55 token/s
```
### [06/2025] TTS用vllm v0.9 跑，加速
```
    copy CosyVoice/cosyvoice到 large_models/cosyvoice_vllm
        # change all the from cosyvoice. to from cosyvoice_vllm. in all the code

        # also need to change the yaml for the model path

            (asr_vllm) junweil@home-lab:~/projects/asr/MLLMs$ cp cosyvoice_vllm/cosyvoice2_vllm.yaml ../CosyVoice/pretrained_models/CosyVoice2-0.5B/

        # 备份这个模型
            (asr) junweil@home-lab:~/projects/asr/CosyVoice/pretrained_models$ tar -zcvf CosyVoice2-0.5B.tgz CosyVoice2-0.5B/
            (asr) junweil@home-lab:~/projects/asr$ mv CosyVoice2-0.5B.tgz CosyVoice2-0.5B-vllm-062025.tgz

    # 复制原本环境，再安装vllm==v0.9
        $ conda create -n asr_vllm --clone asr
        $ pip install vllm==v0.9.0 -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host=mirrors.aliyun.com

        # 注意这个模型跟之前的不一样，需要用 CosyVoice/pretrained_models/CosyVoice2-0.5B

    # 测试速度对比，都用asr_vllm环境
        # 好像有onnx报错，没事; # 记录第三次生成

            (asr_vllm) junweil@home-lab:~/projects/asr/MLLMs$ python test_cosyvoice_laopo.py

                2025-06-11 16:00:40,570 INFO synthesis text 收到好友从远方寄来的生日礼物，那份意外的惊喜与深深的祝福让我心中充满了甜蜜的快乐，笑容如花儿般绽放。
                2025-06-11 16:00:45,576 INFO yield speech len 10.32, rtf 0.6512656923412352
                0
                took 6.758 seconds
                2025-06-11 16:00:55,975 INFO synthesis text 收到好友从远方寄来的生日礼物，那份意外的惊喜与深深的祝福让我心中充满了甜蜜的快乐，笑容如花儿般绽放。
                2025-06-11 16:01:00,998 INFO yield speech len 10.36, rtf 0.48495800338656747
                0
                took 5.043 seconds


            (asr_vllm) junweil@home-lab:~/projects/asr/MLLMs$ python test_cosyvoice_laopo_vllm.py

                2025-06-11 16:56:23,796 INFO synthesis text 收到好友从远方寄来的生日礼物，那份意外的惊喜与深深的祝福让我心中充满了甜蜜的快乐，笑容如花儿般绽放。
                2025-06-11 16:56:25,642 INFO yield speech len 10.84, rtf 0.17022969977882077
                0
                took 3.658 seconds
                2025-06-11 16:56:36,547 INFO synthesis text 收到好友从远方寄来的生日礼物，那份意外的惊喜与深深的祝福让我心中充满了甜蜜的快乐，笑容如花儿般绽放。
                2025-06-11 16:56:38,388 INFO yield speech len 10.76, rtf 0.1712249557324945
                0
                took 1.866 seconds

                # vllm快很多！！！

    # 用large_models的代码挂 模型, m10
        (cosyvoice_vllm) junweil@ai-precog-machine10:~/projects$ git clone https://github.com/JunweiLiang/MLLMs
        (cosyvoice_vllm) junweil@ai-precog-machine10:~/projects/MLLMs$ cp cosyvoice_vllm/cosyvoice2_vllm.yaml ../CosyVoice/pretrained_models/CosyVoice2-0.5B/

        # put it on the same card as the Qwen2.5-VL
        (cosyvoice_vllm) junweil@ai-precog-machine10:~/projects/MLLMs$ CUDA_VISIBLE_DEVICES=3 python cosyvoice_server_vllm_junwei.py --port 50000 --model_dir ../CosyVoice/pretrained_models/CosyVoice2-0.5B/ --gpu_memory_utilization 0.1 --voice_type 4 --prompt_audio_path ./test_audio/laopo2.wav

    # home-lab call


        (asr_vllm) junweil@home-lab:~/projects/asr/MLLMs$ python cosyvoice_client_vllm_junwei_speak.py --host m10.precognition.team --port 50000 --tts_text "收到好友从 远方寄来的生日礼物，那份意外的惊喜与深深的祝福让我心中充满了甜蜜的快 乐，笑容如 花儿般绽放。"

        took 1.749 seconds

```
### [05/2025] 测试语音生成与语音识别硬件, 以及打断词
```
    1. 原版语音、扬声器一体机，生成一段语音然后看识别到的语音

        (asr) junweil@home-lab:~/projects/asr/MLLMs$ python test_tts_asr.py --mic_id 0 --speaker_id 0 --tts_model_path ../CosyVoice/pretrained_models/CosyVoice2-0.5B --prompt_audio_path test_audio/laopo2.wav --tts_voice_type 4 --asr_thres 0.6

        # 好像摄像头麦克风一体本身就能降噪音。自己TTS不会ASR到。但是，在TTS的时候，再人讲话，就会confuse，识别效果差

            [2025-05-27 20:30:29] [ASRAgent-处理文本]: 测试一次。
            [2025-05-27 20:30:35] [ASRAgent-处理文本]: 测试语音生成。
            [2025-05-27 20:30:35] [ASRAgent-再让TTS说一次]
            [2025-05-27 20:30:35]   [TTSAgent-开始生成]: 我已经接入了大模型，可以识别、操作物体，也可以理解人类的指令、。
            [2025-05-27 20:30:44]   [TTSAgent-生成完成]
            [2025-05-27 20:30:53] [ASRAgent-处理文本]: 测试语音生成。
            [2025-05-27 20:30:53] [ASRAgent-再让TTS说一次]
            [2025-05-27 20:30:53]   [TTSAgent-开始生成]: 我已经接入了大模型，可以识别、操作物体，也可以理解人类的指令、。
            [2025-05-27 20:30:57] [ASRAgent-处理文本]: 你听见我说话吗？我已经接。
            [2025-05-27 20:30:59] [ASRAgent-处理文本]: 模型可以。
            [2025-05-27 20:31:01]   [TTSAgent-生成完成]

    2. 接上蓝牙会议扬声器麦克风一体机，另外一端蓝牙接收器usb连接电脑
        # 淘宝 【淘宝】https://e.tb.cn/h.6w6e5mawwKluUg8?tk=InbrVm6hJON CZ028 「联想thinkplus音视频会议全向麦克风免驱蓝牙降噪MK-MC600」

        # 直接同样上述的 mic_id 0 speaker_id 0可以使用

        # 似乎在TTS的过程中，ASR效果更好

            [2025-05-28 09:41:40] [ASRAgent-处理文本]: 测试语音生成。
            [2025-05-28 09:41:40] [ASRAgent-再让TTS说一次]
            [2025-05-28 09:41:40]   [TTSAgent-开始生成]: 你好，欢迎来到港科大广州具身智能实验室，我是实验室打工机器人一号、，
                                    我已经接入了大模型，可以识别、操作物体，也可以理解人类的指令、。
            [2025-05-28 09:41:45] [ASRAgent-处理文本]: 可以听到我说话吗？
            [2025-05-28 09:41:52] [ASRAgent-处理文本]: 话吗？
            [2025-05-28 09:41:52] [ASRAgent-跳过短文本]: 话吗？
            [2025-05-28 09:41:55] [ASRAgent-处理文本]: 到我说话吗？
            [2025-05-28 09:41:58] [ASRAgent-处理文本]: 好。
            [2025-05-28 09:41:58] [ASRAgent-跳过短文本]: 好。
            [2025-05-28 09:41:59]   [TTSAgent-生成完成]

        # TTS过程中，ASR不会混入TTS 的文字，但是会丢失很多词语。要“小明小明小明”才能识别到“小明小明”打断， 说“小明小明”只能识别到“明小明”

            [2025-05-28 09:43:16]   [TTSAgent-开始生成]: 你好，欢迎来到港科大广州具身智能实验室，我是实验室打工机器人一号、，
                        我已经接入了大模型，可以识别、操作物体，也可以理解人类的指令、。
            [2025-05-28 09:43:28] [ASRAgent-处理文本]: 明小明。
            [2025-05-28 09:43:31] [ASRAgent-识别到打断词]
            [2025-05-28 09:43:31]   [TTSAgent-收到stop_and_empty发声队列指令]
            [2025-05-28 09:43:31] [ASRAgent-已发送TTS agent停止指令]
            [2025-05-28 09:43:32]   [TTSAgent-生成完成]
            [2025-05-28 09:43:32] [ASRAgent-处理文本]: 你。
            [2025-05-28 09:43:32] [ASRAgent-跳过短文本]: 你。
            [2025-05-28 09:43:43] [ASRAgent-处理文本]: 以听到我说话吗？
            [2025-05-28 09:43:47] [ASRAgent-处理文本]: 测试语音生成。
            [2025-05-28 09:43:47] [ASRAgent-再让TTS说一次]
            [2025-05-28 09:43:47]   [TTSAgent-开始生成]: 你好，欢迎来到港科大广州具身智能实验室，我是实验室打工机器人一号、，
                                    我已经接入了大模型，可以识别、操作物体，也可以理解人类的指令、。
            [2025-05-28 09:44:07]   [TTSAgent-生成完成]

        # 麦克风还是用别的比较好

```
### [06/13/2025] fixed 打断词，RGB视觉都用zmq发送
```
    # 打断词修复了,sounddevice需要用OutputStream控制
        # v5 不用打断词也可以打断，说新的指令就好
        # 打断词，语音生成过程中识别到这个会打断生成，重启ASR
        # 语音生成中，说别的话也会打断，但是这个别的话也会发送给VLA，G1会有所回应，
        # 比如问“我应该喝牛奶还是咖啡”，回答中，你说“我就是要喝咖啡”， G1会继续回应
        # 打断词的话就会直接终止

        # 只用start_vlm_speech_g1_agent_v5_zmq_tts_api.py了，要zmq启动视觉，TTS用api
            # 或者TTS本地：start_vlm_speech_g1_agent_v5_zmq.py
            # 非zmq的代码不改了

    # 先zmq 分发 RGB
        (asr_vllm) junweil@home-lab:~/projects/asr/MLLMs$ python3 rgb_zmq_publisher.py --fps 10 --h 720 --w 1280 --cam_num 0 --port 5555

        # 语音TTS，用L40挂，默认打开quantization=fp8  (cosyvoice_vllm/cli/model.py - cosyvoice.py); model weight确实能减半，本来0.7, 现在0.36GB

    # tts api 测试通过
        (asr_vllm) junweil@home-lab:~/projects/asr/MLLMs$ python start_vlm_speech_g1_agent_v5_zmq_tts_api.py --cam_num 0 --mic_id 0 --speaker_id 0 --api_url_port m10.precognition.team:8888 --tts_api_url_port m10.precognition.team:50000 --show_video --display_fps_limit 60 --h 720 --w 1280 --asr_thres 0.6 --publisher_ip 127.0.0.1 --publisher_port 5555

        # 基本第一句话2秒内生成

    # 本地tts
        (asr_vllm) junweil@home-lab:~/projects/asr/MLLMs$ python start_vlm_speech_g1_agent_v5_zmq.py --cam_num 0 --mic_id 0 --speaker_id 0 --api_url_port m10.precognition.team:8888 --tts_model_path ../CosyVoice/pretrained_models/CosyVoice2-0.5B --prompt_audio_path test_audio/laopo2.wav --tts_voice_type 4 --show_video --display_fps_limit 60 --h 720 --w 1280 --asr_thres 0.6 --publisher_ip 127.0.0.1 --publisher_port 5555

        # good! 可以通过打断词或者说别的话打断

```
### [06/14/2025] G1实机测试
```
    1. 有线网线连接
        laptop4 本地TTS, quantization fp8
        # [TODO] 再测试一下4090 laptop 本地vllm
                # quantization=fp8了

            # 还是不行
                    [06/14/2025-10:24:25] [TRT] [E] 2: [engine.cpp::deserializeEngine::1312] Error Code 2: Internal Error (Assertion engine->deserialize(start, size, allocator, runtime) failed. )

        # 记得laptop4 有线网络选择 g1-wired-222
        # 1 号机PC 2需要一个conda env
            $ conda create -n zmq python=3.8
            $ conda activate zmq
            (zmq) unitree@ubuntu:~$ pip install pyzmq pygame

        # 1号机开zmq

            (zmq) unitree@ubuntu:~/projects/MLLMs$ python3 rgb_zmq_publisher.py --fps 2 --h 720 --w 1280 --cam_num 0 --port 5555

        # zmq, TTS API

            (asr_vllm) junweil@precognition-laptop4:~/projects/asr/MLLMs$ python start_vlm_speech_g1_agent_v5_zmq_tts_api.py --cam_num 0 --mic_id 0 --speaker_id 0 --api_url_port m10.precognition.team:8888 --tts_api_url_port m10.precognition.team:50000 --show_video --display_fps_limit 60 --h 720 --w 1280 --asr_thres 0.6 --publisher_ip 192.168.123.164 --publisher_port 5555 --enable_g1

            # zmq 延迟190ms , 5 FPS

            # [06/14/2025] 2号机，测试中间，可能会断网，可能是PC2 Jetson挂了？重启G1后正常
                # ping 161 PC1和120 激光雷达都可以，是PC2挂了
                # zmq pub 2 FPS就没问题，不要用5 FPS


    2. 无线wifi连接

        # 1. 把移动电源接上无线路由器接到G1，laptop4有线接上校园网
            # laptop4 无线网络连接上G1无线路由器precognition-glnet-wifi7-5G

        # 先确定本机连接G1无线网络的名称 ifconfig
            wlp59s0f0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500
            inet 192.168.123.249

            # 代码命令几乎一样
            (asr_vllm) junweil@precognition-laptop4:~/projects/asr/MLLMs$ python start_vlm_speech_g1_agent_v5_zmq_tts_api.py --cam_num 0 --mic_id 0 --speaker_id 0 --api_url_port m10.precognition.team:8888 --tts_api_url_port m10.precognition.team:50000 --show_video --display_fps_limit 60 --h 720 --w 1280 --asr_thres 0.6 --publisher_ip 192.168.123.164 --publisher_port 5555 --enable_g1 --g1_network wlp59s0f0

            # zmq 延迟340ms , 5 FPS
            # zmq 延迟100ms-250ms , 2 FPS

            # 发现转身这个动作延迟很高，还可能转一下，等一会，然后再转

    # 推荐测试序列

        # 请和大家打个招呼挥挥手吧
            # 请转身和大家挥挥手打个招呼吧

        # 请用两句话简单赞美一下你看到的人
        # 请往前走几步
        # 请和领导握个手吧

        # 我晚上有点困了，请问我应该喝哪一个？
            # 我就是想要喝咖啡 （打断）

        # [拿起创可贴]请问这是什么，儿童可以使用吗？

    # 如果G1的jetson不稳定，直接usb接RGB相机，有线网线连接G1，在笔记本上用zmq本地分发RGB，还可以继续使用v5_zmq_tts_api.py

```
### 2x4090 48 GB 450w 电脑安装测试
```
    4. 测试agent (双卡4090 48GB)

        # 挂32B VLM，需要留GPU mem给语音生成. So 0.7

            (asr_vllm) junweil@office-precognition:/mnt/ssd2/junweil/deepseek$ vllm serve Qwen2.5-VL-32B-Instruct/ --port 8888 --host 0.0.0.0 --limit-mm-per-prompt image=30,video=0 --max-model-len 65536 --gpu-memory-utilization 0.7 --tensor-parallel-size 2 --max_num_seqs 16 --dtype bfloat16 --chat-template ~/projects/asr/MLLMs/chat_template_byjunwei.jinja --quantization fp8

            # 32.9 GB / 47.99 GB
                和0.85 相比，token延迟差不多

        # 开TTS server

            (asr_vllm) junweil@office-precognition:~/projects/asr/MLLMs$ CUDA_VISIBLE_DEVICES=1 python cosyvoice_server_vllm_junwei.py --port 50000 --model_dir ../CosyVoice/pretrained_models/CosyVoice2-0.5B/ --gpu_memory_utilization 0.1 --voice_type 4 --prompt_audio_path ./test_audio/laopo2.wav

            # 38.98 GB / 47.99 GB

            # 测试TTS server
                (asr_vllm) junweil@office-precognition:~/projects/asr/MLLMs$ python cosyvoice_client_vllm_junwei_speak.py --host 127.0.0.1 --port 50000 --tts_text "收到好友从 远方寄来的生日礼物，那份意外的惊喜与深深的祝福让我心中充满了甜蜜的快 乐，笑容如 花儿般绽放。"

                1.8s - 2.0s

        # 开zmq publisher
            (asr_vllm) junweil@office-precognition:~/projects/asr/MLLMs$ python3 rgb_zmq_publisher.py --fps 10 --h 720 --w 1280 --cam_num 0 --port 5555

                # 本地延迟30ms内

        # 开agent!

            (asr_vllm) junweil@office-precognition:~/projects/asr/MLLMs$ python start_vlm_speech_g1_agent_v5_zmq_tts_api.py --cam_num 0 --mic_id 0 --speaker_id 0 --api_url_port 127.0.0.1:8888 --tts_api_url_port 127.0.0.1:50000 --show_video --display_fps_limit 60 --h 720 --w 1280 --asr_thres 0.6 --publisher_ip 127.0.0.1 --publisher_port 5555

                # 第一次运行会自动下载sensevoice model
                    Downloading Model from https://www.modelscope.cn to directory: /home/junweil/.cache/modelscope/hub/models/iic/SenseVoiceSmall

                # ASR不能开denoise=True，用的麦克风扬声器一体机
                # 偶尔ASR还会识别到回音

                [2025-06-20 11:06:36] [ASRAgent-处理文本]: 这个是什么手势？
                [2025-06-20 11:06:36] [ASRAgent-发送vla_agent]: 这个是什么手势？
                [2025-06-20 11:06:36]   [TTSAgent-Received stop_and_empty command. Text queue cleared.]
                [2025-06-20 11:06:36]   [TTSAgent-No active audio stream to stop.]
                [2025-06-20 11:06:36] [ASRAgent-已发送TTS agent停止指令]
                [2025-06-20 11:06:37] [VLAAgent-发送message]: 8/2 轮对话
                [2025-06-20 11:06:40] [---Latency] ASR done to VLM Inference done: 3.574 seconds
                [2025-06-20 11:06:40] [VLAAgent-收到response并发送TTSAgent]:


                这是一个“V”字手势，通常表示和平或胜利的标志。手指比出“V”形，手掌朝向镜头。这种手势在全球范围内被广泛使用，具有多种含义，但在不同的文化中可能会有不同的解释。

                如果你需要进一步的帮助，请告诉我！

                [2025-06-20 11:06:40]   [TTSAgent-开始生成]: 这是一个“V”字手势，通常表示和平或胜利的标志。
                [2025-06-20 11:06:41]   [---Latency][TTSAgent-TTS time: 1.349 seconds]

                # 比L40还是慢40%

```

### 在5090 笔记本安装用API的版本，仅需本地跑ASR
```
    (base) junweil@precognition-laptop5:~/projects$ git clone https://github.com/JunweiLiang/MLLMs

    # 安装dependencies

        $ conda create -n agent_api python=3.10

        (agent_api) junweil@precognition-laptop5:~/projects/MLLMs/streaming_sensevoice$ pip install -r requirements.txt; pip install -r requirements-ws-demo.txt

        pip install pygame pyzmq opencv-python openai

        # 5090显卡必须要这个, 重装torch==2.7.0+cu128
        $ pip uninstall torchaudio torch torchvision torchaudio-nightly torch-nightly torchvision-nightly
        $ (agent_api) junweil@precognition-laptop5:~/projects/MLLMs$ pip install torch==2.7.0 torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128

        sudo apt-get install sox libsox-dev
        sudo apt install build-essential
        sudo apt-get install libportaudio2
        sudo apt install ffmpeg

        # 安装G1 API

            (asr) junweil@precognition-laptop4:~/projects/asr$ git clone https://github.com/eclipse-cyclonedds/cyclonedds
            cyclonedds$ git checkout 0.10.2
            cyclonedds/build$ cmake ..
            cyclonedds/build$ cmake --build .
            cyclonedds/build$ sudo cmake --build . --target install

            export CYCLONEDDS_HOME=/usr/local/

            (asr) junweil@precognition-laptop4:~/projects/asr$ git clone https://github.com/unitreerobotics/unitree_sdk2_python

            unitree_sdk2_python$ pip3 install -e .

            # 测试G1 API, 有线接上G1，手动设置电脑IP 192.168.123.2xx

                $ python ../unitree_sdk2_python/example/g1/high_level/g1_loco_client_example.py enp58s0

        # 报错
            OSError: cannot load library 'libportaudio.so.2': /home/junweil/anaconda3/envs/agent_api/bin/../lib/libstdc++.so.6: version `GLIBCXX_3.4.32' not found (required by /lib/x86_64-linux-gnu/libjack.so.0)

            # 解决
                (agent_api) junweil@precognition-laptop5:~/projects/MLLMs$ cd ~/anaconda3/envs/agent_api/lib/
                (agent_api) junweil@precognition-laptop5:~/anaconda3/envs/agent_api/lib$ cp /usr/lib/x86_64-linux-gnu/libstdc++.so.6.0.33 .
                (agent_api) junweil@precognition-laptop5:~/anaconda3/envs/agent_api/lib$ rm libstdc++.so.6
                (agent_api) junweil@precognition-laptop5:~/anaconda3/envs/agent_api/lib$ ln -s libstdc++.so.6.0.33 libstdc++.so.6
        # 报错
            File "/home/junweil/anaconda3/envs/agent_api/lib/python3.10/site-packages/pysilero/pysilero.py", line 22, in <module>
                from frame_queue import FrameQueue
            ModuleNotFoundError: No module named 'frame_queue'

            # 需要改一下代码的相对引用 (注意更换自己代码位置)

                $ vi /home/junweil/anaconda3/envs/agent_api/lib/python3.10/site-packages/pysilero/pysilero.py

                from .frame_queue import FrameQueue
                from .pickable_session import silero_vad
                from .utils import get_energy

    # 测试TTS server
        (asr_vllm) junweil@home-lab:~/projects/asr/MLLMs$ python cosyvoice_client_vllm_junwei_speak.py --host m10.precognition.team --port 50000 --tts_text "收到好友从 远方寄来的生日礼物，那份意外的惊喜与深深的祝福让我心中充满了甜蜜的快 乐，笑容如 花儿般绽放。"

        # # 06/2025 换成用sounddevice.OutputStream才能发音
        # 这个测试能正常通过、看到took xx seconds就行

    # 测试ASR

        # 下载模型
            (agent_api) junweil@precognition-laptop5:~/projects/MLLMs$ python
                Python 3.10.18 (main, Jun  5 2025, 13:14:17) [GCC 11.2.0] on linux
                Type "help", "copyright", "credits" or "license" for more information.
                >>> from modelscope import snapshot_download
                >>> snapshot_download('iic/SenseVoiceSmall', local_dir='pretrained_models/SenseVoiceSmall')

        # 测试ASR （可以接上无线麦克风）
            (agent_api) junweil@precognition-laptop5:~/projects/MLLMs$ python test_sensevoice.py

    # 测试ZMQ

        # publish
            (agent_api) junweil@precognition-laptop5:~/projects/MLLMs$ python3 rgb_zmq_publisher.py --fps 10 --h 720 --w 1280 --cam_num 4 --port 5555

        # subscribe
            (agent_api) junweil@precognition-laptop5:~/projects/MLLMs$ python rgb_zmq_sub_pygame_allthreads.py --publisher_ip 127.0.0.1 --publisher_port 5555 --show_video


    # 跑Agent代码
         # ifconfig 查看G1连接的网络名称，比如 enp131s0

         # 不接G1的时候，不要用 --enable_g1即可

        (agent_api) junweil@precognition-laptop5:~/projects/MLLMs$ python start_vlm_speech_g1_agent_v5_zmq_tts_api.py --cam_num 0 --mic_id 0 --speaker_id 0 --api_url_port m10.precognition.team:8888 --tts_api_url_port m10.precognition.team:50000 --show_video --display_fps_limit 60 --h 720 --w 1280 --asr_thres 0.6 --publisher_ip 127.0.0.1 --publisher_port 5555 --enable_g1 --g1_network enp131s0


    # [06/23/2025] [TODO:Iris]
        # 1. 加入新的手势控制:

            # 目前只有C++ API: https://github.com/unitreerobotics/unitree_sdk2/blob/main/include/unitree/robot/g1/arm/g1_arm_action_client.hpp

            # 当前参考的python API:
                https://github.com/unitreerobotics/unitree_sdk2_python/blob/master/example/g1/high_level/g1_loco_client_example.py
                # 调用G1的代码在这里:
                    robot_arm_high_level.py

            # [06/23/2025]不用了，宇树官方催了之后就更新了python API了


        # 2. 加入联网搜索功能，在一个独立进程，当用户说出“联网搜一下”的关键词，用bing API(?)搜索，有结果再告诉用户

```
### [06/2025] G1更新固件v1.4.0之后，高层API改变
```

    # 1. 我们先测试c++例程，python一般更新不及时

        git clone https://github.com/unitreerobotics/unitree_sdk2/

        # 安装
            $ sudo apt install libyaml-cpp-dev
            mkdir build
            cmake ..
            make


        # 机器人需要站立模式，然后进入走跑运控，才能控制手臂高层控制

        (base) junweil@precognition-laptop5:~/projects/unitree_sdk2/build/bin$ ./g1_arm_action_example enp131s0
             --- Unitree Robotics ---
                 G1 Arm Action Example

            Usage:
              - 0: print supported actions.
              - an id: execute an action.
            Attention:
              Some actions will not be displayed on the APP,
              but can be executed by the program.
              These actions may cause the robot to fall,
              so please execute them with caution.

            Enter action ID: .
            0
            Available actions:
            {"actions":[
            {"id":99,"name":"release_arm"},
            {"id":1,"name":"turn_back_wave"},
            {"id":11,"name":"blow_kiss_with_both_hands_50hz"},
            {"id":12,"name":"blow_kiss_with_left_hand"},
            {"id":13,"name":"blow_kiss_with_right_hand"},
            {"id":15,"name":"both_hands_up"},
            {"id":17,"name":"clamp"},
            {"id":18,"name":"high_five_opt"},
            {"id":19,"name":"hug_opt"},
            {"id":20,"name":"make_heart_with_both_hands"},
            {"id":21,"name":"make_heart_with_right_hand_50hz"},
            {"id":22,"name":"refuse"},
            {"id":23,"name":"right_hand_up"},
            {"id":24,"name":"ultraman_ray"},
            {"id":25,"name":"wave_under_head"},
            {"id":26,"name":"wave_above_head"},
            {"id":27,"name":"shake_hand_opt"},
            {"id":28,"name":"box_left_hand_win"},
            {"id":29,"name":"box_right_hand_win"},
            {"id":30,"name":"box_both_hand_win"}]}

            # 99意思是把手放下


            # 部分手部动作id对应列表
                https://github.com/unitreerobotics/unitree_sdk2/blob/main/include/unitree/robot/g1/arm/g1_arm_action_client.hpp#L46
                # 完整列表是G1 PC1里的没有开放代码给我们

            # 以上C++ 的程序可以控制机器人手部动作

    # 2. 我们自己更改python API [06/23/2025]催了宇树，他们马上更新了armClient的python API，我们还是fork一下

        # git clone https://github.com/JunweiLiang/unitree_sdk2_python

            更新测试

                (base) junweil@precognition-laptop5:~/projects$ git clone https://github.com/JunweiLiang/unitree_sdk2_python

                # 需要修改 g1/loco/g1_loco_client.py
                    # 加入走跑运控模式切换，参考模式ID: https://support.unitree.com/home/zh/G1_developer/sport_services_interface

                    # 重新安装python api

                        (agent_api) junweil@precognition-laptop5:~/projects/unitree_sdk2_python$ pip install -e .

                    # 现在走跑运控和主运控都可以使用
                        (agent_api) junweil@precognition-laptop5:~/projects/unitree_sdk2_python$ python example/g1/high_level/g1_loco_client_example.py enp131s0
                            13 / 14 走跑运控和常规运控可以随时切换，会发出冻的一下的声音。
                            set speed mode无效
                            setvelocity走路速度明显有变化
                            走跑运控下，sport_client.SetVelocity(1.0, 0, 0, 2.0)走了大概1.8米

                    # 走跑运控的时候，不能执行手部动作？
                        # https://github.com/unitreerobotics/unitree_sdk2/blob/794e0c2116be7a5a7e71af84660b6858c0c40cbe/include/unitree/robot/g1/arm/g1_arm_action_error.hpp#L14


                    #实际测试，在走跑运控，主运控下，都可以使用手部动作

                        (agent_api) junweil@precognition-laptop5:~/projects/unitree_sdk2_python$ python example/g1/high_level/g1_arm_action_example.py enp131s0

    # 3. 新的agent代码更新到v6, robot控制更新到 robot_arm_high_level_v2.py
        # m10 的L40, vllm 卡死在 INFO 06-24 11:39:17 [pynccl.py:69] vLLM is using nccl==2.21.5
        # 所以还是用4090 挂vllm

        (agent_api) junweil@precognition-laptop5:~/projects/MLLMs$ python start_vlm_speech_g1_agent_v6_zmq_tts_api.py --cam_num 0 --mic_id 0 --speaker_id 0 --api_url_port office.precognition.team:8888 --tts_api_url_port m10.precognition.team:50000 --show_video --display_fps_limit 60 --h 720 --w 1280 --asr_thres 0.6 --publisher_ip 127.0.0.1 --publisher_port 5555 --enable_g1 --g1_network enp131s0

        # 初始化G1会挥一下手，然后切换到走跑运控
        # 测试没问题，走路丝滑，转向更丝滑，可以鼓掌
```

### [07/2025] 用lt1, 2060笔记本电脑跑API版本，本地跑ASR
```
    # 1. 现在 2x4090挂好TTS, VLM
        # 先开VLM
        (asr_vllm) junweil@office-precognition:/mnt/ssd2/junweil/deepseek$ vllm serve Qwen2.5-VL-32B-Instruct/ --port 8888 --host 0.0.0.0 --limit-mm-per-prompt image=30,video=0 --max-model-len 65536 --gpu-memory-utilization 0.85 --tensor-parallel-size 2 --max_num_seqs 16 --dtype bfloat16 --chat-template ~/projects/asr/MLLMs/chat_template_byjunwei.jinja --quantization fp8

        # TTS

        (asr_vllm) junweil@office-precognition:~/projects/asr/MLLMs$ CUDA_VISIBLE_DEVICES=0 python cosyvoice_server_vllm_junwei.py --port 50000 --model_dir ../CosyVoice/pretrained_models/CosyVoice2-0.5B/ --gpu_memory_utilization 0.1 --voice_type 0 --prompt_audio_path ./test_audio/zero_shot_prompt_laoban_no_music.wav


    # 2. lt1安装

        $ conda create -n agent_api python=3.10

        (agent_api) junweil@lt1:~/projects/asr/MLLMs/streaming_sensevoice$ pip install -r requirements.txt; pip install -r requirements-ws-demo.txt

        pip install pygame pyzmq opencv-python openai -i https://pypi.tuna.tsinghua.edu.cn/simple

        sudo apt-get install sox libsox-dev
        sudo apt install build-essential
        sudo apt-get install libportaudio2
        sudo apt install ffmpeg

        # 安装G1 API

            (agent_api) junweil@lt1:~/projects/asr$ git clone https://github.com/eclipse-cyclonedds/cyclonedds
            cyclonedds$ git checkout 0.10.2
            cyclonedds/build$ cmake ..
            cyclonedds/build$ cmake --build .
            cyclonedds/build$ sudo cmake --build . --target install

            export CYCLONEDDS_HOME=/usr/local/

            # 注意这里要用我们自己改过的SDK

            (agent_api) junweil@lt1:~/projects/asr$ git clone https://github.com/JunweiLiang/unitree_sdk2_python

            unitree_sdk2_python$ pip3 install -e .

        # 报错
            File "/home/junweil/anaconda3/envs/agent_api/lib/python3.10/site-packages/pysilero/pysilero.py", line 22, in <module>
                from frame_queue import FrameQueue
            ModuleNotFoundError: No module named 'frame_queue'

            # 需要改一下代码的相对引用 (注意更换自己代码位置)

                $ vi /home/junweil/anaconda3/envs/agent_api/lib/python3.10/site-packages/pysilero/pysilero.py

                from .frame_queue import FrameQueue
                from .pickable_session import silero_vad
                from .utils import get_energy


            # zmq: libGL error: MESA-LOADER: failed to open iris: /usr/lib/dri/iris_dri.so

            $ conda install -c conda-forge libstdcxx-ng

        # 下载模型

            (agent_api) junweil@lt1:~/projects/asr/MLLMs$ python
            Python 3.10.18 (main, Jun  5 2025, 13:14:17) [GCC 11.2.0] on linux
            Type "help", "copyright", "credits" or "license" for more information.
            >>> from modelscope import snapshot_download
            >>> snapshot_download('iic/SenseVoiceSmall', local_dir='pretrained_models/SenseVoiceSmall')

    # 2. lt1上测试
        1. 测试ASR

            (agent_api) junweil@lt1:~/projects/asr/MLLMs$ python test_sensevoice.py

        2. 测试TTS API

            (agent_api) junweil@lt1:~/projects/asr/MLLMs$ python cosyvoice_client_vllm_junwei_speak.py --host office.precognition.team --port 50000 --tts_text "收到好友从 远方寄来的生日礼物，那份意外的惊喜与深深的祝福让我心中充满了甜蜜的快 乐，笑容如 花儿般绽放。"

        3. agent!

            # publish zmq RGB
                (agent_api) junweil@lt1:~/projects/asr/MLLMs$ python3 rgb_zmq_publisher.py --fps 5 --h 720 --w 1280 --cam_num 2 --port 5555

            # subscribe
                (agent_api) junweil@lt1:~/projects/asr/MLLMs$ python rgb_zmq_sub_pygame_allthreads.py --publisher_ip 127.0.0.1 --publisher_port 5555 --show_video

            (agent_api) junweil@lt1:~/projects/asr/MLLMs$ python start_vlm_speech_g1_agent_v6_zmq_tts_api.py --cam_num 0 --mic_id 0 --speaker_id 0 --api_url_port office.precognition.team:8888 --tts_api_url_port office.precognition.team:50000 --show_video --display_fps_limit 60 --h 720 --w 1280 --asr_thres 0.6 --publisher_ip 127.0.0.1 --publisher_port 5555

            --enable_g1 --g1_network enp2s0

```
## [09/01/2025] lt2上也同样安装测试, realsense serve images, v7 web search
```
    # 安装过程同上
    # 再加
    $ pip install pyrealsense2

        # 下载语音识别模型
        (agent_api) junweil@ai-precognition-laptop2:~/projects/MLLMs$ python
        Python 3.10.18 (main, Jun  5 2025, 13:14:17) [GCC 11.2.0] on linux
        Type "help", "copyright", "credits" or "license" for more information.
        >>> from modelscope import snapshot_download
        >>> snapshot_download('iic/SenseVoiceSmall', local_dir='pretrained_models/SenseVoiceSmall')

    # 2. lt2上测试
        1. 测试ASR

            (agent_api) junweil@ai-precognition-laptop2:~/projects/MLLMs$ python test_sensevoice.py

        2. 测试TTS API

            (agent_api) junweil@ai-precognition-laptop2:~/projects/MLLMs$ python cosyvoice_client_vllm_junwei_speak.py --host office.precognition.team --port 50000 --tts_text "收到好友从 远方寄来的生日礼物，那份意外的惊喜与深深的祝福让我心中充满了甜蜜的快 乐，笑容如 花儿般绽放。"

        3. agent!
            # 记得现在lt2电脑上，设置，sound，确保输入输出device都选对了


            # send code to G1
                (agent_api) junweil@ai-precognition-laptop2:~/projects/MLLMs$ scp rgb_zmq_realsense_publisher.py unitree@192.168.123.164:~/projects/MLLMs/

                unitree@ubuntu:~/projects/MLLMs$ pip install zmq pygame

            # publish zmq RGB using the realsense camera !!
                # fps 5 does not work
                # for realsense, 1280x720 @ 6 fps/ 15fps/30fps works
                unitree@ubuntu:~/projects/MLLMs$ python3 rgb_zmq_realsense_publisher.py --fps 30 --h 720 --w 1280 --cam_num 0 --port 5555 --is_realsense

                # 1号机 jetson会自动挂掉，还是直接realsense接笔记本吧

                (agent_api) junweil@ai-precognition-laptop2:~/projects/MLLMs$ python3 rgb_zmq_realsense_publisher.py --fps 6 --h 720 --w 1280 --cam_num 0 --port 5555 --is_realsense

            # subscribe test image client
                (agent_api) junweil@ai-precognition-laptop2:~/projects/MLLMs$ python rgb_zmq_sub_pygame_allthreads.py --publisher_ip 127.0.0.1 --publisher_port 5555 --show_video

            # v6
                (agent_api) junweil@ai-precognition-laptop2:~/projects/asr/MLLMs$ python start_vlm_speech_g1_agent_v6_zmq_tts_api.py --cam_num 0 --mic_id 0 --speaker_id 0 --api_url_port office.precognition.team:8888 --tts_api_url_port office.precognition.team:50000 --show_video --display_fps_limit 60 --h 720 --w 1280 --asr_thres 0.6 --publisher_ip 127.0.0.1 --publisher_port 5555 --enable_g1 --g1_network enp2s0

            # v7 with web search
                # without g1 first
                    $ pip install langchain langchain-community beautifulsoup4
                    $ export BRAVE_SEARCH_API_KEY="BSAR9HjxJzkpapWXbmps3fkYM-rJm6F"
                        # 或者自己去注册api key, 有免费的：https://brave.com/zh/search/api/
                        # 中国地址visa也可以

                # [09/02/2025] 报错422，已反馈Iris
                # [09/03/2025] 更新后，可以了。
                    # 样例：现在的美国总统是谁？Qwen会回答拜登，然后网络查询现在的美国总统是谁？ 就会得到特朗普了，要20秒左右。如果出现connection reset by peers错误，重启可以解决。网络问题
                    # 测试视频： https://drive.google.com/file/d/1CJTsMvYcO4Wt8A_1Hgz6FF6EEuEWdvQY/view?usp=drive_link

            # [09/2025] 加入自定义的手势
                 (agent_api) junweil@precognition-laptop6:~/projects/speechvla/MLLMs$ python test_g1_high_level.py gesture_data/ enp131s0

                 # 测试左欢迎，右欢迎
```
## [09/2025] 测试宇树自己的ASR方位角API
```
    # 宇树的离线speech ASR跑在PC1上，直接给出DDS/ROS2 topic 结果
    # 方位角识别不work
        (base) unitree@ubuntu:~$ ros2 topic echo /audio_msg
        data: '{"index":1,"timestamp":1756974332218,"type":0,"text":"你好。","angle":0,"speaker_id":0,"emotion":"<|HAPPY|>","confidence":0.500000,...'
        ---
        data: '{"index":2,"timestamp":1756974345038,"type":0,"text":"听见我说话吗？","angle":0,"speaker_id":0,"emotion":"<|NEUTRAL|>","confidence":0.5...'
        ---
        data: '{"index":3,"timestamp":1756974354965,"type":0,"text":"在这边讲话。","angle":0,"speaker_id":0,"emotion":"<|NEUTRAL|>","confidence":0.50...'
        ---
        data: '{"index":4,"timestamp":1756974362016,"type":0,"text":"在这边讲话。","angle":0,"speaker_id":0,"emotion":"<|NEUTRAL|>","confidence":0.50...'
        ---
        data: '{"index":5,"timestamp":1756974374951,"type":0,"text":"听见我说话吗？","angle":0,"speaker_id":0,"emotion":"<|NEUTRAL|>","confidence":0.5...'
        ---
        data: '{"index":6,"timestamp":1756974382298,"type":0,"text":"听见我说话吗？","angle":0,"speaker_id":0,"emotion":"<|NEUTRAL|>","confidence":0.5...'
        ---
    # [09/04/2025] 宇树就说这个还没实现的
```
## [09/2025] 测试幻尔AI科大讯飞语音版子
```
    # 代码，ROS1: https://github.com/yanjingang/xf_mic_asr_offline/tree/main
        # ROS1 只支持到Ubuntu 20.04
        # 宇树的PC2倒是有ROS1 +  ROS2
        # 用宇树的PC2来搞

        # 发送代码
            (base) junweil@precognition-laptop6:~/projects/speechvla$ scp -r /home/junweil/Downloads/xf_mic_asr_offline.zip  unitree@192.168.123.164:~/Downloads/

        # 安装包裹

            (base) unitree@ubuntu:~/catkin_ws$ cp -r ~/Downloads/xf_mic_asr_offline src/

            # 更改一下CMakelist x64 -> arm64 for jetson
            (base) unitree@ubuntu:~/catkin_ws$ vi src/xf_mic_asr_offline/CMakeLists.txt

            # 安装！没报错
            (base) unitree@ubuntu:~/catkin_ws$ catkin_make -DPYTHON_EXECUTABLE=/usr/bin/python3

        # 跑程序
            # 需要先去科大讯飞获取api key

                https://console.xfyun.cn/app/myapp
                # 还得先实名认证
                创建应用后，去语音识别-》离线命令词识别 -> 复制页面的appid 5e59d3a8
                 下载SDK -> Linux MSC
                 # 选择旧版可以下载到 junweiliang@work_laptop:~/Downloads$ ls Linux_aitalk_exp1227_5e59d3a8.zip

                 # 发送
                    (base) junweil@precognition-laptop6:~/projects/speechvla$ scp /home/junweil/Downloads/Linux_aitalk_exp1227_5e59d3a8.zip unitree@192.168.123.164:~/Downloads

                # 替换文件
                    (base) unitree@ubuntu:~/catkin_ws$ cp ~/Downloads/bin/msc/res/asr/common.jet src/xf_mic_asr_offline/config/msc/res/asr/
                    (base) unitree@ubuntu:~/catkin_ws$ rm -rf src/xf_mic_asr_offline/config/msc/res/asr/GrmBuilld/

                # 更改配置 appID
                    (base) unitree@ubuntu:~/catkin_ws$ vi src/xf_mic_asr_offline/launch/mic_init.launch

            # 还有一些依赖
                (base) unitree@ubuntu:~/catkin_ws$ python3 -m pip install pyyaml rospkg pyserial

                (base) unitree@ubuntu:~/catkin_ws$ export LD_LIBRARY_PATH=~/catkin_ws/src/xf_mic_asr_offline/lib/arm64:$LD_LIBRARY_PATH


                $ sudo cp ~/catkin_ws/src/xf_mic_asr_offline/xf_mic.rules /etc/udev/rules.d/
                $ sudo udevadm control --reload-rules
                $ sudo udevadm trigger

            (base) unitree@ubuntu:~/catkin_ws$ source ~/catkin_ws/devel/setup.bash

            # 这个默认使用 /dev/ttyUSB0, 需要拆掉所有其他usb

            (base) unitree@ubuntu:~/catkin_ws$ roslaunch xf_mic_asr_offline mic_init.launch

            # 可以用！但是有一堆其他的语音识别的东西

            >>>>>正在录音........
            >>>>>唤醒角度为: 151


            >>>>>停止录音........
            >>>>>是否识别成功(whether the recognition succeeds): [ 否 ]
            >>>>>关键字的置信度(keywords confidence): [ 0 ]
            >>>>>关键字置信度较低，文本不予显示(keyword confidence is too low. The text will not be displayed)
            >>>>>完成一次识别(finish voice recognition)

            >>>>>开始一次语音识别！(start first voice recognition!)
            已初始化录音参数

            >>>>>正在录音........
            >>>>>唤醒角度为: 89


            >>>>>停止录音........
            >>>>>未能检测到有效声音,请重试(no sound is detected, and please try again)
            >>>>>完成一次识别(finish voice recognition)

            >>>>>开始一次语音识别！(start first voice recognition!)
            已初始化录音参数

            >>>>>正在录音........
            >>>>>唤醒角度为: 29


            >>>>>停止录音........
            >>>>>未能检测到有效声音,请重试(no sound is detected, and please try again)
            >>>>>完成一次识别(finish voice recognition)

            >>>>>开始一次语音识别！(start first voice recognition!)
            已初始化录音参数

            >>>>>正在录音........
            >>>>>唤醒角度为: 338

            # 视频效果: https://drive.google.com/file/d/1lh86Ib74tNU6WvmZW8SOFuyNEynBSdbq/view?usp=drive_link

```


