import argparse
import wave

def read_pcm_bytes_from_wav(file_path: str) -> bytes:
    """
    从 WAV 文件中读取原始 PCM 字节流数据 (Bytes)
    
    :param file_path: wav 文件路径
    :return: PCM 二进制数据
    """
    try:
        with wave.open(file_path, 'rb') as wav_file:
            # 提取音频元数据（可选，根据业务需求决定是否需要返回这些信息）
            channels = wav_file.getnchannels()       # 声道数 (1: 单声道, 2: 立体声)
            sample_width = wav_file.getsampwidth()   # 采样位深 (通常 2 表示 16-bit)
            frame_rate = wav_file.getframerate()     # 采样率 (如 16000, 44100 Hz)
            num_frames = wav_file.getnframes()       # 总帧数
            
            print(f"🔊 音频信息: {frame_rate}Hz, {channels}声道, {sample_width*8}位深")
            
            # 一次性读取所有的 PCM 数据 (纯二进制)
            pcm_bytes = wav_file.readframes(num_frames)
            
            return pcm_bytes
            
    except wave.Error as e:
        print(f"❌ 读取 WAV 文件失败: {e}")
        return b""
    except FileNotFoundError:
        print(f"❌ 找不到文件: {file_path}")
        return b""

# 使用示例
# pcm_data = read_pcm_bytes_from_wav("test.wav")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="查看WAV文件参数")
    parser.add_argument("-i", "--path", required=True, help="输入文件的路径")
    args = parser.parse_args()
    pcm_data = read_pcm_bytes_from_wav(args.path)

