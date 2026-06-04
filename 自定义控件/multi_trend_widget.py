#!/usr/bin/env python3
"""
multi_trend_widget.py — 工业级多通道实时趋势曲线 (Mini Designer v20+)
特性: 多通道/可改量程/格子背景/画布缩放/属性面板全控/零外部依赖
"""
import math, random
from collections import deque
from PySide6.QtCore import Qt, QTimer, Signal, QRectF, QPointF, QSize
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QBrush, QPainterPath, QWheelEvent
from PySide6.QtWidgets import QWidget, QSizePolicy

class MultiTrendWidget(QWidget):
    """工业级多通道实时趋势曲线 - 内置版"""
    
    # 标记为设计器可识别的显示名称
    _display_name = "多通道趋势曲线"
    
    dataUpdated = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_OpaquePaintEvent, True)
        self.setMinimumSize(200, 120)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMouseTracking(True)
        
        # ── 数据存储 ──
        self._channels = []  # [{"name": str, "color": QColor, "data": deque, "visible": bool}]
        self._window_size = 300
        
        # ── Y轴范围 (可通过属性面板修改) ──
        self._y_min = 0.0
        self._y_max = 100.0
        self._auto_scale = False
        
        # ── 外观配置 (可通过属性面板修改) ──
        self._bg_color = QColor("#1a1a2e")
        self._grid_color = QColor("#333355")
        self._text_color = QColor("#aaaacc")
        self._border_color = QColor("#444466")
        self._grid_density_x = 10  # X轴网格密度
        self._grid_density_y = 8   # Y轴网格密度
        
        # ── 交互状态 ──
        self._mouse_pos = None
        self._zoom_factor = 1.0
        
        # ── 演示定时器 ──
        self._demo_timer = QTimer(self)
        self._demo_timer.timeout.connect(self._demo_tick)
        self._demo_phase = 0.0
        
        # 初始化默认通道
        self.add_channel("温度", QColor("#4A90D9"))
        self.add_channel("压力", QColor("#E74C3C"))
        self.add_channel("流量", QColor("#27AE60"))
    
    # ════════════════════════════════════════════════════════════
    # 公开API
    # ════════════════════════════════════════════════════════════
    
    def add_channel(self, name: str, color: QColor = None):
        """添加数据通道"""
        colors = [QColor("#4A90D9"), QColor("#E74C3C"), QColor("#27AE60"), 
                  QColor("#F39C12"), QColor("#9B59B6"), QColor("#1ABC9C")]
        c = color or colors[len(self._channels) % len(colors)]
        self._channels.append({
            "name": name, "color": c, 
            "data": deque(maxlen=self._window_size), "visible": True
        })
        self.update()
    
    def remove_channel(self, index: int):
        if 0 <= index < len(self._channels):
            self._channels.pop(index)
            self.update()
    
    def set_y_range(self, y_min: float, y_max: float):
        """设置Y轴固定范围"""
        self._y_min = float(y_min)
        self._y_max = float(y_max)
        self._auto_scale = False
        self.update()
    
    def set_auto_scale(self, enabled: bool):
        """启用/禁用Y轴自动缩放"""
        self._auto_scale = bool(enabled)
        self.update()
    
    def set_bg_color(self, color_str: str):
        """设置背景色 (属性面板调用)"""
        try: self._bg_color = QColor(color_str); self.update()
        except: pass
    
    def set_grid_color(self, color_str: str):
        """设置网格色 (属性面板调用)"""
        try: self._grid_color = QColor(color_str); self.update()
        except: pass
    
    def set_text_color(self, color_str: str):
        """设置文字色 (属性面板调用)"""
        try: self._text_color = QColor(color_str); self.update()
        except: pass
    
    def set_grid_density_x(self, val: int):
        """设置X轴网格密度 (属性面板调用)"""
        self._grid_density_x = max(2, min(50, int(val))); self.update()
    
    def set_grid_density_y(self, val: int):
        """设置Y轴网格密度 (属性面板调用)"""
        self._grid_density_y = max(2, min(50, int(val))); self.update()
    
    def start_demo(self):
        if not self._demo_timer.isActive():
            self._demo_timer.start(50)  # 20Hz
    
    def stop_demo(self):
        self._demo_timer.stop()
    
    def add_value(self, channel_index: int, value: float):
        if 0 <= channel_index < len(self._channels):
            self._channels[channel_index]["data"].append(float(value))
            self.dataUpdated.emit()
            self.update()
    
    # ════════════════════════════════════════════════════════════
    # 内部方法
    # ════════════════════════════════════════════════════════════
    
    def _demo_tick(self):
        self._demo_phase += 0.05
        for i, ch in enumerate(self._channels):
            val = 50 + 30 * math.sin(self._demo_phase + i * 1.2) + random.uniform(-2, 2)
            self.add_value(i, val)
    
    def wheelEvent(self, event: QWheelEvent):
        if event.modifiers() & Qt.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0: self._zoom_factor = min(3.0, self._zoom_factor * 1.1)
            else: self._zoom_factor = max(0.3, self._zoom_factor / 1.1)
            self.update()
            event.accept()
        else:
            super().wheelEvent(event)
    
    def mouseMoveEvent(self, event):
        self._mouse_pos = event.position().toPoint()
        self.update()
    
    def leaveEvent(self, event):
        self._mouse_pos = None
        self.update()
    
    # ════════════════════════════════════════════════════════════
    # 绘制核心
    # ════════════════════════════════════════════════════════════
    
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        
        w, h = self.width(), self.height()
        margin_l, margin_r, margin_t, margin_b = 55, 15, 25, 30
        
        plot_w = (w - margin_l - margin_r) * self._zoom_factor
        plot_h = h - margin_t - margin_b
        
        if plot_w <= 0 or plot_h <= 0: return
        
        # ── 背景 ──
        p.fillRect(self.rect(), self._bg_color)
        
        # ── 计算Y轴范围 ──
        y_min, y_max = self._y_min, self._y_max
        if self._auto_scale and self._channels:
            all_vals = [v for ch in self._channels if ch["visible"] for v in ch["data"]]
            if all_vals:
                y_min = min(all_vals)
                y_max = max(all_vals)
                pad = (y_max - y_min) * 0.1 or 5.0
                y_min -= pad; y_max += pad
        
        y_range = y_max - y_min if y_max != y_min else 1.0
        
        # ── 网格 ──
        p.setPen(QPen(self._grid_color, 1, Qt.DotLine))
        for i in range(self._grid_density_y + 1):
            gy = margin_t + plot_h * i / self._grid_density_y
            p.drawLine(margin_l, int(gy), margin_l + plot_w, int(gy))
        for i in range(self._grid_density_x + 1):
            gx = margin_l + plot_w * i / self._grid_density_x
            p.drawLine(int(gx), margin_t, int(gx), margin_t + plot_h)
        
        # ── Y轴刻度 ──
        p.setPen(QPen(self._text_color, 1))
        font = QFont("Consolas", 8)
        p.setFont(font)
        for i in range(self._grid_density_y + 1):
            val = y_max - (y_range * i / self._grid_density_y)
            gy = margin_t + plot_h * i / self._grid_density_y
            p.drawText(2, int(gy) - 6, margin_l - 4, 12, 
                      Qt.AlignRight | Qt.AlignVCenter, f"{val:.1f}")
        
        # ── 边框 ──
        p.setPen(QPen(self._border_color, 1.5))
        p.drawRect(margin_l, margin_t, int(plot_w), int(plot_h))
        
        # ── 裁剪区域 ──
        p.setClipRect(margin_l, margin_t, int(plot_w), int(plot_h))
        
        # ── 绘制曲线 ──
        visible_chs = [ch for ch in self._channels if ch["visible"] and len(ch["data"]) >= 2]
        for ch in visible_chs:
            path = QPainterPath()
            n = len(ch["data"])
            step_x = plot_w / max(1, n - 1)
            
            for j, val in enumerate(ch["data"]):
                px = margin_l + j * step_x
                py = margin_t + plot_h * (1.0 - (val - y_min) / y_range)
                if j == 0: path.moveTo(px, py)
                else: path.lineTo(px, py)
            
            pen = QPen(ch["color"], 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            p.setPen(pen)
            p.drawPath(path)
        
        p.setClipping(False)
        
        # ── 图例 ──
        lx, ly = margin_l + 10, margin_t + 10
        legend_font = QFont("Microsoft YaHei", 8)
        p.setFont(legend_font)
        for ch in self._channels:
            if not ch["visible"]: continue
            p.setPen(QPen(ch["color"], 2))
            p.drawLine(lx, ly + 6, lx + 16, ly + 6)
            p.setPen(QPen(self._text_color, 1))
            p.drawText(lx + 20, ly + 3, ch["name"])
            ly += 16
        
        # ── 十字光标 + 数值提示 ──
        if self._mouse_pos and self.rect().contains(self._mouse_pos):
            mx, my = self._mouse_pos.x(), self._mouse_pos.y()
            if margin_l <= mx <= margin_l + plot_w and margin_t <= my <= margin_t + plot_h:
                p.setPen(QPen(QColor("#ffffff88"), 1, Qt.DashLine))
                p.drawLine(mx, margin_t, mx, margin_t + plot_h)
                p.drawLine(margin_l, my, margin_l + plot_w, my)
                
                y_val = y_max - ((my - margin_t) / plot_h) * y_range
                p.setPen(QPen(QColor("#ffffff"), 1))
                p.setFont(QFont("Consolas", 8))
                p.drawText(mx + 6, my - 6, f"{y_val:.2f}")
        
        p.end()
    
    def sizeHint(self): return QSize(400, 250)
    def minimumSizeHint(self): return QSize(150, 100)