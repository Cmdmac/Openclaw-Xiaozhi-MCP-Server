#!/usr/bin/env python3
"""
OpenClaw WebChat Python 客户端库
兼容 OpenAI API，支持普通/流式响应、会话跟踪、模型列表查询
"""
import requests
import json
from typing import Union, Generator, Optional


class OpenClawClient:
    """OpenClaw 客户端主类"""
    def __init__(
        self,
        gateway_url: str,
        api_token: str,
        model: str = "openclaw/default"
    ):
        """
        初始化客户端
        
        Args:
            gateway_url: OpenClaw 网关地址
            api_token: API 认证令牌
            model: 默认使用的模型/agent
        """
        self.base_url = gateway_url.rstrip("/")
        self.api_token = api_token
        self.model = model
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }

    def send_message(
        self,
        message: str,
        user_id: str = "xiaozhi-mcp",
        stream: bool = False
    ) -> Union[str, Generator[str, None, None]]:
        """
        发送消息到 OpenClaw
        
        Args:
            message: 用户消息
            user_id: 会话ID（保持多轮对话）
            stream: 是否流式响应
        
        Returns:
            普通响应返回字符串，流式返回生成器
        """
        url = f"{self.base_url}/v1/chat/completions"
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": message}],
            "user": user_id,
            "stream": stream
        }

        if stream:
            return self._stream_response(url, payload)
        
        # 普通非流式请求
        response = requests.post(url, headers=self.headers, json=payload)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

    def _stream_response(self, url: str, payload: dict) -> Generator[str, None, None]:
        """私有方法：处理流式响应"""
        response = requests.post(url, headers=self.headers, json=payload, stream=True)
        response.raise_for_status()

        for line in response.iter_lines():
            if line:
                line = line.decode("utf-8")
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        content = chunk["choices"][0]["delta"].get("content")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue

    def list_models(self) -> dict:
        """获取可用模型/agent列表"""
        url = f"{self.base_url}/v1/models"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()
