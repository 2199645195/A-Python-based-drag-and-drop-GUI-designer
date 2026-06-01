#!/usr/bin/env python
"""
MCP Vision Server — 通过阿里云百炼 Dashscope API（Qwen-VL）分析图片
MCP 协议：JSON-RPC 2.0 over stdio
"""

import base64
import json
import os
import sys
import requests

DASHSCOPE_API_KEY = os.environ.get("DASHSCOPE_API_KEY", "")
DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

def encode_image(image_path):
    """读取图片文件并返回 base64 编码"""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def analyze_image(image_path, question="请详细描述这张图片的内容"):
    """调用 Qwen-VL 分析图片"""
    base64_image = encode_image(image_path)
    
    # 获取文件扩展名作为格式提示
    ext = os.path.splitext(image_path)[1].lower()
    mime_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
    }
    mime = mime_map.get(ext, "image/png")
    data_url = f"data:{mime};base64,{base64_image}"

    headers = {
        "Authorization": f"Bearer {DASHSCOPE_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "qwen3-vl-flash",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": question},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }
        ],
    }

    resp = requests.post(
        f"{DASHSCOPE_BASE_URL}/chat/completions",
        headers=headers,
        json=payload,
        timeout=60,
    )
    resp.raise_for_status()
    result = resp.json()
    return result["choices"][0]["message"]["content"]


# === MCP Protocol Implementation (JSON-RPC over stdio) ===

def read_message():
    """从 stdin 读取一行 JSON-RPC 消息（UTF-8）"""
    line = sys.stdin.buffer.readline()
    if not line:
        return None
    return json.loads(line.decode("utf-8").strip())


def send_message(msg):
    """发送 JSON-RPC 消息到 stdout（UTF-8）"""
    content = json.dumps(msg, ensure_ascii=False)
    sys.stdout.buffer.write((content + "\n").encode("utf-8"))
    sys.stdout.buffer.flush()


def handle_initialize(msg):
    """处理 initialize 请求"""
    return {
        "jsonrpc": "2.0",
        "id": msg.get("id"),
        "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {},
            },
            "serverInfo": {
                "name": "mcp-vision-server",
                "version": "1.0.0",
            },
        },
    }


def handle_list_tools(msg):
    """处理 tools/list 请求"""
    return {
        "jsonrpc": "2.0",
        "id": msg.get("id"),
        "result": {
            "tools": [
                {
                    "name": "analyze_image",
                    "description": "分析图片内容 — 使用通义千问 Qwen-VL 多模态模型理解图片",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "image_path": {
                                "type": "string",
                                "description": "图片文件的完整路径",
                            },
                            "question": {
                                "type": "string",
                                "description": "关于图片的问题（可选，默认：请详细描述这张图片）",
                            },
                        },
                        "required": ["image_path"],
                    },
                }
            ]
        },
    }


def handle_call_tool(msg):
    """处理 tools/call 请求"""
    tool_name = msg["params"]["name"]
    arguments = msg["params"]["arguments"]

    if tool_name == "analyze_image":
        try:
            image_path = arguments["image_path"]
            question = arguments.get("question", "请详细描述这张图片的内容")
            result = analyze_image(image_path, question)
            return {
                "jsonrpc": "2.0",
                "id": msg.get("id"),
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": result,
                        }
                    ],
                },
            }
        except FileNotFoundError:
            return {
                "jsonrpc": "2.0",
                "id": msg.get("id"),
                "error": {
                    "code": -32000,
                    "message": f"文件未找到: {arguments['image_path']}",
                },
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": msg.get("id"),
                "error": {
                    "code": -32000,
                    "message": f"分析失败: {str(e)}",
                },
            }
    else:
        return {
            "jsonrpc": "2.0",
            "id": msg.get("id"),
            "error": {
                "code": -32601,
                "message": f"未知工具: {tool_name}",
            },
        }


def main():
    initialized = False
    while True:
        msg = read_message()
        if msg is None:
            break

        method = msg.get("method")
        msg_type = "request" if "id" in msg else "notification"

        if method == "initialize":
            resp = handle_initialize(msg)
            send_message(resp)
        elif method == "notifications/initialized":
            initialized = True
            # No response for notifications
        elif method == "tools/list":
            resp = handle_list_tools(msg)
            send_message(resp)
        elif method == "tools/call":
            resp = handle_call_tool(msg)
            send_message(resp)
        else:
            # Unknown method
            if msg_type == "request":
                send_message({
                    "jsonrpc": "2.0",
                    "id": msg.get("id"),
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}",
                    },
                })


if __name__ == "__main__":
    main()
