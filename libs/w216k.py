import argparse
from pydub import AudioSegment

def resample_with_pydub(input_file: str, output_file: str, int bitrate):
    # 加载音频
    audio = AudioSegment.from_wav(input_file)
    
    # 转换为 16kHz (16000)
    audio = audio.set_frame_rate(bitrate)
    
    # 【进阶推荐】顺手转成单声道 (Mono)，AI 模型最爱
    audio = audio.set_channels(1) 
    
    # 导出文件
    audio.export(output_file, format="wav")
    print("✅ 转换完成！")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="将 WAV 转换为 16K 格式")
    parser.add_argument("-i", "--input", required=True, help="输入文件的路径")
    parser.add_argument("-o", "--output", required=True, help="输出文件的路径")
    parser.add_argument("-b", "--bitrate", default="16000", help="音频比特率 (默认: 16k)")

    args = parser.parse_args()
    resample_with_pydub(args.input, args.output, bitrate)