#!/usr/bin/env python3
"""
MCP Server for Mini Designer v20
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
允许 AI 助手通过 MCP 工具协议与 Mini Designer 交互：
  - 读取设计状态 (JSON project file)
  - 截取画布截图 (base64 PNG，AI 能"看见"界面)
  - 执行设计操作 (添加/删除/移动/缩放控件、修改属性)
  - 分析布局结构

通信方式：通过 gui_command.json → gui_response.json 与设计器进程通信
设计器在 Qt 事件循环中轮询命令并直接执行（不再依赖 pyautogui 模拟鼠标）
"""
import json
import os
import sys
import time
import uuid
import base64
from typing import Any, List

import subprocess
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Resource, Tool, TextContent

# ── Windows GBK 编码兼容 ──
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

app = Server("mini-designer-mcp-v2")

# ── 配置 ──
# 设计器运行时 CWD 是项目根目录，MCP 命令文件必须放在同一位置
MCP_WORK_DIR = r"D:\GUI设计器"
os.makedirs(MCP_WORK_DIR, exist_ok=True)
PROJECT_FILE = os.path.join(MCP_WORK_DIR, "untitled.json")
COMMAND_FILE = os.path.join(MCP_WORK_DIR, "gui_command.json")
RESPONSE_FILE = os.path.join(MCP_WORK_DIR, "gui_response.json")
PREVIEW_FILE = os.path.join(MCP_WORK_DIR, "canvas_preview.png")
POLL_INTERVAL = 0.15
MAX_WAIT = 15  # 每次命令等待最大秒数
# 设计器路径
DESIGNER_SCRIPT = r"D:\GUI设计器\MiniDesigner\mini_designer.py"
DESIGNER_EXE = r"D:\xiazairuanjian\MiniDesigner\MiniDesigner.exe"
PYTHON_PATH = sys.executable


_designer_proc = None

def _ensure_designer_running():
    """检查设计器是否在运行，不在则自动启动"""
    global _designer_proc
    # 先发一个轻量命令测试是否活着
    probe = _send_command_raw("get_canvas_info", {}, wait_sec=2)
    if probe.get("status") == "ok":
        return True
    # 没响应，尝试启动
    launcher = None
    if os.path.exists(DESIGNER_EXE):
        launcher = [DESIGNER_EXE]
    elif os.path.exists(DESIGNER_SCRIPT):
        launcher = [PYTHON_PATH, DESIGNER_SCRIPT]
    else:
        print(f"[MCP] 设计器未找到: {DESIGNER_EXE} / {DESIGNER_SCRIPT}")
        return False
    try:
        print(f"[MCP] 🚀 正在启动 Mini Designer...")
        _designer_proc = subprocess.Popen(launcher, cwd=MCP_WORK_DIR,
                                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # 等待设计器启动并开始轮询命令
        import time as _time
        _time.sleep(3)
        # 再试一次
        probe = _send_command_raw("get_canvas_info", {}, wait_sec=3)
        if probe.get("status") == "ok":
            print(f"[MCP] ✅ Mini Designer 已启动并就绪")
            return True
        else:
            print(f"[MCP] ⚠️ 设计器已启动但未响应命令，请检查窗口是否正常打开")
            return True  # 窗口可能已打开，继续
    except Exception as e:
        print(f"[MCP] ❌ 启动设计器失败: {e}")
        return False


def _send_command_raw(action, params, wait_sec=MAX_WAIT):
    """发送命令并轮询响应，不自动启动设计器"""
    cmd_id = str(uuid.uuid4())[:8]
    if params is None:
        params = {}
    command = {"id": cmd_id, "action": action, "params": params}
    for f in [RESPONSE_FILE]:
        if os.path.exists(f):
            try: os.remove(f)
            except: pass
    try:
        with open(COMMAND_FILE, "w", encoding="utf-8") as f:
            json.dump(command, f, ensure_ascii=False, indent=2)
    except Exception as e:
        return {"status": "error", "message": f"写入命令失败: {e}"}
    deadline = time.time() + wait_sec
    while time.time() < deadline:
        if os.path.exists(RESPONSE_FILE):
            try:
                with open(RESPONSE_FILE, "r", encoding="utf-8") as f:
                    result = json.load(f)
                os.remove(RESPONSE_FILE)
                return result
            except (json.JSONDecodeError, PermissionError, OSError):
                time.sleep(POLL_INTERVAL)
                continue
        time.sleep(POLL_INTERVAL)
    return {"status": "error", "message": "timeout"}


def _send_command(action: str, params: dict = None) -> dict:
    """向 Mini Designer 发送命令，如果设计器未运行则自动启动"""
    result = _send_command_raw(action, params, wait_sec=MAX_WAIT)
    if result.get("status") == "error" and "timeout" in result.get("message", ""):
        print(f"[MCP] 设计器未响应，尝试自动启动...")
        if _ensure_designer_running():
            result = _send_command_raw(action, params, wait_sec=MAX_WAIT)
            if result.get("status") == "ok":
                return result
    return result


def _load_project_file() -> dict:
    """读取项目 JSON 文件"""
    if not os.path.exists(PROJECT_FILE):
        return {"error": "未找到项目文件。请先在 Mini Designer 中打开/保存一个项目。", "pages": []}
    try:
        with open(PROJECT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return {"error": f"读取项目文件失败: {e}", "pages": []}


# ── Resources ──

@app.list_resources()
async def list_resources() -> List[Resource]:
    return [
        Resource(
            uri=f"file://./{PROJECT_FILE}",
            name="Current Project State",
            mimeType="application/json",
            description="设计器当前项目状态 (JSON)。读取此文件可了解布局结构。"
        ),
        Resource(
            uri=f"file://./{PREVIEW_FILE}",
            name="Canvas Preview Image",
            mimeType="image/png",
            description="画布最新截图。调用 capture_canvas_preview 工具后会更新此文件。"
        )
    ]


@app.read_resource()
async def read_resource(uri: str) -> str:
    if PROJECT_FILE in uri:
        data = _load_project_file()
        return json.dumps(data, ensure_ascii=False, indent=2)
    elif PREVIEW_FILE in uri:
        if os.path.exists(PREVIEW_FILE):
            try:
                with open(PREVIEW_FILE, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode()
                return b64
            except Exception as e:
                return json.dumps({"error": f"读取截图失败: {e}"})
        else:
            return json.dumps({"error": "截图文件不存在。请先调用 capture_canvas_preview 工具。"})
    raise ValueError(f"Unknown resource: {uri}")


# ── Tools ──

@app.list_tools()
async def list_tools() -> List[Tool]:
    return [
        Tool(
            name="get_widget_summary",
            description="获取当前设计中所有控件的摘要列表（名称、类型、位置）",
            inputSchema={"type": "object", "properties": {}, "required": []}
        ),
        Tool(
            name="find_widget_by_name",
            description="通过 objectName 或 tag 搜索控件详情",
            inputSchema={
                "type": "object",
                "properties": {
                    "name_query": {"type": "string", "description": "要搜索的 objectName 或 tag（部分匹配）"}
                },
                "required": ["name_query"]
            }
        ),
        Tool(
            name="analyze_layout_structure",
            description="分析 GUI 的层次结构和布局",
            inputSchema={"type": "object", "properties": {}, "required": []}
        ),
        Tool(
            name="execute_gui_action",
            description="执行 GUI 设计操作。直接在画布上添加/删除/移动/缩放控件或修改属性。操作直接在设计器内执行，无需模拟鼠标。",
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": [
                            "new_project", "add_widget", "delete_widget", "move_widget",
                            "resize_widget", "set_property", "set_canvas_size",
                            "capture", "save", "set_canvas_bg", "clear_canvas_bg"
                        ],
                        "description": "操作类型：new_project=新建项目清空画布 | add_widget=添加控件 | delete_widget=删除 | move/resize=移动缩放 | set_property=改属性 | set_canvas_size=设置画布尺寸 | capture=截图 | save=保存 | set_canvas_bg=设置画布背景图(path) | clear_canvas_bg=清除画布背景",
                    },
                    "widget_type": {
                        "type": "string",
                        "description": "控件类型（add_widget 用）：'按钮' / '标签' / '单行输入框' / '下拉框' / '复选框' / '单选按钮' / '滑块' / '进度条' / '表格控件' / '树形控件' / '列表控件' / '分组框' / '实时趋势曲线' / '旋钮' / '液晶数字显示' / '日历控件' / '框架' / '图片背景框' / '水平布局容器' / '垂直布局容器' 等"
                    },
                    "objectName": {
                        "type": "string",
                        "description": "控件的 objectName（delete/move/resize/set_property 用）"
                    },
                    "x": {"type": "number", "description": "X 坐标"},
                    "y": {"type": "number", "description": "Y 坐标"},
                    "w": {"type": "number", "description": "宽度"},
                    "h": {"type": "number", "description": "高度"},
                    "text": {"type": "string", "description": "显示文本"},
                    "role": {
                        "type": "string",
                        "enum": ["default", "primary", "success", "warning", "danger", "outline", "ghost"],
                        "description": "控件角色（影响按钮配色等）"
                    },
                    "property": {
                        "type": "string",
                        "description": "要修改的属性名（set_property 用）：text / objectName / role / tag / styleSheet / x / y / w / h / image_path / scale_mode / opacity / bg_color"
                    },
                    "value": {
                        "type": "string",
                        "description": "属性新值（set_property 用）"
                    },
                    "bg_path": {
                        "type": "string",
                        "description": "背景图片路径（set_canvas_bg 用）"
                    },
                    "bg_scale": {
                        "type": "string",
                        "description": "背景缩放模式（set_canvas_bg 用）：fit / stretch / tile / center"
                    },
                    "bg_opacity": {
                        "type": "number",
                        "description": "背景透明度 0-100（set_canvas_bg 用）"
                    }
                },
                "required": ["action"]
            }
        ),
        Tool(
            name="capture_canvas_preview",
            description="截取画布当前状态的截图并返回 base64 PNG。调用后 AI 可以'看到'界面实际渲染效果。返回格式：{status, message, image_base64(可选), size}",
            inputSchema={
                "type": "object",
                "properties": {
                    "include_base64": {
                        "type": "boolean",
                        "description": "是否在返回中包含 base64 图片数据（设为 true 时 AI 可以直接查看截图）"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="get_widget_list",
            description="获取画布上所有控件的详细列表（含位置、尺寸、文本、角色、锁定状态）",
            inputSchema={"type": "object", "properties": {}, "required": []}
        ),
        Tool(
            name="quick_demo",
            description="创建一个示例工业监控界面作为演示（自动添加标签、趋势曲线、按钮、表格等）",
            inputSchema={"type": "object", "properties": {}, "required": []}
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> List[TextContent]:
    
    # ── 读取型工具（直接从 JSON 文件读取） ──

    if name == "get_widget_summary":
        data = _load_project_file()
        if "error" in data:
            return [TextContent(type="text", text=f"⚠️ {data['error']}")]
        
        summary = []
        pages = data.get("pages", [])
        if not pages:
            summary.append("📄 空项目（无页面）")
        for page in pages:
            summary.append(f"📄 页面: {page.get('name', '未命名')}")
            for w in page.get("widgets", []):
                summary.append(
                    f"  - 🧩 {w.get('display_name', '?')} "
                    f"| Name: `{w.get('objectName', '?')}` "
                    f"| ({w.get('x',0)}, {w.get('y',0)}) "
                    f"{w.get('w',0)}x{w.get('h',0)}"
                    f"{' | 📝 ' + w.get('text','') if w.get('text') else ''}"
                    f"{' | 🏷 ' + w.get('tag','') if w.get('tag') else ''}"
                )
            if not page.get("widgets"):
                summary.append("  (空页面)")
        
        if len(summary) > 50:
            summary = summary[:50] + [f"... (共 {len(data.get('pages',[]))} 页，仅显示前50行)"]
            
        return [TextContent(type="text", text="\n".join(summary))]


    elif name == "find_widget_by_name":
        query = arguments.get("name_query", "").lower()
        data = _load_project_file()
        if "error" in data:
            return [TextContent(type="text", text=f"⚠️ {data['error']}")]
        
        results = []
        for page in data.get("pages", []):
            for w in page.get("widgets", []):
                obj_name = w.get("objectName", "").lower()
                tag = w.get("tag", "").lower()
                display = w.get("display_name", "").lower()
                if query in obj_name or query in tag or query in display:
                    results.append(json.dumps(w, ensure_ascii=False, indent=2))
                    
        if not results:
            return [TextContent(type="text", text=f"未找到匹配 '{query}' 的控件")]
        return [TextContent(type="text", text=f"找到 {len(results)} 个匹配:\n\n" + "\n---\n".join(results))]


    elif name == "analyze_layout_structure":
        data = _load_project_file()
        if "error" in data:
            return [TextContent(type="text", text=f"⚠️ {data['error']}")]
        
        analysis = []
        total_widgets = 0
        for page in data.get("pages", []):
            analysis.append(f"📄 页面: {page['name']}")
            widgets = page.get("widgets", [])
            total_widgets += len(widgets)
            containers = [w for w in widgets if w.get('children')]
            if containers:
                analysis.append(f"  📦 容器控件 ({len(containers)} 个):")
                for c in containers:
                    children = c.get('children', [])
                    analysis.append(f"    - {c['objectName']} ({c['display_name']}) 含 {len(children)} 个子控件")
            else:
                analysis.append("  ℹ️ 无嵌套容器")
        
        analysis.append(f"\n📊 总计: {len(data.get('pages',[]))} 页, {total_widgets} 个控件")
        analysis.append(f"🎨 画布尺寸: {data.get('design_width', 800)} x {data.get('design_height', 600)}")
        
        return [TextContent(type="text", text="\n".join(analysis))]


    # ── 操作型工具（通过命令协议与设计器交互） ──

    elif name == "execute_gui_action":
        action = arguments.get("action", "")
        
        # 构建命令参数
        params = {}
        for key in ("widget_type", "objectName", "x", "y", "w", "h", "text", "role", "property", "value", "tag", "bg_path", "bg_scale", "bg_opacity", "path", "scale", "opacity"):
            if key in arguments and arguments[key] is not None:
                params[key] = arguments[key]
        
        # 映射旧版 action_type → action（兼容）
        if not action and "action_type" in arguments:
            mapping = {
                "drag_widget": "add_widget",
                "set_property": "set_property"
            }
            action = mapping.get(arguments["action_type"], arguments["action_type"])
            params["widget_type"] = params.get("widget_type") or arguments.get("widget_name")
            # 旧版 drag_widget 用 target_x/target_y
            if "target_x" in arguments:
                params["x"] = arguments["target_x"]
            if "target_y" in arguments:
                params["y"] = arguments["target_y"]
            if "property_name" in arguments:
                params["property"] = arguments["property_name"]
            if "property_value" in arguments:
                params["value"] = arguments["property_value"]

        if not action:
            return [TextContent(type="text", text="❌ 请指定 action 参数")]

        result = _send_command(action, params)
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]


    elif name == "capture_canvas_preview":
        # 触发设计器截图
        result = _send_command("capture")
        include_b64 = arguments.get("include_base64", False)
        
        if result.get("status") != "ok":
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]
        
        response = {
            "status": "ok",
            "message": f"截图成功: {result.get('file', PREVIEW_FILE)} ({result.get('size', {}).get('w', '?')}x{result.get('size', {}).get('h', '?')})",
            "size": result.get("size", {})
        }

        # 如果请求 base64，读取图片文件
        if include_b64 and os.path.exists(PREVIEW_FILE):
            try:
                with open(PREVIEW_FILE, "rb") as f:
                    response["image_base64"] = base64.b64encode(f.read()).decode()
                response["message"] += f" (base64: {len(response['image_base64'])} bytes)"
            except Exception as e:
                response["warning"] = f"读取图片失败: {e}"

        return [TextContent(type="text", text=json.dumps(response, ensure_ascii=False, indent=2))]


    elif name == "get_widget_list":
        result = _send_command("get_canvas_info")
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]


    elif name == "quick_demo":
        result = _send_command("add_widget", {"widget_type": "标签", "x": 150, "y": 20, "w": 500, "h": 50, "text": "🏭 工业监控系统 v20", "tag": "title"})
        _send_command("add_widget", {"widget_type": "实时趋势曲线", "x": 20, "y": 80, "w": 450, "h": 220, "tag": "trend"})
        _send_command("add_widget", {"widget_type": "旋钮", "x": 500, "y": 80, "w": 160, "h": 160, "tag": "gauge1"})
        _send_command("add_widget", {"widget_type": "图片背景框", "x": 20, "y": 320, "w": 640, "h": 160, "tag": "bg_frame"})
        _send_command("add_widget", {"widget_type": "按钮", "x": 40, "y": 340, "w": 120, "h": 36, "text": "开始采集", "role": "primary", "tag": "start_btn"})
        _send_command("add_widget", {"widget_type": "按钮", "x": 180, "y": 340, "w": 120, "h": 36, "text": "停止采集", "tag": "stop_btn"})
        _send_command("add_widget", {"widget_type": "表格控件", "x": 20, "y": 380, "w": 640, "h": 100, "tag": "data_table"})
        _send_command("add_widget", {"widget_type": "标签", "x": 30, "y": 500, "w": 400, "h": 30, "text": "⏱ 系统就绪  |  192.168.1.100  |  Modbus TCP", "tag": "status"})
        cap = _send_command("capture")
        return [TextContent(type="text", text=json.dumps({
            "status": "ok",
            "message": "示例界面已创建！请调用 capture_canvas_preview 查看效果。",
            "capture": cap
        }, ensure_ascii=False, indent=2))]


    else:
        raise ValueError(f"未知工具: {name}")


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
