import os

def get_opus_frame_duration(toc_byte: int) -> float:
    """
    根据 Opus 协议 (RFC 6716)，从 TOC 字节解析当前帧的时长（毫秒）
    """
    config = toc_byte >> 3  # 右移 3 位，提取最高的 5 个 Bit
    
    if config < 12:
        # SILK 模式
        return [10.0, 20.0, 40.0, 60.0][config % 4]
    elif config < 16:
        # Hybrid 模式
        return [10.0, 20.0][config % 2]
    else:
        # CELT 模式
        return [2.5, 5.0, 10.0, 20.0][config % 4]


def stream_opus_from_ogg(ogg_path: str) -> list:
    packets = []
    
    if not os.path.exists(ogg_path):
        print(f"❌ 文件不存在: {ogg_path}")
        return packets

    with open(ogg_path, 'rb') as f:
        packet_data = b''
        page_count = 0
        
        while True:
            header = f.read(27)
            if len(header) < 27 or header[:4] != b'OggS':
                break
                
            page_count += 1
            num_segments = header[26]
            segment_table = f.read(num_segments)
            
            duration = 0
            frames = b''
            # 5. 根据大小表提取真正的 Opus 帧数据
            for length in segment_table:
                packet_data += f.read(length)
                
                # 根据 OGG 协议，如果 length < 255，说明当前数据包（Packet）拼装结束了
                if length < 255:
                    if len(packet_data) > 0:
                        # 过滤掉 Ogg 规范里的前两个非音频配置头 (OpusHead 和 OpusTags)
                        if packet_data.startswith(b'OpusHead') or packet_data.startswith(b'OpusTags'):
                            pass # 这是头文件，直接丢弃
                        else:
                            # 剩下的就是纯正的 Opus 音频帧，存入列表！
                            sz = len(packet_data)
                            toc_byte = packet_data[0] # 取出第一块肉的第一个字节
                            pkg_duration = get_opus_frame_duration(toc_byte)
                            duration = duration + pkg_duration
                            frames += packet_data
                            if duration == 60:                                
                                print(f"📦 帧大小: {sz:3} 字节 | ⏱️ 时长: {duration} ms")
                                duration = 0
                                packets.append(frames)
                                frames = b''
                            
                    
                    # 清空缓冲，准备接收下一帧
                    packet_data = b''
                    
    return packets

# 测试运行
if __name__ == "__main__":
    all_packets = stream_opus_from_ogg("check_openclaw_result.ogg")