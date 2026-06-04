#!/usr/bin/env python3
"""
Mini Designer - 实时趋势曲线控件
多通道、滚动窗口、缩放、游标读数
"""
import math, time
from collections import deque

from PySide6.QtCore import Qt, QRectF, QPointF, QTimer, Signal
from PySide6.QtGui import (
    QPainter, QPen, QColor, QFont, QFontMetrics, QBrush,
    QLinearGradient,
)
from PySide6.QtWidgets import QWidget, QSizePolicy


# ═══════════════════════════════════════════════════════════════
# 通道颜色
# ═══════════════════════════════════════════════════════════════
CHANNEL_COLORS = ["#00FF88", "#FF4444", "#4488FF", "#FFAA00",
                  "#FF66AA", "#66FF66", "#AA66FF", "#FFDD44"]


# ═══════════════════════════════════════════════════════════════
# 实时趋势曲线
# ═══════════════════════════════════════════════════════════════
class TrendWidget(QWidget):
    """实时趋势曲线 — 多通道/滚动窗口/缩放/游标读数"""
    _display_name = "趋势曲线"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(200, 150)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WA_StyledBackground, False)
        self.setAttribute(Qt.WA_OpaquePaintEvent, True)

        self._channels = []
        self._time_window = 60.0
        self._show_grid = True
        self._show_legend = True
        self._crosshair_pos = None
        self._is_panning = False
        self._pan_start = None

        self._bg_color = QColor("#1a1a2e")
        self._grid_color = QColor("#2a2a3e")
        self._text_color = QColor("#aaaacc")
        self._border_color = QColor("#3a3a5e")

        self._demo_timer = QTimer(self)
        self._demo_timer.timeout.connect(self._demo_tick)
        self._demo_time = 0

        # 默认两个通道
        self.add_channel("CH1", CHANNEL_COLORS[0])
        self.add_channel("CH2", CHANNEL_COLORS[1])

    # ── 通道管理 ──
    def add_channel(self, name, color=None, max_points=500):
        ch = {"name": name, "color": color or CHANNEL_COLORS[len(self._channels) % 8],
              "data": deque(maxlen=max_points), "min": 0.0, "max": 100.0}
        self._channels.append(ch)
        return ch

    def clear_data(self):
        for ch in self._channels:
            ch["data"].clear()
        self.update()

    def add_value(self, channel_index, value, timestamp=None):
        if 0 <= channel_index < len(self._channels):
            ts = timestamp if timestamp is not None else time.time()
            self._channels[channel_index]["data"].append((ts, value))
            vals = [v for _, v in self._channels[channel_index]["data"]]
            if vals:
                margin = (max(vals) - min(vals)) * 0.1 or 10
                self._channels[channel_index]["min"] = min(vals) - margin
                self._channels[channel_index]["max"] = max(vals) + margin
            self.update()

    def set_time_window(self, seconds):
        self._time_window = max(5, min(3600, float(seconds)))

    def time_window(self):
        return self._time_window

    # ── 预览 ──
    def start(self):
        self._demo_time = 0
        self._demo_timer.start(100)

    def stop(self):
        self._demo_timer.stop()

    def _demo_tick(self):
        self._demo_time += 0.1
        ts = time.time()
        for i, ch in enumerate(self._channels):
            val = 50 + 30 * math.sin(self._demo_time * 0.5 + i * 2.1) \
                  + 10 * math.sin(self._demo_time * 0.13 + i * 0.7)
            ch["data"].append((ts, val))
            vals = [v for _, v in ch["data"]]
            if vals:
                margin = (max(vals) - min(vals)) * 0.1 or 10
                ch["min"] = min(vals) - margin
                ch["max"] = max(vals) + margin
        self.update()

    # ── 绘制 ──
    def paintEvent(self, e):
        if self.width() < 10 or self.height() < 10 or not self.isVisible() or not self.paintEngine():
            super().paintEvent(e)
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        ml, mr, mt, mb = 50, 20, 20, 50
        pr = QRectF(ml, mt, w - ml - mr, h - mt - mb)

        # 背景 + 边框
        p.fillRect(self.rect(), self._bg_color)
        p.setPen(QPen(QColor("#4A90D9"), 2))
        p.drawRect(self.rect().adjusted(1, 1, -1, -1))
        p.fillRect(pr, QColor("#1e1e32"))
        p.setPen(QPen(self._border_color, 1))
        p.drawRect(pr)

        if not self._channels:
            p.setPen(self._text_color)
            p.drawText(self.rect(), Qt.AlignCenter, "无数据")
            p.end(); return

        # 网格
        if self._show_grid:
            p.setPen(QPen(self._grid_color, 1, Qt.DotLine))
            for i in range(5):
                y = pr.top() + pr.height() * i / 4
                p.drawLine(QPointF(pr.left(), y), QPointF(pr.right(), y))
            for i in range(7):
                x = pr.left() + pr.width() * i / 6
                p.drawLine(QPointF(x, pr.top()), QPointF(x, pr.bottom()))

        # 收集所有数据
        all_vals = [v for ch in self._channels for _, v in ch["data"]]
        if not all_vals:
            p.setPen(self._text_color)
            p.drawText(pr, Qt.AlignCenter, "等待数据...")
            p.end(); return

        y_min = min(all_vals); y_max = max(all_vals)
        if y_max - y_min < 1: y_min -= 5; y_max += 5

        # 绘制每条曲线
        for ch in self._channels:
            data = list(ch["data"])
            if len(data) < 2: continue
            p.setPen(QPen(QColor(ch["color"]), 2))
            t_end = data[-1][0] if data else time.time()
            t_start = t_end - self._time_window
            pts = []
            for t, v in data:
                if t < t_start: continue
                x = pr.left() + ((t - t_start) / self._time_window) * pr.width()
                y = pr.bottom() - ((v - y_min) / (y_max - y_min)) * pr.height()
                pts.append(QPointF(x, y))
            for i in range(1, len(pts)):
                p.drawLine(pts[i - 1], pts[i])

        # Y 轴标签
        font = QFont("Consolas", 9); p.setFont(font)
        for i in range(5):
            val = y_max - (y_max - y_min) * i / 4
            y = pr.top() + pr.height() * i / 4
            p.setPen(self._text_color)
            p.drawText(QRectF(2, y - 8, ml - 5, 16), Qt.AlignRight | Qt.AlignVCenter, f"{val:.1f}")

        # X 轴标签
        for i in range(4):
            t_off = self._time_window * i / 3
            x = pr.left() + pr.width() * i / 3
            p.setPen(self._text_color)
            p.drawText(QRectF(x - 25, pr.bottom() + 5, 50, 20), Qt.AlignCenter, f"-{self._time_window - t_off:.0f}s")

        # 图例
        if self._show_legend:
            ly = h - 22; lx = pr.left()
            for ci, ch in enumerate(self._channels):
                p.setPen(QPen(QColor(ch["color"]), 3))
                p.drawLine(lx, ly, lx + 20, ly)
                p.setPen(self._text_color); p.setFont(QFont("Arial", 9))
                p.drawText(QRectF(lx + 24, ly - 8, 70, 16), Qt.AlignLeft, ch["name"])
                lx += 90

        # 游标
        if self._crosshair_pos:
            cx, cy = self._crosshair_pos
            if pr.contains(cx, cy):
                p.setPen(QPen(Qt.white, 1, Qt.DashLine))
                p.drawLine(QPointF(cx, pr.top()), QPointF(cx, pr.bottom()))
                p.drawLine(QPointF(pr.left(), cy), QPointF(pr.right(), cy))
                val = y_max - ((cy - pr.top()) / pr.height()) * (y_max - y_min)
                t_off = self._time_window * (1 - (cx - pr.left()) / pr.width())
                p.setPen(Qt.white); p.setFont(QFont("Consolas", 9))
                p.drawText(QRectF(cx + 5, cy - 20, 120, 18), Qt.AlignLeft, f"值: {val:.1f}")
                p.drawText(QRectF(cx + 5, cy - 2, 120, 18), Qt.AlignLeft, f"时间: -{t_off:.0f}s")
        p.end()

    # ── 鼠标交互 ──
    def mouseMoveEvent(self, e):
        if self._is_panning and self._pan_start:
            dx = e.position().x() - self._pan_start.x()
            self._time_window = max(5, self._time_window - dx * 0.1)
            self._pan_start = e.position().toPoint()
            self.update()
        else:
            self._crosshair_pos = (e.position().x(), e.position().y())
            self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._is_panning = True
            self._pan_start = e.position().toPoint()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._is_panning = False; self._pan_start = None

    def wheelEvent(self, e):
        d = e.angleDelta().y()
        self._time_window = max(5, min(3600, self._time_window * (0.9 if d > 0 else 1.1)))
        self.update(); e.accept()
