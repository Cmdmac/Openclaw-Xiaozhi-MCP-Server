import urllib.request
import json
import asyncio
import websockets
import os
import wave
import sys
from openclaw_client import OpenClawClient

# ==========================================
# ⚙️ 配置区域
# ==========================================
XIAOZHI_WS_URL = "wss://api.xiaozhi.me/mcp/?token=eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOjIyMjY5OCwiYWdlbnRJZCI6MTYxNTk3MiwiZW5kcG9pbnRJZCI6ImFnZW50XzE2MTU5NzIiLCJwdXJwb3NlIjoibWNwLWVuZHBvaW50IiwiaWF0IjoxNzc0NzA3NzEyLCJleHAiOjE4MDYyNjUzMTJ9.PXLOtgB9vp0rZDAVDIEG9CBLA3EKzwaAd23s7oqQ02IsUfMcEeVAYIBsLktjfhC012d7LQisz2I4_v-Y4L3d0w"  # ⚠️ 填入你的小智接入点
GATEWAY_URL = "http://47.112.18.149:13090"
API_TOKEN = "4795849d32b1f6711e87b5440a517c46"

# 初始化客户端
client = OpenClawClient(
    gateway_url=GATEWAY_URL,
    api_token=API_TOKEN,
)

# 🌟 全局“文件柜”：用来存放后台任务的状态和结果
TASK_STORE = {
    "status": "idle", # 状态：idle(空闲), running(执行中), finished(已完成)
    "prompt": "",     # 记录当前在查什么
    "result": ""      # 存放最终结果
}
# =======================================

                

def _sync_http_request(prompt_text):
    
    reply = client.send_message(prompt_text)
    return reply

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
    """
    纯 Python 实现的 OGG 容器解析器，直接提取 Opus 数据帧。
    完全零依赖，不需要安装 av，不需要编译 C 语言！
    """
    packets = []
    
    if not os.path.exists(ogg_path):
        print(f"file not exist: {ogg_path}")
        return packets

    print(f"parse ogg file and send file stream: {ogg_path}")

    with open(ogg_path, 'rb') as f:
        packet_data = b''
        page_count = 0
        
        while True:
            # 1. 读取 27 字节的 Ogg 页面头部
            header = f.read(27)
            if len(header) < 27:
                break # 文件读完了
            
            # 2. 校验 Ogg 的魔法标识 "OggS"
            if header[:4] != b'OggS':
                print("not a valid ogg file")
                break
                
            page_count += 1
            
            # 3. 获取该页面的 Segment (分段) 数量 (在头部的第 26 字节处)
            num_segments = header[26]
            
            # 4. 读取 Segment 大小表
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
                            toc_byte = packet_data[0] # 取出第一块肉的第一个字节
                            pkg_duration = get_opus_frame_duration(toc_byte)
                            duration = duration + pkg_duration
                            frames += packet_data
                            l = len(frames)
                            if duration == 60:                                
                                print(f"framesize: {l} bytes | duration: {duration} ms")
                                duration = 0
                                packets.append(frames)
                                frames = b''
                            
                    
                    # 清空缓冲，准备接收下一帧
                    packet_data = b''
                    
    print(f"parsing success {page_count} pages，total {len(packets)} frames Opus data。")
    return packets
        
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
            
            print(f"wav info: {frame_rate}Hz, {channels}channel, {sample_width*8} bitwidth")
            
            # 一次性读取所有的 PCM 数据 (纯二进制)
            pcm_bytes = wav_file.readframes(num_frames)
            
            return pcm_bytes
            
    except wave.Error as e:
        print(f"read wav failure: {e}")
        return b""
    except FileNotFoundError:
        print(f"file not found: {file_path}")
        return b""

async def sendWav(ws, file_path):
    # 发送读取的文件内容
    file_size = os.path.getsize(file_path)
    type="wav_stream"
    await ws.send(f"cmd=start_send,type={type},file_size={file_size}")	                   
    pcm_data = read_pcm_bytes_from_wav("check_openclaw_result_16k.wav") 
    await ws.send(pcm_data)
    await ws.send("cmd=end_send")

async def sendOgg(ws, file_path):
    file_size = os.path.getsize(file_path)
    type="ogg_file"
    await ws.send(f"cmd=start_send,type={type},file_size={file_size}")	  
    print(f"sendtype={type},file_size={file_size}")
    with open(file_path, 'rb') as f:
        content = f.read()
        await ws.send(content)        
    
#    frames = stream_opus_from_ogg(file_path)
#    for frame in frames:
#        await ws.send(frame)
    await ws.send("cmd=end_send")
    
async def background_worker(prompt_text):
    """后台打工人：负责偷偷去查服务器，查完放进文件柜"""

    TASK_STORE["status"] = "running"
    TASK_STORE["prompt"] = prompt_text
    TASK_STORE["result"] = ""
    
    print(f"running background prompt: {prompt_text}")
    
    # 将耗时的网络请求扔到专门的线程里，绝不卡主程序
	# 获取当前的事件循环，并把耗时任务扔进默认的后台线程池
    loop = asyncio.get_event_loop()
    prompt_final_text = "用简短易懂的方式回复以下问题:" + prompt_text
    result = await loop.run_in_executor(None, _sync_http_request, prompt_final_text)
     
    # 活干完了，把结果存起来
    TASK_STORE["result"] = result
    TASK_STORE["status"] = "finished"
    print(result)
    print(f"task finish, waiting query")
    print("notifying clients")
    if CONNECTED_CLIENTS:
        print(f":sending notifications to {len(CONNECTED_CLIENTS)} clients...")
	            
	   # 遍历花名册，给每个在线的客户端发送 "hello"
        for ws in list(CONNECTED_CLIENTS):
            try:
                file_path = "audios/check_openclaw_result.ogg"
                await sendOgg(ws, file_path)
            except Exception as e:
                print(f"send to client failure: {e}")

CONNECTED_CLIENTS = set()
# ==========================================
# 1. 静态数据抽离：把冗长的工具定义放在最上面
# ==========================================
MY_TOOLS_SCHEMA = [
    {
        "name": "execute_openclaw_task",
        "description": "这是名为小龙的服务器执行服务器运维或执行任务接口。调用后立刻用语音安抚用户，告诉任务已交由后台处理。",
        "inputSchema": {
            "type": "object",
            "properties": {"prompt": {"type": "string", "description": "用户的具体指令"}},
            "required": ["prompt"]
        }
    },
    {
        "name": "check_openclaw_result",
        "description": "这是名为小龙的服务器查询任务结果接口。当用户询问之前的服务器任务完成情况时，调用此工具获取后台结果。",
        "inputSchema": {
            "type": "object", "properties": {}, "required": []
        }
    }
]

# ==========================================
# 2. 协议层封装：统一回复 JSON-RPC 格式
# ==========================================
async def send_rpc_result(ws, msg_id, result_data):
    """统一的 JSON-RPC 回复发送器"""
    response = {
        "jsonrpc": "2.0",
        "id": msg_id,
        "result": result_data
    }
    await ws.send(json.dumps(response))

# ==========================================
# 3. 业务层拆分：将每个动作写成独立的处理器
# ==========================================
async def handle_initialize(ws, msg_id, params):
    await send_rpc_result(ws, msg_id, {
        "protocolVersion": "2024-11-05", 
        "capabilities": {"tools": {}}, 
        "serverInfo": {"name": "龙虾", "version": "2.0"}
    })

async def handle_tools_list(ws, msg_id, params):
    await send_rpc_result(ws, msg_id, {"tools": MY_TOOLS_SCHEMA})

async def handle_tools_call(ws, msg_id, params):
    global TASK_STORE
    tool_name = params.get("name")
    reply_text = ""

    if tool_name == "execute_openclaw_task":
        user_prompt = params.get("arguments", {}).get("prompt", "")
        if TASK_STORE["status"] == "running":
            reply_text = f"warning：one task「{TASK_STORE['prompt']}」running，please call later"
        else:
            asyncio.ensure_future(background_worker(user_prompt))
            reply_text = "指令已成功下发！请向用户播报友好内容"
            print("return to xiaozhi immediately... not to block calling")

    elif tool_name == "check_openclaw_result":
        print(f"query from xiaozhi mcp，current status: {TASK_STORE['status']}")
        if TASK_STORE["status"] == "idle":
            reply_text = "目前服务器后台很闲，没有任何正在执行或已完成的任务记录。"
        elif TASK_STORE["status"] == "running":
            reply_text = f"请告诉用户：任务「{TASK_STORE['prompt']}」仍在努力执行中，请多给一点时间。"
        elif TASK_STORE["status"] == "finished":
            reply_text = f"请告诉用户任务执行结果：\n{TASK_STORE['result']}"

    # 返回工具执行结果
    await send_rpc_result(ws, msg_id, {"content": [{"type": "text", "text": reply_text}]})


# 路由表：把指令名称映射到对应的处理函数
METHOD_ROUTERS = {
    "initialize": handle_initialize,
    "tools/list": handle_tools_list,
    "tools/call": handle_tools_call,
    "call_tool": handle_tools_call  # 兼容不同的叫法
}

# ==========================================
# 连接小智MCP接入点
# ==========================================
async def connect_to_xiaozhi():
    """核心循环：主动连接小智，并保持监听"""
    print("connecting to xiaozhi mcp server...")
    
    while True: # 外层加个 while True 实现断线自动重连
        try:
            async with websockets.connect(XIAOZHI_WS_URL, ping_interval=None) as ws:
                print("connect to xiaozhi mcp server success!")
                
                async for message in ws:
                    data = json.loads(message)
                    method = data.get("method")
                    msg_id = data.get("id")

                    if method == "ping":
                        await send_rpc_result(ws, msg_id, {})
                        continue
                    
                    if not method:
                        continue

                    # 【核心简化】去路由表里找对应的处理函数，找到了就执行
                    handler = METHOD_ROUTERS.get(method)
                    if handler:
                        await handler(ws, msg_id, data.get("params", {}))
                    else:
                        print(f"unkown method: {method}")
                        
        except websockets.exceptions.ConnectionClosed:
            print("connection closed, sleep 5s and reconnect...")
            await asyncio.sleep(5)
        except Exception as e:
            print(f"unknown error: {e}, sleep 5s and reconnect...")
            await asyncio.sleep(5)

async def handler_client(websocket, path):
    client_ip = websocket.remote_address[0]
    print(f"client from ip: {client_ip}, path: {path}")
    
    # 客户端连入时，将其加入花名册
    CONNECTED_CLIENTS.add(websocket)
    
    
    try:
        # 循环接收客户端发来的消息
        async for message in websocket:
            if isinstance(message, str):
                print(f"message from client: {message}")       
                    
            
                
    except websockets.exceptions.ConnectionClosedOK:
        print(f"connection close from client normally")
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"client {client_ip} connection close: {e}")
    finally:
        # 客户端断开时，务必将其从花名册中移除，防止向死连接发消息报错
        CONNECTED_CLIENTS.remove(websocket)
        print(f"remove client: {client_ip}")

async def keyboard_listener():
    loop = asyncio.get_event_loop()
    while True:
        # 使用 to_thread 防止 input() 阻塞整个服务端的异步运行
        #await asyncio.to_thread(input) 
        await loop.run_in_executor(None, input)
        # 当你按下回车后，代码会走到这里
        if CONNECTED_CLIENTS:
            # 【修正】修改了日志文案，使其与实际发送的文件行为一致
            print(f"sending audio to  {len(CONNECTED_CLIENTS)} clients...")
            
            # 遍历花名册，给每个在线的客户端发送数据
            for ws in list(CONNECTED_CLIENTS):               
                try: 
                    # 发送读取的文件内容
                    file_path = "audios/check_openclaw_result.ogg"
                    await sendOgg(ws, file_path);
                    
                except Exception as e: # 【修正】与 try 对齐
                    print(f"sending failure: {e}") # 【修正】统一 4 个空格缩进
        else:
            print("no clients no sending")
            
if __name__ == "__main__":
    print("=================================================")
    print(" MCP Channel Server Starting...")
    print("=================================================")

# 1. 拿到全场唯一的发动机 (事件循环)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        start_server = websockets.serve(handler_client, "0.0.0.0", 8765)
        loop.run_until_complete(start_server)
        print("local listening websocket server: ws://0.0.0.0:8765")    

        # 3. 把小智客户端塞进后台任务列表
        asyncio.ensure_future(connect_to_xiaozhi())

        asyncio.ensure_future(keyboard_listener())
        # 4. 发动机启动，永远运行！
        loop.run_forever()
        
        
    except KeyboardInterrupt:
        print("keyboard interrupt closing")
        # 获取所有还在事件循环里挂起的后台任务
        pending_tasks = asyncio.Task.all_tasks(loop=loop)
        
        # 向所有任务发送取消信号
        for task in pending_tasks:
            task.cancel()
            
        # 让事件循环再跑最后一段，等待所有任务乖乖处理完取消信号
        if pending_tasks:
            print(f"cleaning {len(pending_tasks)} tasks...")
            # gather 会等待所有任务结束，return_exceptions=True 防止取消时抛出异常打断关机
            loop.run_until_complete(asyncio.gather(*pending_tasks, return_exceptions=True))
    finally:
        # 拔钥匙熄火
        loop.close()
        print("bye bye!")
