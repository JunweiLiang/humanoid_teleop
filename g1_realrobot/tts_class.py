import threading
import  re
import time
import numpy as np
from datetime import datetime
import sounddevice as sd
import requests
import sys
sys.path.append("third_party/Matcha-TTS")

def print_with_time(*args, **kwargs):
    timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    print(timestamp, *args, **kwargs)

class TTSAgent:
    def __init__(self, api_url_port=None):

        self.tts_url = "http://{}/inference_zero_shot_fast".format(api_url_port)

        self.control_dt = 1.0 / 100  # 最高控制频率，至少隔这个时间才去看有没有东西要生成
        self.cosyvoice_sample_rate = 24000

        # First-in-first-out queue
        self.text_queue = []

        # initialize publish thread
        self.publish_thread = threading.Thread(target=self._run_tts)
        self.ctrl_lock = threading.Lock()
        self.publish_thread.daemon = True
        self.publish_thread.start()

        # 需要这些才能打断
        self.audio_stream = None  # The sounddevice OutputStream instance
        self.audio_data_buffer = None  # Stores the current audio segment to play
        self.current_frame = 0  # Tracks playback position within audio_data_buffer
        self.stop_playback_event = threading.Event()  # Signals the callback to stop playback

        # --- Latency Tracking ---
        self.tts_start_time = None

    def split_message(self, text):
        # Use regex to split while keeping the delimiter
        # 按标点拆分，并保留标点到原句子

        sentences = re.split(r"([。？！?!])", text)  # 按句号拆分
        result = []

        for i in range(0, len(sentences) - 1, 2):  # 两两合并（句子 + 标点）
            result.append(sentences[i] + sentences[i + 1])

        if len(sentences) % 2 == 1 and sentences[-1].strip():  # 处理没有结尾标点的情况
            result.append(sentences[-1])

        return result

    # 所以这个函数，可以一直接收要生成的文本，存起来
    def send_non_block(self, text):
        text = text.strip()
        if text:
            # 给定的text可能有多句话，要断句
            text_list = self.split_message(text)
            with self.ctrl_lock:
                self.text_queue += text_list

            # print_with_time("\t[TTSAgent-收到send_non_block , 当前text_queue %s]"% self.text_queue)

            # Capture the time when TTS is requested (if it's the first text in queue)
            if self.tts_start_time is None:
                self.tts_start_time = time.perf_counter()

    def stop_and_empty(self):
        """
        Stops current audio playback immediately and clears the text queue.
        This can be called from any thread.
        """
        with self.ctrl_lock:
            # Clear pending TTS texts
            self.text_queue = []
            print_with_time("\t[TTSAgent-Received stop_and_empty command. Text queue cleared.]")

            # Stop the currently playing audio stream if active
            if self.audio_stream and self.audio_stream.active:
                print_with_time("\t[TTSAgent-Signaling audio callback to stop...]")
                self.stop_playback_event.set()  # Signal the callback to stop providing data

                # Explicitly stop the stream object to ensure its active state updates
                print_with_time("\t[TTSAgent-Calling self.audio_stream.stop()...]")
                self.audio_stream.stop()  # This is the definitive stop command
                print_with_time("\t[TTSAgent-self.audio_stream.stop() called.]")
            else:

                print_with_time("\t[TTSAgent-No active audio stream to stop.]")
                self.stop_playback_event.clear()

            self.tts_start_time = None  # Reset TTS start time on stop

    def _audio_playback_callback(self, outdata, frames, time_info, status):
        """
        Sounddevice callback for feeding audio data.
        This runs in an internal sounddevice thread.
        """
        # 1. Handle potential errors reported by sounddevice
        if status:
            if status.output_underflow:
                print("TTSAgent Callback: Output underflow! Consider increasing blocksize or processing speed.", file=sys.stderr)
            else:
                print(f"TTSAgent Callback Status: {status}", file=sys.stderr)
            outdata.fill(0)
            return sd.CallbackStop

        # 2. Check for external stop signal (highest priority)
        if self.stop_playback_event.is_set():
            outdata.fill(0)
            return sd.CallbackStop

        # 3. Determine how many frames we can actually provide from our buffer
        num_frames_to_copy = min(frames, len(self.audio_data_buffer) - self.current_frame)

        # 4. Get the chunk of data from our buffer
        chunk = self.audio_data_buffer[self.current_frame : self.current_frame + num_frames_to_copy]

        # 5. Copy the chunk to outdata
        outdata[:num_frames_to_copy] = chunk

        # 6. Pad the rest of the outdata buffer with zeros if we didn't fill it
        if num_frames_to_copy < frames:
            outdata[num_frames_to_copy:].fill(0)

        # 7. Advance frame pointer by the amount copied
        self.current_frame += num_frames_to_copy

        # 8. Explicitly check if all audio data has been sent
        if self.current_frame >= len(self.audio_data_buffer):
            # print("returned sd.CallbackStop") # Debug print to confirm it's reached
            self.stop_playback_event.set()  # 必须用这个才能停止
            return sd.CallbackStop  # Signal that all data has been played

        # 9. If we reached here, it means more data is still available
        return sd.CallbackFlags(0)

    def _call_tts_api(self, text):
        payload = {
            "tts_text": text,
        }
        response = requests.request("GET", self.tts_url, data=payload, stream=True)

        tts_audio = b""
        for r in response.iter_content(chunk_size=16000):
            tts_audio += r
        # tts_speech = torch.from_numpy(np.array(np.frombuffer(tts_audio, dtype=np.int16))).unsqueeze(dim=0)
        # print(tts_speech.shape) #torch.Size([1, 287040]) # this is for torchaudio.save()
        tts_speech = np.array(np.frombuffer(tts_audio, dtype=np.int16))

        return tts_speech

    # 一开始就准备着，当有文本生成的时候就生成
    def _run_tts(self):
        while True:
            start_time = time.time()

            text_to_read = None
            with self.ctrl_lock:
                # 取第一个text读
                if self.text_queue:
                    text_to_read = self.text_queue.pop(0)
            # for debug
            # print_with_time("\t[TTSAgent-run_tts , 当前text_queue %s, text_to_read: %s]"% (self.text_queue, text_to_read))

            if text_to_read:
                print_with_time("\t[TTSAgent-开始生成]: %s" % text_to_read)

                tts_speech = self._call_tts_api(text_to_read)

                self.audio_data_buffer = tts_speech.reshape(-1, 1)  # (N,) -> (N, 1)

                self.current_frame = 0  # Reset frame counter for new audio segment

                # 只有一个segment
                if self.tts_start_time is not None:
                    # 这个只是计算文本生成语音的时间
                    time_to_first_voice = time.perf_counter() - self.tts_start_time
                    print_with_time(f"\t[---Latency][TTSAgent-TTS time: {time_to_first_voice:.3f} seconds]")
                    self.tts_start_time = None  # Reset after first voice output

                # Initialize stop event for THIS playback segment
                self.stop_playback_event.clear()

                # --- Audio Playback ---
                try:
                    # Create the stream instance (NOT with a 'with' statement here)
                    # need to initialize every time
                    # This allows it to be controlled externally.
                    self.audio_stream = sd.OutputStream(
                        samplerate=self.cosyvoice_sample_rate,
                        channels=1,
                        dtype=np.int16,
                        callback=self._audio_playback_callback,  # Our custom callback
                        # finished_callback=self.stop_playback_event.set,
                    )
                    # with self.audio_stream:
                    #    self.stop_playback_event.wait()
                    self.audio_stream.start()
                    while True:
                        # print_with_time("playback event waiting...")
                        if not self.audio_stream.active or self.stop_playback_event.is_set():
                            break
                        time.sleep(0.05)
                    # print_with_time("playback event done.")

                except Exception as e:
                    print_with_time(f"\t[TTSAgent-Error during audio playback: {e}]")
                finally:
                    # Ensure the stream is closed after each segment or on error
                    if self.audio_stream:
                        if self.audio_stream.active:
                            # print_with_time("\t[TTSAgent-Ensuring stream is stopped before closing...]")
                            self.audio_stream.stop()  # Ensure it's stopped
                        # print_with_time("\t[TTSAgent-Closing audio stream.]")
                        self.audio_stream.close()
                        self.audio_stream = None  # Clear instance after closing

                self.stop_playback_event.clear()
                print_with_time("\t[TTSAgent-生成完成]")

            current_time = time.time()
            all_t_elapsed = current_time - start_time
            sleep_time = max(0, (self.control_dt - all_t_elapsed))
            time.sleep(sleep_time)
