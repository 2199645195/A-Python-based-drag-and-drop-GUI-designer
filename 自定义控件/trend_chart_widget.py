#!/usr/bin/env python3
"""
trend_chart_widget.py — 工业级实时趋势曲线自定义控件 (Mini Designer v20+ 适配版)

使用方法:
    1. 在 Mini Designer 中点击 "🧩 自定义控件" → "📂 添加文件" → 选择本文件
    2. 工具箱底部会出现 "⭐ 自定义控件" 分类，拖拽 "实时趋势曲线" 到画布即可
    3. 预览模式下自动播放演示数据；数据模拟器中选择对应 Tag 即可驱动
"""

import math
import random
from collections import deque

from PySide6.QtCore import Qt, QTimer, Signal, QPointF, QLineF, QRectF
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPolygonF, QBrush, QPalette
from PySide6.QtWidgets import QWidget, QSizePolicy


class TrendChartWidget(QWidget):
    """
    工业级实时趋势曲线控件 (已适配 Mini Designer v20)
    
    特性:
        - 多通道数据叠加显示
        - 滚动窗口 + 自动/手动Y轴缩放
        - 网格线 + Y轴刻度 + 标题 + 图例
        - 鼠标悬停十字线 + 实时读数
        - 纯 QPainter 软件渲染，无GPU依赖
        - 内置演示模式（预览时自动启动）
        - 【新增】完全支持 QSS 样式表定制 (背景/边框/文字颜色)
    """
    
    # 标记为设计器可识别的显示名称
    _display_name = "实时趋势曲线"
    
    # 预定义通道颜色
    COLORS = [
        QColor("#4A90D9"), QColor("#27AE60"), QColor("#E74C3C"),
        QColor("#F39C12"), QColor("#9B59B6"), QColor("#1ABC9C"),
        QColor("#E67E22"), QColor("#3498DB"), QColor("#2ECC71"), QColor("#E91E63"),
    ]
    
    dataUpdated = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # ── 【核心修复】开启不透明绘制，防止设计器拖拽时产生残影/花屏 ──
        self.setAttribute(Qt.WA_OpaquePaintEvent, True)
        
        # ── 基本设置 ──
        self.setMinimumSize(200, 120)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMouseTracking(True)
        
        # ── 数据存储 ──
        self._channels: dict[str, deque] = {}          
        self._channel_colors: dict[str, QColor] = {}   
        self._window_size: int = 200
        
        # ── Y轴范围 ──
        self._y_min: float = 0.0
        self._y_max: float = 100.0
        self._auto_scale: bool = True
        
        # ── 显示开关 ──
        self._grid_visible: bool = True
        self._legend_visible: bool = True
        self._title: str = ""
        
        # ── 运行状态 ──
        self._running: bool = False
        
        # ── 鼠标交互 ──
        self._mouse_pos = None
        
        # ── 演示定时器 ──
        self._demo_timer = QTimer(self)
        self._demo_timer.timeout.connect(self._demo_tick)
        self._demo_phase: float = 0.0
    
    # ════════════════════════════════════════════════════════════
    # 公开API (保持原有接口不变)
    # ════════════════════════════════════════════════════════════
    
    def addChannel(self, name: str, color=None):
        if name not in self._channels:
            self._channels[name] = deque(maxlen=self._window_size)
            idx = len(self._channel_colors) % len(self.COLORS)
            self._channel_colors[name] = color or self.COLORS[idx]
            self.update()
    
    def removeChannel(self, name: str):
        self._channels.pop(name, None)
        self._channel_colors.pop(name, None)
        self.update()
    
    def clearChannels(self):
        self._channels.clear()
        self._channel_colors.clear()
        self.update()
    
    def addValue(self, channel_name: str, value: float):
        if channel_name not in self._channels:
            self.addChannel(channel_name)
        self._channels[channel_name].append(float(value))
        if self._running or self._demo_timer.isActive():
            self.update()
        self.dataUpdated.emit()
    
    def setWindowSize(self, size: int):
        self._window_size = max(10, int(size))
        for ch in self._channels.values():
            old_data = list(ch)
            ch.clear()
            ch.extend(old_data[-self._window_size:])
        self.update()
    
    def setYRange(self, y_min: float, y_max: float):
        self._y_min = float(y_min)
        self._y_max = float(y_max)
        self._auto_scale = False
        self.update()
    
    def setAutoScale(self, enabled: bool):
        self._auto_scale = bool(enabled)
        self.update()
    
    def setTitle(self, title: str):
        self._title = str(title)
        self.update()
    
    def setGridVisible(self, visible: bool):
        self._grid_visible = bool(visible)
        self.update()
    
    def setLegendVisible(self, visible: bool):
        self._legend_visible = bool(visible)
        self.update()
    
    def start(self):
        """启动实时更新或演示模式 (适配设计器预览按钮)"""
        self._running = True
        # 如果没有外部数据源，且当前没有通道，则自动进入演示模式
        if not self._channels and not self._demo_timer.isActive():
            self.startDemo()
    
    def stop(self):
        """停止更新 (适配设计器退出预览)"""
        self._running = False
        self.stopDemo()
    
    def startDemo(self):
        if not self._channels:
            self.addChannel("温度")
            self.addChannel("压力")
            self.addChannel("流量")
        self._demo_timer.start(100)
    
    def stopDemo(self):
        self._demo_timer.stop()
    
    # ════════════════════════════════════════════════════════════
    # 内部方法
    # ════════════════════════════════════════════════════════════
    
    def _demo_tick(self):
        self._demo_phase += 0.1
        channels = list(self._channels.keys())[:3]
        for i, name in enumerate(channels):
            val = 50 + 30 * math.sin(self._demo_phase + i * 1.5) + random.uniform(-2, 2)
            self.addValue(name, val)
    
    # ════════════════════════════════════════════════════════════
    # 绘制 (已增加 QSS 样式支持)
    # ════════════════════════════════════════════════════════════
    
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        
        w, h = self.width(), self.height()
        
        # ── 【边界保护】防止尺寸为0时崩溃 ──
        if w < 10 or h < 10:
            return
            
        margin_left = 50
        margin_right = 10
        margin_top = 24 if self._title else 10
        margin_bottom = 20
        
        plot_w = w - margin_left - margin_right
        plot_h = h - margin_top - margin_bottom
        
        if plot_w <= 0 or plot_h <= 0:
            return
        
        # ── 【核心修复】从 QSS/Palette 动态获取颜色 ──
        # 优先使用 styleSheet 中定义的 background，否则使用调色板
        bg_color = self.palette().color(QPalette.Window)
        border_color = self.palette().color(QPalette.Mid)
        text_color = self.palette().color(QPalette.Text)
        grid_color = QColor(border_color.red(), border_color.green(), border_color.blue(), 80)
        
        # 尝试解析 styleSheet 中的特定属性 (简易解析)
        ss = self.styleSheet()
        if "background" in ss or "background-color" in ss:
            import re
            match = re.search(r'background(?:-color)?\s*:\s*(#[0-9a-fA-F]{3,8})', ss)
            if match: bg_color = QColor(match.group(1))
        if "color:" in ss:
            match = re.search(r'\bcolor\s*:\s*(#[0-9a-fA-F]{3,8})', ss)
            if match: text_color = QColor(match.group(1))
        if "border" in ss:
            match = re.search(r'border[^;]*?(\#[0-9a-fA-F]{3,8})', ss)
            if match: border_color = QColor(match.group(1))

        # ── 背景填充 (消除花屏的关键) ──
        p.fillRect(self.rect(), bg_color)
        p.setPen(QPen(border_color, 1))
        p.drawRect(self.rect().adjusted(0, 0, -1, -1))
        
        # ── 计算Y轴范围 ──
        y_min, y_max = self._y_min, self._y_max
        if self._auto_scale and self._channels:
            all_vals = []
            for ch_data in self._channels.values():
                all_vals.extend(ch_data)
            if all_vals:
                y_min = min(all_vals)
                y_max = max(all_vals)
                padding = (y_max - y_min) * 0.1 or 5.0
                y_min -= padding
                y_max += padding
        
        y_range = y_max - y_min if y_max != y_min else 1.0
        
        # ── 网格线 ──
        if self._grid_visible:
            p.setPen(QPen(grid_color, 1, Qt.DotLine))
            for i in range(1, 5):
                gy = margin_top + plot_h * i / 5
                p.drawLine(margin_left, int(gy), margin_left + plot_w, int(gy))
            for i in range(1, 5):
                gx = margin_left + plot_w * i / 5
                p.drawLine(int(gx), margin_top, int(gx), margin_top + plot_h)
        
        # ── Y轴刻度标签 ──
        p.setPen(QPen(text_color, 1))
        font = QFont("Microsoft YaHei", 8) # 改用微软雅黑以更好支持中文
        p.setFont(font)
        for i in range(6):
            val = y_max - (y_range * i / 5)
            gy = margin_top + plot_h * i / 5
            p.drawText(2, int(gy) - 6, margin_left - 4, 12,
                       Qt.AlignRight | Qt.AlignVCenter, f"{val:.1f}")
        
        # ── 标题 ──
        if self._title:
            p.setPen(QPen(text_color, 1))
            title_font = QFont("Microsoft YaHei", 9, QFont.Bold)
            p.setFont(title_font)
            p.drawText(margin_left, 2, plot_w, 20,
                       Qt.AlignLeft | Qt.AlignVCenter, self._title)
        
        # ── 绘制曲线 ──
        p.setClipRect(margin_left, margin_top, plot_w, plot_h)
        for ch_name, ch_data in self._channels.items():
            if len(ch_data) < 2:
                continue
            color = self._channel_colors.get(ch_name, self.COLORS[0])
            p.setPen(QPen(color, 2, Qt.SolidLine))
            
            points = QPolygonF()
            n = len(ch_data)
            for j, val in enumerate(ch_data):
                px = margin_left + (j / max(n - 1, 1)) * plot_w
                py = margin_top + (1.0 - (val - y_min) / y_range) * plot_h
                points.append(QPointF(px, py))
            
            p.drawPolyline(points)
        
        p.setClipping(False)
        
        # ── 图例 ──
        if self._legend_visible and self._channels:
            lx = margin_left + 8
            ly = margin_top + 4
            legend_font = QFont("Microsoft YaHei", 8)
            p.setFont(legend_font)
            for ch_name, color in self._channel_colors.items():
                if ch_name not in self._channels:
                    continue
                p.setPen(QPen(color, 2))
                p.drawLine(lx, ly + 6, lx + 16, ly + 6)
                p.setPen(QPen(text_color, 1))
                p.drawText(lx + 20, ly, 100, 14,
                           Qt.AlignLeft | Qt.AlignVCenter, ch_name)
                ly += 16
                if ly > margin_top + plot_h - 10:
                    break
        
        # ── 鼠标十字线 + 读数 ──
        if self._mouse_pos and self.rect().contains(self._mouse_pos):
            mx, my = self._mouse_pos.x(), self._mouse_pos.y()
            if (margin_left <= mx <= margin_left + plot_w and
                    margin_top <= my <= margin_top + plot_h):
                crosshair_color = QColor(text_color.red(), text_color.green(), text_color.blue(), 100)
                p.setPen(QPen(crosshair_color, 1, Qt.DashLine))
                p.drawLine(mx, margin_top, mx, margin_top + plot_h)
                p.drawLine(margin_left, my, margin_left + plot_w, my)
                
                y_val = y_max - ((my - margin_top) / plot_h) * y_range
                p.setPen(QPen(text_color, 1))
                p.setFont(QFont("Consolas", 8))
                p.drawText(mx + 4, my - 4, f"{y_val:.2f}")
        
        p.end()
    
    # ════════════════════════════════════════════════════════════
    # 鼠标事件
    # ════════════════════════════════════════════════════════════
    
    def mouseMoveEvent(self, event):
        self._mouse_pos = event.position().toPoint()
        self.update()
        super().mouseMoveEvent(event)
    
    def leaveEvent(self, event):
        self._mouse_pos = None
        self.update()
        super().leaveEvent(event)