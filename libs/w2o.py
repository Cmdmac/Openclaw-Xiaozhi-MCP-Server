import argparse
from pydub import AudioSegment

def convert_wav_to_ops_16k(input_path, output_path, bitrate):
    try:
        print(f"正在读取文件: {input_path}")
        audio = AudioSegment.from_wav(input_path)

        # ==========================================
        # 核心修改 1：在送给编码器之前，强制重采样为 16000Hz 和单声道
        # ==========================================
        print("正在进行 16kHz 重采样和单声道转换...")
        audio = audio.set_frame_rate(16000).set_channels(1)

        # ==========================================
        # 核心修改 2：增加专门针对 16K 语音的 FFmpeg 底层参数
        # ==========================================
        print(f"正在转换，目标比特率: {bitrate}，请稍候...")
        audio.export(
            output_path, 
            format="ogg", 
            codec="libopus", 
            parameters=[
                "-b:a", bitrate,          # 设置比特率 (例如 "16k")
                "-application", "voip",   # 强制切换到 VOIP (人声) 模式，启用 SILK 算法
                "-vbr", "on",             # 开启可变比特率 (Opus 官方推荐)
                "-compression_level", "10" # 开启最高级压缩，确保底层彻底切到窄带/宽带模式
            ] 
        )
        print(f"转换成功！文件已保存至: {output_path}")
        
    except FileNotFoundError:
        print(f"错误: 找不到输入文件 '{input_path}'，请检查路径是否正确。")
    except Exception as e:
        print(f"转换失败: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="将 WAV 转换为 16K 优化的 OPS/Opus 格式")
    parser.add_argument("-i", "--input", required=True, help="输入文件的路径")
    parser.add_argument("-o", "--output", required=True, help="输出文件的路径")
    parser.add_argument("-b", "--bitrate", default="16k", help="音频比特率 (默认: 16k)")

    args = parser.parse_args()
    convert_wav_to_ops_16k(args.input, args.output, args.bitrate)