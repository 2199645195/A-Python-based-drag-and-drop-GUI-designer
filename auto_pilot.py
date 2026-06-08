#!/usr/bin/env python3
"""
Auto Pilot for Mini Designer v20
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
不再使用 pyautogui 模拟鼠标点击，改为：
  1. 将命令写入 gui_command.json
  2. Mini Designer 在 Qt 事件循环中轮询并直执行
  3. 等待 gui_response.json 获取执行结果

这样消除了屏幕坐标依赖，操作精确可靠。
支持将当前 Python 进程注入设计器进程（--inject 模式）或发送本地命令文件。
"""
import json
import os
import sys
import time
import subprocess
import uuid

# ── 配置 ──
COMMAND_FILE = "gui_command.json"
RESPONSE_FILE = "gui_response.json"
PREVIEW_FILE = "canvas_preview.png"
PYTHON_PATH = sys.executable  # 默认使用当前 Python
DESIGNER_SCRIPT = r"D:\GUI设计器\MiniDesigner\mini_designer.py"
POLL_INTERVAL = 0.1   # 轮询间隔（秒）
MAX_WAIT = 30         # 最大等待响应时间（秒）


def find_and_focus_designer():
    """使用 uiautomation 查找设计器窗口并激活"""
    try:
        from uiautomation import WindowControl
        win = WindowControl(searchDepth=1, Name="Mini Designer")
        if win.Exists():
            win.SetFocus()
            time.sleep(0.3)
            return True
    except ImportError:
        pass
    except Exception as e:
        print(f"[auto_pilot] 查找窗口异常: {e}")
    return False


def launch_designer():
    """启动 Mini Designer（如果未运行）"""
    if not os.path.exists(DESIGNER_SCRIPT):
        print(f"[auto_pilot] ⚠️ 未找到设计器脚本: {DESIGNER_SCRIPT}")
        print(f"[auto_pilot] 请在配置中设置正确的 DESIGNER_SCRIPT 路径")
        return False
    try:
        subprocess.Popen([PYTHON_PATH, DESIGNER_SCRIPT])
        print(f"[auto_pilot] 🚀 已启动 Mini Designer")
        time.sleep(2)  # 等待窗口创建
        return True
    except Exception as e:
        print(f"[auto_pilot] ❌ 启动失败: {e}")
        return False


def send_command(action, params=None):
    """
    向 Mini Designer 发送命令并等待执行结果。
    
    参数:
        action: 命令动作 (add_widget / delete_widget / move_widget / resize_widget
                / set_property / capture / save / get_canvas_info)
        params: 参数字典
    
    返回:
        dict: {status, message, ...} 或 None（超时）
    """
    cmd_id = str(uuid.uuid4())[:8]
    if params is None:
        params = {}

    command = {
        "id": cmd_id,
        "action": action,
        "params": params
    }

    # 清理旧的响应文件
    if os.path.exists(RESPONSE_FILE):
        try:
            os.remove(RESPONSE_FILE)
        except PermissionError:
            pass

    # 写入命令
    try:
        with open(COMMAND_FILE, "w", encoding="utf-8") as f:
            json.dump(command, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[auto_pilot] ❌ 写入命令失败: {e}")
        return None

    # 等待响应（带超时）
    deadline = time.time() + MAX_WAIT
    while time.time() < deadline:
        if os.path.exists(RESPONSE_FILE):
            try:
                with open(RESPONSE_FILE, "r", encoding="utf-8") as f:
                    result = json.load(f)
                os.remove(RESPONSE_FILE)
                return result
            except (json.JSONDecodeError, PermissionError):
                time.sleep(POLL_INTERVAL)
                continue
        time.sleep(POLL_INTERVAL)

    print(f"[auto_pilot] ⏰ 等待 '{action}' 响应超时 ({MAX_WAIT}s)")
    return None


def ensure_designer_ready():
    """确保设计器窗口已就绪，未启动则自动启动"""
    if find_and_focus_designer():
        return True
    print("[auto_pilot] 🔍 未找到设计器窗口，尝试启动...")
    if launch_designer():
        # 再次尝试获取焦点
        for _ in range(5):
            if find_and_focus_designer():
                return True
            time.sleep(1)
    return False


# ── 便捷命令封装 ──

def add_widget(widget_type="按钮", x=100, y=100, w=None, h=None, text=None, role=None, tag=None):
    """添加控件到画布"""
    params = {"widget_type": widget_type, "x": x, "y": y}
    if w is not None: params["w"] = w
    if h is not None: params["h"] = h
    if text is not None: params["text"] = text
    if role is not None: params["role"] = role
    if tag is not None: params["tag"] = tag
    return send_command("add_widget", params)


def delete_widget(name):
    """删除指定控件"""
    return send_command("delete_widget", {"objectName": name})


def move_widget(name, x, y):
    """移动控件到新位置"""
    return send_command("move_widget", {"objectName": name, "x": x, "y": y})


def resize_widget(name, w, h):
    """调整控件尺寸"""
    return send_command("resize_widget", {"objectName": name, "w": w, "h": h})


def set_property(name, prop, value):
    """修改控件属性"""
    return send_command("set_property", {"objectName": name, "property": prop, "value": value})


def capture():
    """截取画布截图"""
    return send_command("capture")


def save():
    """保存项目"""
    return send_command("save")


def get_canvas_info():
    """获取画布上所有控件信息"""
    return send_command("get_canvas_info")


def set_canvas_bg(path, scale="fit", opacity=100):
    """设置画布背景图"""
    return send_command("set_canvas_bg", {"path": path, "scale": scale, "opacity": opacity})


def clear_canvas_bg():
    """清除画布背景"""
    return send_command("clear_canvas_bg", {})


# ── CLI 入口 ──

def main():
    """CLI 模式：auto_pilot.py <action> [params...]"""
    if len(sys.argv) < 2:
        print("用法: python auto_pilot.py <action> [参数...]")
        print("")
        print("动作列表:")
        print("  add_widget   <type> <x> <y> [w h] [text]")
        print("  delete       <objectName>")
        print("  move         <objectName> <x> <y>")
        print("  resize       <objectName> <w> <h>")
        print("  setprop      <objectName> <prop> <value>")
        print("  capture")
        print("  save")
        print("  info")
        print("  set_bg       <path> [scale]  — 设置画布背景图")
        print("  clear_bg     — 清除画布背景")
        print("  demo         — 演示：创建示例界面")
        return

    action = sys.argv[1]

    if action == "add_widget":
        widget_type = sys.argv[2] if len(sys.argv) > 2 else "按钮"
        x = int(sys.argv[3]) if len(sys.argv) > 3 else 100
        y = int(sys.argv[4]) if len(sys.argv) > 4 else 100
        w = int(sys.argv[5]) if len(sys.argv) > 5 else None
        h = int(sys.argv[6]) if len(sys.argv) > 6 else None
        text = sys.argv[7] if len(sys.argv) > 7 else None
        r = add_widget(widget_type, x, y, w, h, text)
        print(json.dumps(r, ensure_ascii=False, indent=2))

    elif action == "delete":
        r = delete_widget(sys.argv[2])
        print(json.dumps(r, ensure_ascii=False, indent=2))

    elif action == "move":
        r = move_widget(sys.argv[2], int(sys.argv[3]), int(sys.argv[4]))
        print(json.dumps(r, ensure_ascii=False, indent=2))

    elif action == "resize":
        r = resize_widget(sys.argv[2], int(sys.argv[3]), int(sys.argv[4]))
        print(json.dumps(r, ensure_ascii=False, indent=2))

    elif action == "setprop":
        r = set_property(sys.argv[2], sys.argv[3], sys.argv[4])
        print(json.dumps(r, ensure_ascii=False, indent=2))

    elif action == "capture":
        ensure_designer_ready()
        r = capture()
        print(json.dumps(r, ensure_ascii=False, indent=2))

    elif action == "save":
        r = save()
        print(json.dumps(r, ensure_ascii=False, indent=2))

    elif action == "info":
        ensure_designer_ready()
        r = get_canvas_info()
        print(json.dumps(r, ensure_ascii=False, indent=2))

    elif action == "set_bg":
        path = sys.argv[2] if len(sys.argv) > 2 else ""
        scale = sys.argv[3] if len(sys.argv) > 3 else "fit"
        r = set_canvas_bg(path, scale)
        print(json.dumps(r, ensure_ascii=False, indent=2))

    elif action == "clear_bg":
        r = clear_canvas_bg()
        print(json.dumps(r, ensure_ascii=False, indent=2))

    elif action == "demo":
        _run_demo()

    else:
        print(f"未知动作: {action}")


def _run_demo():
    """演示：创建一个简单的工业监控界面"""
    if not ensure_designer_ready():
        print("❌ 设计器未就绪")
        return

    print("🚀 开始创建示例界面...")

    # 1. 添加标题标签
    r = add_widget("标签", 150, 20, 500, 50, text="🏭 工业监控系统 v20", tag="title")
    print(f"  {r.get('message', '')}")

    # 2. 实时趋势曲线
    r = add_widget("实时趋势曲线", 20, 80, 450, 220, tag="trend")
    print(f"  {r.get('message', '')}")

    # 3. 仪表盘
    r = add_widget("旋钮", 500, 80, 160, 160, tag="gauge1")
    print(f"  {r.get('message', '')}")

    # 3.5 图片背景框
    r = add_widget("图片背景框", 20, 320, 640, 170, tag="bg_frame")
    print(f"  {r.get('message', '')}")

    # 4. 按钮区域
    buttons = [("开始采集", "primary", "采集数据"), ("停止采集", "default", "停止"), ("导出报表", "outline", "导出")]
    for i, (text, role, tag) in enumerate(buttons):
        r = add_widget("按钮", 40 + i * 140, 335, 120, 36, text=text, role=role, tag=tag)
        print(f"  {r.get('message', '')}")

    # 5. 数据表格
    r = add_widget("表格控件", 20, 390, 640, 100, tag="data_table")
    print(f"  {r.get('message', '')}")

    # 6. 状态栏
    r = add_widget("标签", 30, 560, 400, 30, text="⏱ 系统就绪  |  192.168.1.100  |  Modbus TCP", tag="status")
    print(f"  {r.get('message', '')}")

    # 截图看看效果
    r = capture()
    if r and r.get("status") == "ok":
        print(f"📸 截图已保存: {PREVIEW_FILE} ({r.get('size', {}).get('w', '?')}x{r.get('size', {}).get('h', '?')})")

    print("✅ 示例界面创建完成！")


if __name__ == "__main__":
    main()
