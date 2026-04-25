#!/usr/bin/env python3
"""
OpenClaw WebChat Python 客户端示例
使用 OpenAI 兼容 HTTP API 与 OpenClaw 收发消息

配置信息:
- Gateway URL: http://47.112.18.149:13090
- API Token: 4795849d32b1f6711e87b5440a517c46
- 模型：openclaw/default
"""

import requests
import json

# ============== 配置 ==============
GATEWAY_URL = "http://47.112.18.149:13090"
API_TOKEN = "4795849d32b1f6711e87b5440a517c46"
MODEL = "openclaw/default"  # 使用默认 agent

# 请求头
HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}


def send_message(message: str, user_id: str = "python-user", stream: bool = False):
    """
    发送消息到 OpenClaw
    
    Args:
        message: 要发送的消息内容
        user_id: 用户标识（用于会话跟踪，相同 user_id 会共享会话）
        stream: 是否使用流式响应
    
    Returns:
        回复内容或生成器
    """
    url = f"{GATEWAY_URL}/v1/chat/completions"
    
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "user", "content": message}
        ],
        "user": user_id,  # 用于会话跟踪
        "stream": stream
    }
    
    if stream:
        return stream_response(url, payload)
    else:
        response = requests.post(url, headers=HEADERS, json=payload)
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]


def stream_response(url: str, payload: dict):
    """流式响应生成器"""
    response = requests.post(url, headers=HEADERS, json=payload, stream=True)
    response.raise_for_status()
    
    for line in response.iter_lines():
        if line:
            line = line.decode('utf-8')
            if line.startswith('data: '):
                data = line[6:]
                if data == '[DONE]':
                    break
                try:
                    chunk = json.loads(data)
                    if chunk["choices"][0]["delta"].get("content"):
                        yield chunk["choices"][0]["delta"]["content"]
                except json.JSONDecodeError:
                    continue


def list_models():
    """列出可用的模型/agents"""
    url = f"{GATEWAY_URL}/v1/models"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    return response.json()


# ============== 使用示例 ==============
if __name__ == "__main__":
    print("=== OpenClaw Python 客户端示例 ===\n")
    
    # 1. 列出可用模型
    print("1. 可用模型:")
    models = list_models()
    for model in models.get("data", []):
        print(f"   - {model['id']}")
    print()
    
    # 2. 发送普通消息
    print("2. 发送消息:")
    reply = send_message("你好，请用一句话介绍你自己")
    print(f"   OpenClaw: {reply}")
    print()
    
    # 3. 流式响应
    print("3. 流式响应:")
    print("   OpenClaw: ", end="", flush=True)
    for chunk in send_message("讲一个简短的笑话", stream=True):
        print(chunk, end="", flush=True)
    print("\n")
    
    # 4. 多轮对话（相同 user_id 保持会话）
    print("4. 多轮对话:")
    user_id = "conversation-1"
    
    msg1 = send_message("我想学习 Python，从哪里开始？", user_id=user_id)
    print(f"   Q: 我想学习 Python，从哪里开始？")
    print(f"   A: {msg1[:100]}...")
    
    msg2 = send_message("有什么推荐的在线资源吗？", user_id=user_id)
    print(f"\n   Q: 有什么推荐的在线资源吗？")
    print(f"   A: {msg2[:100]}...")
