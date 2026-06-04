#!/usr/bin/env python3
"""
Mini Designer - P&ID 图元库
SVG/矢量风格的工业阀门、泵、管路、电机等
"""
import math
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import (
    QPainter, QPen, QColor, QFont, QBrush, QPainterPath,
)
from PySide6.QtWidgets import QWidget


# ═══════════════════════════════════════════════════════════════
# 1. 球阀
# ═══════════════════════════════════════════════════════════════
class ValveBall(QWidget):
    """球阀 — 圆形阀体 + 开/关竖线指示"""
    _display_name = "球阀"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(40, 40)
        self._tag = ""; self._status_color = QColor("#4A90D9")
        self._line_color = QColor("#333"); self._fill_color = QColor("#e8e8e8")
        self._value = 0.0

    def setValue(self, v): self._value = float(v); self.update()
    def value(self): return self._value
    def setTag(self, t): self._tag = str(t); self.update()

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w / 2.0, h / 2.0; r = min(w, h) * 0.35
        # 阀体
        p.setPen(QPen(self._line_color, 2)); p.setBrush(QBrush(self._fill_color))
        p.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))
        # 阀杆
        p.setPen(QPen(self._status_color, 3))
        p.drawLine(QPointF(cx, cy - r * 0.6), QPointF(cx, cy + r * 0.6))
        # 标签
        if self._tag:
            p.setPen(QColor("#666")); p.setFont(QFont("Arial", 8))
            p.drawText(QRectF(0, h - 16, w, 14), Qt.AlignCenter, self._tag)
        p.end()


# ═══════════════════════════════════════════════════════════════
# 2. 闸阀
# ═══════════════════════════════════════════════════════════════
class ValveGate(QWidget):
    """闸阀 — 菱形"""
    _display_name = "闸阀"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(40, 40)
        self._tag = ""; self._status_color = QColor("#F39C12")
        self._line_color = QColor("#333"); self._fill_color = QColor("#e8e8e8")

    def setValue(self, v): self.update()
    def value(self): return 0.0

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w / 2.0, h / 2.0; s = min(w, h) * 0.35
        path = QPainterPath()
        path.moveTo(cx, cy - s); path.lineTo(cx + s, cy)
        path.lineTo(cx, cy + s); path.lineTo(cx - s, cy); path.closeSubpath()
        p.setPen(QPen(self._line_color, 2)); p.setBrush(QBrush(self._fill_color))
        p.drawPath(path)
        p.setPen(QPen(self._status_color, 3))
        p.drawLine(QPointF(cx, cy - s * 1.3), QPointF(cx, cy + s * 1.3))
        if self._tag:
            p.setPen(QColor("#666")); p.setFont(QFont("Arial", 8))
            p.drawText(QRectF(0, h - 16, w, 14), Qt.AlignCenter, self._tag)
        p.end()


# ═══════════════════════════════════════════════════════════════
# 3. 离心泵
# ═══════════════════════════════════════════════════════════════
class PumpCentrifugal(QWidget):
    """离心泵 — 圆形 + 三角箭头"""
    _display_name = "离心泵"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(40, 40)
        self._status_color = QColor("#27AE60")
        self._line_color = QColor("#333"); self._fill_color = QColor("#ddeeff")
        self._value = 0.0

    def setValue(self, v): self._value = float(v); self.update()
    def value(self): return self._value

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w / 2.0, h / 2.0; r = min(w, h) * 0.35
        p.setPen(QPen(self._line_color, 2)); p.setBrush(QBrush(self._fill_color))
        p.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))
        # 箭头
        ar = r * 0.3
        path = QPainterPath()
        path.moveTo(cx + ar, cy); path.lineTo(cx - ar, cy - ar)
        path.lineTo(cx - ar, cy + ar); path.closeSubpath()
        p.setPen(QPen(self._status_color, 2)); p.setBrush(QBrush(self._status_color))
        p.drawPath(path)
        # 管线
        p.setPen(QPen(self._line_color, 2))
        p.drawLine(QPointF(cx - r - 8, cy), QPointF(cx - r, cy))
        p.drawLine(QPointF(cx + r, cy), QPointF(cx + r + 8, cy))
        p.end()


# ═══════════════════════════════════════════════════════════════
# 4. 电机
# ═══════════════════════════════════════════════════════════════
class Motor(QWidget):
    """电机 — 矩形写 M"""
    _display_name = "电机"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(40, 40)
        self._status_color = QColor("#E74C3C")
        self._line_color = QColor("#333"); self._fill_color = QColor("#ffe0e0")
        self._value = 0.0

    def setValue(self, v): self._value = float(v); self.update()
    def value(self): return self._value

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        rect = QRectF(4, 4, w - 8, h - 8)
        p.setPen(QPen(self._status_color, 2)); p.setBrush(QBrush(self._fill_color))
        p.drawRoundedRect(rect, 4, 4)
        p.setPen(QPen(self._line_color, 2)); p.setFont(QFont("Arial", int(h * 0.4), QFont.Bold))
        p.drawText(rect, Qt.AlignCenter, "M")
        p.end()


# ═══════════════════════════════════════════════════════════════
# 5. 水平管道
# ═══════════════════════════════════════════════════════════════
class PipeHorizontal(QWidget):
    """水平管道 — 粗线 + 流向箭头"""
    _display_name = "水平管道"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(60, 16)
        self._status_color = QColor("#4A90D9")
        self._line_color = QColor("#555")

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height(); hh = h / 2.0
        p.setPen(QPen(self._line_color, 4, Qt.RoundCap))
        p.drawLine(QPointF(0, hh), QPointF(w, hh))
        if w > 60:
            cx = w / 2.0
            path = QPainterPath()
            path.moveTo(cx + 10, hh); path.lineTo(cx - 5, hh - 6)
            path.lineTo(cx - 5, hh + 6); path.closeSubpath()
            p.setPen(QPen(self._status_color, 2)); p.setBrush(QBrush(self._status_color))
            p.drawPath(path)
        p.end()


# ═══════════════════════════════════════════════════════════════
# 6. 垂直管道
# ═══════════════════════════════════════════════════════════════
class PipeVertical(QWidget):
    """垂直管道 — 粗线"""
    _display_name = "垂直管道"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(16, 60)
        self._line_color = QColor("#555")

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w = self.width() / 2.0
        p.setPen(QPen(self._line_color, 4, Qt.RoundCap))
        p.drawLine(QPointF(w, 0), QPointF(w, self.height()))
        p.end()


# ═══════════════════════════════════════════════════════════════
# 7. 储罐
# ═══════════════════════════════════════════════════════════════
class Tank(QWidget):
    """储罐 — 圆角矩形 + 液位"""
    _display_name = "储罐"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(50, 60)
        self._line_color = QColor("#333"); self._fill_color = QColor("#ddeeff")
        self._value = 60.0; self._tag = ""

    def setValue(self, v): self._value = max(0, min(100, float(v))); self.update()
    def value(self): return self._value
    def setTag(self, t): self._tag = str(t); self.update()

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        rect = QRectF(4, 10, w - 8, h - 20)
        p.setPen(QPen(self._line_color, 2)); p.setBrush(QBrush(self._fill_color))
        p.drawRoundedRect(rect, 6, 6)
        p.drawLine(QPointF(rect.left() + 8, rect.top()), QPointF(rect.right() - 8, rect.top()))
        level = rect.height() * self._value / 100.0
        p.setBrush(QBrush(QColor(74, 144, 217, 60))); p.setPen(Qt.NoPen)
        p.drawRect(QRectF(rect.left() + 2, rect.bottom() - level, rect.width() - 4, level))
        if self._tag:
            p.setPen(QColor("#333")); p.setFont(QFont("Arial", 8))
            p.drawText(QRectF(0, h - 16, w, 14), Qt.AlignCenter, self._tag)
        p.end()


# ═══════════════════════════════════════════════════════════════
# 8. 换热器
# ═══════════════════════════════════════════════════════════════
class HeatExchanger(QWidget):
    """换热器 — 矩形 + 内部管线"""
    _display_name = "换热器"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(40, 60)
        self._line_color = QColor("#333"); self._fill_color = QColor("#f0f0f0")

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w / 2.0, h / 2.0; r = min(w, h) * 0.3
        p.setPen(QPen(self._line_color, 2)); p.setBrush(QBrush(self._fill_color))
        p.drawRect(QRectF(cx - r, cy - r * 1.2, r * 2, r * 2.4))
        p.drawLine(QPointF(cx - r * 0.6, cy - r * 1.2), QPointF(cx - r * 0.6, cy + r * 1.2))
        p.drawLine(QPointF(cx + r * 0.6, cy - r * 1.2), QPointF(cx + r * 0.6, cy + r * 1.2))
        p.end()


# ═══════════════════════════════════════════════════════════════
# 9. 流量计
# ═══════════════════════════════════════════════════════════════
class FlowMeter(QWidget):
    """流量计 — 菱形 + F 字母"""
    _display_name = "流量计"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(36, 36)
        self._line_color = QColor("#333"); self._fill_color = QColor("#fff0d0")
        self._value = 0.0

    def setValue(self, v): self._value = float(v); self.update()
    def value(self): return self._value

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w / 2.0, h / 2.0; s = min(w, h) * 0.4
        path = QPainterPath()
        path.moveTo(cx, cy - s); path.lineTo(cx + s, cy)
        path.lineTo(cx, cy + s); path.lineTo(cx - s, cy); path.closeSubpath()
        p.setPen(QPen(self._line_color, 2)); p.setBrush(QBrush(self._fill_color))
        p.drawPath(path)
        p.setPen(QPen(self._line_color, 2))
        p.setFont(QFont("Arial", int(s * 0.8), QFont.Bold))
        p.drawText(QRectF(cx - s, cy - s, s * 2, s * 2), Qt.AlignCenter, "F")
        p.end()


# ═══════════════════════════════════════════════════════════════
# 10. 温度变送器
# ═══════════════════════════════════════════════════════════════
class TemperatureTransmitter(QWidget):
    """温度变送器 — 圆形 + T 字母"""
    _display_name = "温度变送器"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(36, 36)
        self._line_color = QColor("#333"); self._fill_color = QColor("#ffd0d0")
        self._value = 0.0

    def setValue(self, v): self._value = float(v); self.update()
    def value(self): return self._value

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w / 2.0, h / 2.0; r = min(w, h) * 0.4
        p.setPen(QPen(self._line_color, 2)); p.setBrush(QBrush(self._fill_color))
        p.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))
        p.setPen(QPen(self._line_color, 2))
        p.setFont(QFont("Arial", int(r * 0.8), QFont.Bold))
        p.drawText(QRectF(cx - r, cy - r, r * 2, r * 2), Qt.AlignCenter, "T")
        p.end()
