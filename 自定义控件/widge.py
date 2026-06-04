#!/usr/bin/env python3
"""
my_widgets.py — 自定义控件库
包含：缺失的Qt原生控件 + 自创工业/UI控件
拖入 mini_designer.py 的「🧩 自定义控件」即可使用
"""

import math
import random
from collections import deque

from PySide6.QtCore import Qt, Signal, QRect, QRectF, QPoint, QPointF, QSize, QTimer, QTime, QDateTime
from PySide6.QtGui import (
    QPainter, QPen, QColor, QFont, QFontMetrics, QKeySequence,
    QBrush, QLinearGradient, QRadialGradient, QConicalGradient, QPainterPath,
)
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QFrame, QColorDialog, QFileDialog, QFontComboBox, QKeySequenceEdit,
    QScrollBar, QListView, QTableView, QGraphicsView, QGraphicsScene,
    QAbstractItemView, QHeaderView, QSpinBox, QSlider, QComboBox, QCheckBox,
    QSizePolicy, QApplication, QMessageBox,
)


# ═══════════════════════════════════════════════════════════════
# 第一部分：工业监控与数据可视化控件
# ═══════════════════════════════════════════════════════════════

class GaugeWidget(QWidget):
    """
    P13: 仪表盘控件 (GaugeWidget)
    工业圆形/弧形仪表控件 — 支持多阈值颜色、刻度、指针
    """
    valueChanged = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._min_val = 0
        self._max_val = 100
        self._value = 50
        self._unit = ""
        self._title = "仪表"
        self._gauge_color = QColor("#4A90D9")
        self._warning_color = QColor("#F39C12")
        self._danger_color = QColor("#E74C3C")
        self._warning_threshold = 70
        self._danger_threshold = 90
        self._start_angle = 225
        self._span_angle = 270
        self._tick_count = 10
        self._decimals = 1
        self.setMinimumSize(120, 120)

    def setValue(self, v):
        self._value = max(self._min_val, min(self._max_val, float(v)))
        self.valueChanged.emit(self._value)
        self.update()

    def value(self): return self._value
    def setRange(self, mn, mx): self._min_val = float(mn); self._max_val = float(mx); self.update()
    def minimum(self): return self._min_val
    def maximum(self): return self._max_val
    def setUnit(self, u): self._unit = str(u); self.update()
    def setGaugeTitle(self, t): self._title = str(t); self.update()
    def setGaugeColor(self, c): self._gauge_color = QColor(c); self.update()
    def setDecimals(self, d): self._decimals = int(d); self.update()
    def intValue(self): return int(self._value)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        margin = 20
        side = min(w, h) - margin * 2
        if side < 40: return
        
        cx, cy = w / 2.0, h / 2.0
        radius = side / 2.0
        pen_w = max(6, int(radius / 10))

        # Background Arc
        bg_pen = QPen(QColor("#e8e8e8"), pen_w)
        bg_pen.setCapStyle(Qt.RoundCap)
        p.setPen(bg_pen)
        p.setBrush(Qt.NoBrush)
        p.drawArc(QRectF(cx - radius, cy - radius, radius * 2, radius * 2),
                  int(self._start_angle * 16), int(self._span_angle * 16))

        # Value Arc
        ratio = ((self._value - self._min_val) / (self._max_val - self._min_val)) if self._max_val > self._min_val else 0
        ratio = max(0.0, min(1.0, ratio))
        
        if self._value >= self._danger_threshold:
            arc_color = self._danger_color
        elif self._value >= self._warning_threshold:
            arc_color = self._warning_color
        else:
            arc_color = self._gauge_color
            
        val_pen = QPen(arc_color, pen_w)
        val_pen.setCapStyle(Qt.RoundCap)
        p.setPen(val_pen)
        p.drawArc(QRectF(cx - radius, cy - radius, radius * 2, radius * 2),
                  int(self._start_angle * 16), int(self._span_angle * ratio * 16))

        # Ticks
        tick_pen = QPen(QColor("#999"), max(1, int(radius / 60)))
        p.setPen(tick_pen)
        for i in range(self._tick_count + 1):
            ang = (self._start_angle + self._span_angle * i / self._tick_count) * math.pi / 180.0
            inner_r = radius - pen_w - 4
            outer_r = radius - 2
            x1 = cx + inner_r * math.cos(ang)
            y1 = cy - inner_r * math.sin(ang)
            x2 = cx + outer_r * math.cos(ang)
            y2 = cy - outer_r * math.sin(ang)
            p.drawLine(QPointF(x1, y1), QPointF(x2, y2))

        # Labels
        for i in range(0, self._tick_count + 1, max(1, self._tick_count // 5)):
            ang = (self._start_angle + self._span_angle * i / self._tick_count) * math.pi / 180.0
            val = self._min_val + (self._max_val - self._min_val) * i / self._tick_count
            label_r = radius - 14
            lx = cx + label_r * math.cos(ang)
            ly = cy - label_r * math.sin(ang)
            p.setFont(QFont("Microsoft YaHei", max(7, int(radius / 14))))
            p.setPen(QColor("#666"))
            p.drawText(QPointF(lx - 14, ly - 8), 28, 16, Qt.AlignCenter, f"{val:.{self._decimals}f}")
            p.setPen(tick_pen)

        # Needle
        needle_angle = (self._start_angle + self._span_angle * ratio) * math.pi / 180.0
        needle_len = radius - max(8, int(radius / 8))
        nx = cx + needle_len * 0.8 * math.cos(needle_angle)
        ny = cy - needle_len * 0.8 * math.sin(needle_angle)
        needle_pen = QPen(QColor("#333"), max(2, int(radius / 40)))
        p.setPen(needle_pen)
        p.drawLine(QPointF(cx, cy), QPointF(nx, ny))

        # Hub
        hub_r = max(6, int(radius / 12))
        p.setBrush(QColor("#333"))
        p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(cx, cy), hub_r, hub_r)
        p.setBrush(QColor("#fff"))
        p.drawEllipse(QPointF(cx, cy), hub_r * 0.5, hub_r * 0.5)

        # Text Values
        p.setPen(QColor("#333"))
        p.setFont(QFont("Microsoft YaHei", max(9, int(radius / 8)), QFont.Bold))
        val_text = f"{self._value:.{self._decimals}f}{self._unit}"
        fm = QFontMetrics(p.font())
        val_y = cy + radius * 0.15
        tw = fm.horizontalAdvance(val_text)
        p.drawText(QRectF(cx - tw / 2.0, val_y - fm.height() / 2.0, tw * 1.0, fm.height() * 1.0), Qt.AlignCenter, val_text)

        if self._title:
            p.setFont(QFont("Microsoft YaHei", max(7, int(radius / 16))))
            p.setPen(QColor("#888"))
            p.drawText(QRectF(cx - 50, val_y + max(14, int(radius / 12)), 100, 18), Qt.AlignCenter, self._title)
        
        p.end()

    def sizeHint(self): return QSize(160, 160)
    def minimumSizeHint(self): return QSize(100, 100)


class CurveWidget(QWidget):
    """
    P14: 实时曲线控件 (CurveWidget)
    实时趋势曲线控件 — 多通道、自动滚动、纯QPainter渲染
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self._title = "实时曲线"
        self._channels = [
            {"name": "通道1", "color": QColor("#4A90D9"), "data": deque(maxlen=300)},
            {"name": "通道2", "color": QColor("#E74C3C"), "data": deque(maxlen=300)},
        ]
        self._x_range = 60
        self._y_min = 0.0
        self._y_max = 100.0
        self._auto_range = True
        self._grid_color = QColor("#e8e8e8")
        self._bg_color = QColor("#ffffff")
        self._tick_count = 0
        self._running = False
        self._demo_timer = QTimer(self)
        self._demo_timer.timeout.connect(self._demo_tick)
        self._demo_phase = 0.0
        self.setMinimumSize(200, 150)

    def start(self):
        if not self._running:
            self._running = True
            self._demo_timer.start(100)

    def stop(self):
        self._running = False
        self._demo_timer.stop()

    def isRunning(self): return self._running

    def _demo_tick(self):
        self._demo_phase += 0.3
        v0 = 50 + 30 * math.sin(self._demo_phase * 0.7) + random.uniform(-3, 3)
        v1 = 30 + 20 * math.cos(self._demo_phase * 0.5) + random.uniform(-2, 2)
        self.addValues([v0, v1])
        if len(self._channels) > 2:
            self.addValue(2, 60 + 25 * math.sin(self._demo_phase * 0.3 + 1))
        self._tick_count += 1
        self.update()

    def setTitle(self, t): self._title = str(t); self.update()
    def title(self): return self._title

    def addValue(self, channel_index, value):
        if 0 <= channel_index < len(self._channels):
            self._channels[channel_index]["data"].append(value)
            self._tick_count += 1
            if self._tick_count % 5 == 0: self.update()

    def addValues(self, values):
        for i, v in enumerate(values):
            if i < len(self._channels):
                self._channels[i]["data"].append(v)
                self._tick_count += 1
                if self._tick_count % 5 == 0: self.update()

    def setChannelCount(self, n):
        colors = [QColor("#4A90D9"), QColor("#E74C3C"), QColor("#27AE60"), QColor("#F39C12"), QColor("#9B59B6"), QColor("#1ABC9C")]
        while len(self._channels) < n:
            idx = len(self._channels)
            self._channels.append({"name": f"通道{idx + 1}", "color": colors[idx % len(colors)], "data": deque(maxlen=300)})
        self._channels = self._channels[:max(1, n)]
        self.update()

    def setRange(self, y_min, y_max):
        self._y_min = float(y_min)
        self._y_max = float(y_max)
        self._auto_range = False
        self.update()

    def minimum(self): return self._y_min
    def maximum(self): return self._y_max

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        margin_l, margin_r, margin_t, margin_b = 45, 15, 25, 30
        pw = w - margin_l - margin_r
        ph = h - margin_t - margin_b
        if pw <= 0 or ph <= 0: return

        p.fillRect(0, 0, w, h, self._bg_color)

        # Grid
        p.setPen(QPen(self._grid_color, 1))
        for i in range(5):
            y = margin_t + ph * i / 4.0
            p.drawLine(QPointF(margin_l, y), QPointF(w - margin_r, y))
        for i in range(6):
            x = margin_l + pw * i / 5.0
            p.drawLine(QPointF(x, margin_t), QPointF(x, h - margin_b))
        
        p.setPen(QPen(QColor("#ccc"), 1.5))
        p.drawRect(margin_l, margin_t, pw, ph)

        # Auto Range Calculation
        if self._auto_range:
            all_vals = []
            for ch in self._channels: all_vals.extend(ch["data"])
            if all_vals:
                mn, mx = min(all_vals), max(all_vals)
                pad = max((mx - mn) * 0.1, 1.0)
                self._y_min, self._y_max = mn - pad, mx + pad
            else:
                self._y_min, self._y_max = 0.0, 100.0

        y_range = self._y_max - self._y_min or 1.0

        # Y-Axis Labels
        p.setFont(QFont("Microsoft YaHei", 8))
        p.setPen(QColor("#666"))
        for i in range(5):
            val = self._y_max - y_range * i / 4.0
            y = margin_t + ph * i / 4.0
            p.drawText(QRectF(2, y - 8, margin_l - 6, 16), Qt.AlignRight | Qt.AlignVCenter, f"{val:.1f}")

        # Draw Curves
        for ch_idx, ch in enumerate(self._channels):
            data = list(ch["data"])
            if len(data) < 2: continue
            pen = QPen(ch["color"], 2)
            p.setPen(pen)
            n = len(data)
            for i in range(1, n):
                x1 = margin_l + pw * (i - 1) / max(1, n - 1)
                x2 = margin_l + pw * i / max(1, n - 1)
                y1 = margin_t + ph * (1.0 - (data[i - 1] - self._y_min) / y_range)
                y2 = margin_t + ph * (1.0 - (data[i] - self._y_min) / y_range)
                y1v = max(margin_t, min(margin_t + ph, y1))
                y2v = max(margin_t, min(margin_t + ph, y2))
                p.drawLine(QPointF(x1, y1v), QPointF(x2, y2v))
            
            # Draw last point dot
            if data:
                last_x = margin_l + pw
                last_y = margin_t + ph * (1.0 - (data[-1] - self._y_min) / y_range)
                last_y = max(margin_t, min(margin_t + ph, last_y))
                p.setBrush(ch["color"])
                p.setPen(Qt.NoPen)
                p.drawEllipse(QPointF(last_x, last_y), 3, 3)

        # Title
        if self._title:
            p.setFont(QFont("Microsoft YaHei", 9, QFont.Bold))
            p.setPen(QColor("#333"))
            p.drawText(QRectF(margin_l, 2, pw, margin_t - 2), Qt.AlignCenter, self._title)

        # Legend
        legend_x = margin_l + 4
        legend_y = margin_t + 4
        p.setFont(QFont("Microsoft YaHei", 8))
        for ch in self._channels:
            p.setPen(Qt.NoPen)
            p.setBrush(ch["color"])
            p.drawRect(int(legend_x), int(legend_y), 10, 10)
            p.setPen(QColor("#333"))
            p.drawText(QRectF(legend_x + 14, legend_y, 60, 12), Qt.AlignLeft, ch["name"])
            legend_y += 14
        
        p.end()

    def sizeHint(self): return QSize(320, 200)
    def minimumSizeHint(self): return QSize(200, 100)


# ═══════════════════════════════════════════════════════════════
# 第二部分：基础交互与输入控件
# ═══════════════════════════════════════════════════════════════

class KeySequenceEdit(QWidget):
    """1. 快捷键捕获器 (KeySequenceEdit) - 快捷键输入框"""
    _display_name = "快捷键捕获器"
    keyChanged = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(30)
        self._keys = ""
        self._recording = False
        self.setStyleSheet(
            "KeySequenceEdit{background:#fff;border:1px solid #d0d0d0;border-radius:4px;padding:4px 8px;font-size:12px;}"
        )
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("点击后按下快捷键组合")

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = self.rect().adjusted(1, 1, -1, -1)
        p.setBrush(QColor("#f0f8ff" if self._recording else "#fff"))
        p.setPen(QPen(QColor("#4A90D9" if self._recording else "#d0d0d0"), 2 if self._recording else 1))
        p.drawRoundedRect(QRectF(r), 4, 4)
        p.setPen(QColor("#999" if not self._keys else "#333"))
        p.setFont(QFont("Consolas", 11))
        display = "按下快捷键..." if self._recording else (self._keys or "点击设置快捷键")
        p.drawText(r, Qt.AlignCenter, display)
        p.end()

    def mousePressEvent(self, e):
        self._recording = True
        self._keys = ""
        self.update()

    def keyPressEvent(self, e):
        if not self._recording: return super().keyPressEvent(e)
        parts = []
        if e.modifiers() & Qt.ControlModifier: parts.append("Ctrl")
        if e.modifiers() & Qt.ShiftModifier: parts.append("Shift")
        if e.modifiers() & Qt.AltModifier: parts.append("Alt")
        if e.modifiers() & Qt.MetaModifier: parts.append("Meta")
        key = e.key()
        if key not in (Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Meta, Qt.Key_unknown):
            key_str = QKeySequence(key).toString()
            if key_str:
                parts.append(key_str)
                self._keys = "+".join(parts)
                self._recording = False
                self.keyChanged.emit(self._keys)
                self.update()


class FontComboBox(QWidget):
    """2. 字体选择器 (FontComboBox) - 字体下拉选择框"""
    _display_name = "字体选择器"
    fontChanged = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        self.combo = QFontComboBox()
        self.combo.setMinimumHeight(28)
        self.combo.setStyleSheet("QFontComboBox{padding:3px 6px;font-size:12px;}")
        self.combo.currentFontChanged.connect(lambda f: self.fontChanged.emit(f.family()))
        layout.addWidget(self.combo)
        self.sample = QLabel("Aa")
        self.sample.setMinimumWidth(36)
        self.sample.setAlignment(Qt.AlignCenter)
        self.sample.setStyleSheet("QLabel{background:#f5f5f5;border:1px solid #ddd;border-radius:4px;font-size:14px;}")
        self.combo.currentFontChanged.connect(lambda f: self.sample.setFont(f))
        layout.addWidget(self.sample)

    def currentFont(self): return self.combo.currentFont()
    def setCurrentFont(self, f): self.combo.setCurrentFont(f)


class HorizontalScrollBar(QScrollBar):
    """3. 独立滚动条 - 水平滚动条"""
    _display_name = "水平滚动条"
    def __init__(self, parent=None):
        super().__init__(Qt.Horizontal, parent)
        self.setRange(0, 100)
        self.setValue(0)
        self.setMinimumHeight(18)


class VerticalScrollBar(QScrollBar):
    """3. 独立滚动条 - 垂直滚动条"""
    _display_name = "垂直滚动条"
    def __init__(self, parent=None):
        super().__init__(Qt.Vertical, parent)
        self.setRange(0, 100)
        self.setValue(0)
        self.setMinimumWidth(18)


class ToggleSwitch(QWidget):
    """4. 开关控件 (ToggleSwitch) - iOS风格开关"""
    _display_name = "滑动开关"
    toggled = Signal(bool)
    valueChanged = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._checked = False
        self._on_color = QColor("#27AE60")
        self._off_color = QColor("#ccc")
        self.setFixedSize(52, 28)
        self.setCursor(Qt.PointingHandCursor)

    def isChecked(self): return self._checked
    def setChecked(self, v):
        self._checked = bool(v)
        self.toggled.emit(self._checked)
        self.valueChanged.emit(self._checked)
        self.update()
    def value(self): return 1 if self._checked else 0
    def setValue(self, v): self.setChecked(bool(v))

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = self.rect().adjusted(2, 2, -2, -2)
        track_color = self._on_color if self._checked else self._off_color
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#e0e0e0") if not self._checked else track_color.lighter(150))
        p.drawRoundedRect(QRectF(r), r.height() / 2, r.height() / 2)
        knob_r = r.height() - 4
        knob_x = r.right() - knob_r - 2 if self._checked else r.left() + 2
        p.setBrush(track_color)
        p.drawEllipse(QPointF(knob_x + knob_r / 2, r.center().y()), knob_r / 2, knob_r / 2)
        p.end()

    def mousePressEvent(self, e):
        self.setChecked(not self._checked)

    def setText(self, t): pass  # 兼容
    def sizeHint(self): return QSize(52, 28)


class IPAddressEdit(QWidget):
    """11. IP地址输入框 - IP地址4段输入"""
    _display_name = "IP地址输入框"
    ipChanged = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        self._octets = []
        for i in range(4):
            sb = QSpinBox()
            sb.setRange(0, 255)
            sb.setValue(192 if i == 0 else 168 if i == 1 else 0)
            sb.setMinimumWidth(50)
            sb.setAlignment(Qt.AlignCenter)
            sb.setStyleSheet("QSpinBox{padding:3px;font-size:12px;font-family:Consolas;}")
            sb.valueChanged.connect(lambda v, idx=i: self._on_change(idx, v))
            layout.addWidget(sb)
            self._octets.append(sb)
            if i < 3:
                dot = QLabel(".")
                dot.setStyleSheet("font-weight:bold;font-size:14px;")
                dot.setAlignment(Qt.AlignCenter)
                dot.setFixedWidth(8)
                layout.addWidget(dot)
        layout.addStretch()

    def ip(self):
        return ".".join(str(o.value()) for o in self._octets)
    
    def setIP(self, ip_str):
        parts = ip_str.split(".")
        for i, p in enumerate(parts[:4]):
            try: self._octets[i].setValue(int(p))
            except: pass
            
    def _on_change(self, idx, val):
        self.ipChanged.emit(self.ip())

    def setText(self, t): self.setIP(t)  # 兼容
    def text(self): return self.ip()


# ═══════════════════════════════════════════════════════════════
# 第三部分：状态指示与显示控件
# ═══════════════════════════════════════════════════════════════

class LedIndicator(QWidget):
    """5. LED指示灯 - 圆形LED指示灯 — 支持多颜色和闪烁"""
    _display_name = "LED指示灯"
    LED_COLORS = {
        "red": QColor("#E74C3C"), "green": QColor("#27AE60"), "yellow": QColor("#F39C12"),
        "blue": QColor("#4A90D9"), "white": QColor("#ecf0f1"), "orange": QColor("#E67E22"),
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._color = QColor("#27AE60")
        self._on = True
        self._blinking = False
        self._blink_timer = QTimer(self)
        self._blink_timer.timeout.connect(lambda: (setattr(self, '_on', not self._on), self.update()))
        self.setFixedSize(28, 28)

    def setColor(self, name):
        self._color = self.LED_COLORS.get(name, QColor(name))
        self.update()

    def setOn(self, on): self._on = on; self.update()
    def setChecked(self, v): self.setOn(bool(v))
    def setBlinking(self, enable):
        self._blinking = enable
        if enable: self._blink_timer.start(500)
        else: self._blink_timer.stop(); self._on = True; self.update()
    def setValue(self, v): self.setOn(bool(v))
    def value(self): return 1 if self._on else 0

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        s = min(self.width(), self.height()) - 4
        cx, cy = self.width() / 2, self.height() / 2
        r = s / 2
        # glow
        glow = QRadialGradient(cx, cy, r * 1.4)
        c = self._color if self._on else QColor("#888")
        glow.setColorAt(0, c.lighter(180)); glow.setColorAt(0.7, c); glow.setColorAt(1, QColor(0, 0, 0, 0))
        p.setBrush(glow); p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(cx, cy), r * 1.3, r * 1.3)
        # main
        body = QRadialGradient(cx - r * 0.3, cy - r * 0.3, r)
        body.setColorAt(0, c.lighter(200)); body.setColorAt(0.5, c); body.setColorAt(1, c.darker(150))
        p.setBrush(body); p.setPen(QPen(c.darker(200), 1))
        p.drawEllipse(QPointF(cx, cy), r, r)
        # highlight
        p.setBrush(QColor(255, 255, 255, 80)); p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(cx - r * 0.25, cy - r * 0.3), r * 0.35, r * 0.35)
        p.end()

    def sizeHint(self): return QSize(28, 28)


class CircularProgress(QWidget):
    """6. 环形进度条"""
    _display_name = "环形进度条"
    valueChanged = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 0; self._min = 0; self._max = 100
        self._color = QColor("#4A90D9"); self._bg_color = QColor("#e8e8e8")
        self._text_visible = True; self._line_width = 10
        self.setMinimumSize(80, 80)

    def setValue(self, v):
        self._value = max(self._min, min(self._max, int(v)))
        self.valueChanged.emit(self._value); self.update()
    def value(self): return self._value
    def setRange(self, mn, mx): self._min = mn; self._max = mx; self.update()
    def minimum(self): return self._min
    def maximum(self): return self._max

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        side = min(w, h) - self._line_width - 8
        cx, cy = w / 2, h / 2; r = side / 2
        # bg ring
        pen = QPen(self._bg_color, self._line_width); pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen); p.setBrush(Qt.NoBrush)
        p.drawArc(QRectF(cx - r, cy - r, r * 2, r * 2), 90 * 16, -360 * 16)
        # value ring
        ratio = (self._value - self._min) / (self._max - self._min) if self._max > self._min else 0
        pen2 = QPen(self._color, self._line_width); pen2.setCapStyle(Qt.RoundCap)
        p.setPen(pen2)
        p.drawArc(QRectF(cx - r, cy - r, r * 2, r * 2), 90 * 16, -int(360 * ratio * 16))
        # center text
        if self._text_visible:
            p.setPen(self._color)
            p.setFont(QFont("Microsoft YaHei", max(8, int(r / 3)), QFont.Bold))
            txt = f"{int(ratio * 100)}%"
            p.drawText(QRectF(cx - r, cy - r * 0.3, r * 2, r * 0.6), Qt.AlignCenter, txt)
        p.end()

    def sizeHint(self): return QSize(100, 100)


class BatteryIndicator(QWidget):
    """12. 电量指示器 - 电池电量指示器 0~100%"""
    _display_name = "电量指示器"
    valueChanged = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 75; self._min = 0; self._max = 100
        self.setMinimumSize(60, 30)

    def setValue(self, v):
        self._value = max(self._min, min(self._max, int(v)))
        self.valueChanged.emit(self._value); self.update()
    def value(self): return self._value
    def setRange(self, mn, mx): self._min = mn; self._max = mx; self.update()
    def minimum(self): return self._min
    def maximum(self): return self._max

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        body_w = w - 10; body_h = h - 4
        # terminal
        p.setBrush(QColor("#666")); p.setPen(Qt.NoPen)
        p.drawRoundedRect(QRectF(w - 10, h * 0.3, 6, h * 0.4), 2, 2)
        # body
        p.setPen(QPen(QColor("#999"), 2)); p.setBrush(QColor("#f5f5f5"))
        p.drawRoundedRect(QRectF(2, 2, body_w - 4, body_h), 5, 5)
        # fill
        ratio = (self._value - self._min) / (self._max - self._min) if self._max > self._min else 0
        fill_w = (body_w - 10) * ratio
        if ratio > 0.2: color = QColor("#27AE60")
        elif ratio > 0.05: color = QColor("#F39C12")
        else: color = QColor("#E74C3C")
        p.setPen(Qt.NoPen); p.setBrush(color)
        p.drawRoundedRect(QRectF(5, 5, fill_w, body_h - 6), 3, 3)
        # text
        p.setPen(QColor("#333"))
        p.setFont(QFont("Microsoft YaHei", max(7, int(h / 2.5)), QFont.Bold))
        p.drawText(QRectF(2, 0, body_w - 4, h), Qt.AlignCenter, f"{self._value}%")
        p.end()

    def sizeHint(self): return QSize(70, 32)


class DigitalClock(QWidget):
    """10. 数字时钟 - 实时数字时钟"""
    _display_name = "数字时钟"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._format = "HH:mm:ss"
        self._color = QColor("#4A90D9")
        self._bg = QColor("#1e1e1e")
        self.setMinimumSize(160, 60)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.update)
        self._timer.start(1000)

    def setFormat(self, fmt): self._format = fmt; self.update()
    def setValue(self, v): pass  # 兼容

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), self._bg)
        p.setPen(QPen(self._color, 1)); p.setBrush(self._bg.darker(120))
        p.drawRoundedRect(QRectF(self.rect().adjusted(2, 2, -2, -2)), 8, 8)
        p.setPen(self._color)
        p.setFont(QFont("Consolas", max(12, self.height() // 2), QFont.Bold))
        t = QDateTime.currentDateTime().toString(self._format)
        p.drawText(QRectF(0, 0, self.width(), self.height()), Qt.AlignCenter, t)
        p.end()

    def sizeHint(self): return QSize(180, 60)


class SegmentDisplay(QWidget):
    """16. 段码显示器 (7-Segment) - 7段数码管显示器"""
    _display_name = "数码管显示器"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = "8888"
        self._color_on = QColor("#00ff88")
        self._color_off = QColor("#0a2a1a")
        self._digit_count = 4
        self._decimals = 0
        self.setMinimumSize(120, 50)

    def setValue(self, v):
        try:
            val = float(v)
            self._value = f"{val:0{self._digit_count}.{self._decimals}f}"
        except (ValueError, TypeError):
            self._value = str(v)[:self._digit_count]
        self.update()

    def setDigitCount(self, n): self._digit_count = n; self.update()
    def display(self, v): self.setValue(v)
    def value(self):
        try: return float(self._value)
        except: return 0.0

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor("#0a0a0a"))
        p.setPen(QPen(QColor("#333"), 1)); p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(QRectF(self.rect().adjusted(1, 1, -1, -1)), 6, 6)

        w = self.width(); h = self.height()
        dw = w / self._digit_count
        dh = h * 0.8
        ox = (w - dw * self._digit_count) / 2
        oy = (h - dh) / 2

        for i, ch in enumerate(self._value[:self._digit_count]):
            x = ox + i * dw
            self._draw_digit(p, x + 2, oy, dw - 4, dh, ch, self._color_on, self._color_off)
        p.end()

    def _draw_digit(self, p, x, y, w, h, ch, on, off):
        segs = {
            '0': 'abcdef', '1': 'bc', '2': 'abged', '3': 'abgcd',
            '4': 'fgbc', '5': 'afgcd', '6': 'afedcg', '7': 'abc',
            '8': 'abcdefg', '9': 'abfgcd',
            '-': 'g', ' ': '', '.': '', 'A': 'abcefg', 'E': 'afedg',
            'F': 'afeg', 'H': 'fegbc',
        }
        active = set(segs.get(ch.upper(), ''))
        t = max(2, w / 8)  # thickness

        seg_defs = {
            'a': [(t, 0), (w - t, 0), (w - t * 2, t), (t * 2, t)],
            'b': [(w, t), (w, h / 2 - t), (w - t, h / 2), (w - t, t + t)],
            'c': [(w, h / 2 + t), (w, h - t), (w - t, h - t - t), (w - t, h / 2)],
            'd': [(t * 2, h - t), (w - t * 2, h - t), (w - t, h), (t, h)],
            'e': [(0, h / 2 + t), (t, h / 2), (t, h - t - t), (0, h - t)],
            'f': [(0, t), (t, t + t), (t, h / 2), (0, h / 2 - t)],
            'g': [(t, h / 2), (w - t, h / 2), (w - t * 2, h / 2 - t), (t * 2, h / 2 - t)],
        }

        for name, pts in seg_defs.items():
            color = on if name in active else off
            p.setBrush(color); p.setPen(Qt.NoPen)
            path = QPainterPath()
            for j, (px, py) in enumerate(pts):
                pt = QPointF(x + px, y + py)
                if j == 0: path.moveTo(pt)
                else: path.lineTo(pt)
            path.closeSubpath(); p.drawPath(path)

    def sizeHint(self): return QSize(140, 52)


class ValueCard(QWidget):
    """17. 仪表值显示卡 (工业常用) - 数值显示卡片 — 标题+数值+单位+趋势箭头"""
    _display_name = "数值卡片"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._title = "参数"
        self._value = 0.0
        self._unit = ""
        self._decimals = 1
        self._trend = 0  # -1=down, 0=flat, 1=up
        self._color = QColor("#4A90D9")
        self.setMinimumSize(100, 80)

    def setTitle(self, t): self._title = t; self.update()
    def setValue(self, v): self._value = float(v); self.update()
    def setUnit(self, u): self._unit = u; self.update()
    def setDecimals(self, d): self._decimals = int(d); self.update()
    def setTrend(self, t): self._trend = max(-1, min(1, int(t))); self.update()
    def value(self): return self._value

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor("#f8f9fa"))
        p.setPen(QPen(QColor("#dee2e6"), 1)); p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(QRectF(self.rect().adjusted(1, 1, -1, -1)), 8, 8)
        # title
        p.setPen(QColor("#888"))
        p.setFont(QFont("Microsoft YaHei", 10))
        p.drawText(QRectF(6, 4, self.width() - 12, 18), Qt.AlignLeft, self._title)
        # value
        p.setPen(self._color)
        p.setFont(QFont("Microsoft YaHei", max(12, self.height() // 3), QFont.Bold))
        val_text = f"{self._value:.{self._decimals}f}"
        p.drawText(QRectF(6, 22, self.width() - 30, self.height() - 28), Qt.AlignCenter, val_text)
        # unit
        p.setPen(QColor("#666"))
        p.setFont(QFont("Microsoft YaHei", 10))
        p.drawText(QRectF(self.width() - 50, self.height() - 26, 44, 20), Qt.AlignRight, self._unit)
        # trend arrow
        if self._trend != 0:
            tx, ty = self.width() - 20, 8
            p.setPen(Qt.NoPen)
            if self._trend > 0:
                p.setBrush(QColor("#27AE60"))
                p.drawPolygon([QPointF(tx, ty + 14), QPointF(tx + 7, ty), QPointF(tx + 14, ty + 14)])
            else:
                p.setBrush(QColor("#E74C3C"))
                p.drawPolygon([QPointF(tx, ty), QPointF(tx + 7, ty + 14), QPointF(tx + 14, ty)])
        p.end()

    def sizeHint(self): return QSize(120, 90)


# ═══════════════════════════════════════════════════════════════
# 第四部分：辅助与工具控件
# ═══════════════════════════════════════════════════════════════

class ColorPickerButton(QPushButton):
    """7. 颜色选择按钮 - 点击弹出颜色对话框"""
    _display_name = "颜色选择器"
    colorChanged = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._color = QColor("#4A90D9")
        self.setText("选择颜色")
        self.clicked.connect(self._pick)
        self._update_style()

    def color(self): return self._color
    def setColor(self, c):
        self._color = QColor(c) if isinstance(c, str) else c
        self._update_style()
        self.colorChanged.emit(self._color.name())

    def _pick(self):
        c = QColorDialog.getColor(self._color, self, "选择颜色")
        if c.isValid(): self.setColor(c)

    def _update_style(self):
        self.setStyleSheet(
            f"QPushButton{{background:{self._color.name()};color:#fff;border:none;border-radius:4px;"
            f"padding:6px 14px;font-size:12px;font-weight:bold;}}"
            f"QPushButton:hover{{background:{self._color.darker(110).name()};}}"
        )


class FilePicker(QWidget):
    """8. 文件路径选择器 - 输入框+浏览按钮"""
    _display_name = "文件选择器"
    pathChanged = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self); layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(4)
        self.edit = QLineEdit()
        self.edit.setPlaceholderText("选择文件路径...")
        self.edit.setMinimumHeight(28)
        self.edit.setStyleSheet("QLineEdit{padding:3px 6px;font-size:12px;}")
        self.edit.textChanged.connect(self.pathChanged.emit)
        layout.addWidget(self.edit)
        self.btn = QPushButton("📂")
        self.btn.setFixedWidth(32); self.btn.setMinimumHeight(28)
        self.btn.setStyleSheet("QPushButton{background:#f0f0f0;border:1px solid #ccc;border-radius:4px;font-size:14px;}")
        self.btn.clicked.connect(self._browse)
        layout.addWidget(self.btn)
        self._mode = "file"  # file | dir | save

    def setMode(self, m): self._mode = m
    def path(self): return self.edit.text()
    def setPath(self, p): self.edit.setText(p)
    def setPlaceholderText(self, t): self.edit.setPlaceholderText(t)

    def _browse(self):
        if self._mode == "dir":
            path = QFileDialog.getExistingDirectory(self, "选择目录", self.edit.text())
        elif self._mode == "save":
            path, _ = QFileDialog.getSaveFileName(self, "保存文件", self.edit.text())
        else:
            path, _ = QFileDialog.getOpenFileName(self, "选择文件", self.edit.text())
        if path: self.edit.setText(path)


class StarRating(QWidget):
    """9. 星级评分 - 1~5星评分控件"""
    _display_name = "星级评分"
    ratingChanged = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rating = 3; self._max = 5
        self._star_color = QColor("#F39C12")
        self._empty_color = QColor("#ddd")
        self.setFixedSize(160, 32)
        self.setCursor(Qt.PointingHandCursor)

    def setValue(self, v): self._rating = max(0, min(self._max, int(v))); self.update()
    def value(self): return self._rating
    def setRating(self, r): self.setValue(r)

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        p.setFont(QFont("Segoe UI", 20))
        for i in range(self._max):
            color = self._star_color if i < self._rating else self._empty_color
            p.setPen(QPen(color, 1)); p.setBrush(color)
            x = i * 32
            self._draw_star(p, x + 16, 16, 14)
        p.end()

    def _draw_star(self, p, cx, cy, r):
        path = QPainterPath()
        for i in range(10):
            ang = math.pi / 2 + i * math.pi / 5
            rr = r if i % 2 == 0 else r * 0.4
            x = cx + rr * math.cos(ang); y = cy - rr * math.sin(ang)
            if i == 0: path.moveTo(x, y)
            else: path.lineTo(x, y)
        path.closeSubpath(); p.drawPath(path)

    def mousePressEvent(self, e):
        idx = int(e.position().x() / 32)
        self.setValue(idx + 1)
        self.ratingChanged.emit(self._rating)

    def sizeHint(self): return QSize(160, 32)


class TagChip(QWidget):
    """13. 标签徽章 - 标签/徽章控件"""
    _display_name = "标签徽章"
    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._text = "标签"
        self._color = QColor("#4A90D9")
        self._removable = False
        self.setMinimumSize(40, 24)
        self.setCursor(Qt.PointingHandCursor)

    def setText(self, t): self._text = t; self.update()
    def text(self): return self._text
    def setColor(self, c): self._color = QColor(c); self.update()
    def setRemovable(self, v): self._removable = v; self.update()

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        r = self.rect().adjusted(2, 2, -2, -2)
        p.setPen(Qt.NoPen); p.setBrush(self._color.lighter(130))
        p.drawRoundedRect(QRectF(r), self.height() / 2, self.height() / 2)
        p.setPen(self._color.darker(120))
        p.setFont(QFont("Microsoft YaHei", 10))
        p.drawText(r, Qt.AlignCenter, f"  {self._text}  ")
        if self._removable:
            p.setPen(QPen(self._color.darker(150), 2))
            cx = r.right() - 10; cy = r.center().y()
            p.drawLine(QPointF(cx - 4, cy - 4), QPointF(cx + 4, cy + 4))
            p.drawLine(QPointF(cx + 4, cy - 4), QPointF(cx - 4, cy + 4))
        p.end()

    def mousePressEvent(self, e): self.clicked.emit()

    def sizeHint(self):
        fm = QFontMetrics(QFont("Microsoft YaHei", 10))
        return QSize(fm.horizontalAdvance(f"  {self._text}  ") + 20, 26)


class Knob(QWidget):
    """14. 旋钮控件 (Knob) - 旋转旋钮"""
    _display_name = "旋转旋钮"
    valueChanged = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 50.0; self._min = 0.0; self._max = 100.0
        self._start_angle = 225; self._span_angle = 270
        self._color = QColor("#4A90D9")
        self._dragging = False
        self.setMinimumSize(60, 60)
        self.setCursor(Qt.OpenHandCursor)

    def setValue(self, v):
        self._value = max(self._min, min(self._max, float(v)))
        self.valueChanged.emit(self._value); self.update()
    def value(self): return self._value
    def setRange(self, mn, mx): self._min = float(mn); self._max = float(mx); self.update()
    def minimum(self): return self._min
    def maximum(self): return self._max

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        side = min(w, h) - 12; cx, cy = w / 2, h / 2; r = side / 2
        # bg arc
        pen = QPen(QColor("#e0e0e0"), 8); pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen); p.setBrush(Qt.NoBrush)
        p.drawArc(QRectF(cx - r, cy - r, r * 2, r * 2), int(self._start_angle * 16), int(self._span_angle * 16))
        # value arc
        ratio = (self._value - self._min) / (self._max - self._min) if self._max > self._min else 0
        pen2 = QPen(self._color, 8); pen2.setCapStyle(Qt.RoundCap)
        p.setPen(pen2)
        p.drawArc(QRectF(cx - r, cy - r, r * 2, r * 2), int(self._start_angle * 16),
                  int(self._span_angle * ratio * 16))
        # indicator dot
        ang = (self._start_angle + self._span_angle * ratio) * math.pi / 180
        dot_r = r - 8
        dx = cx + dot_r * math.cos(ang); dy = cy - dot_r * math.sin(ang)
        p.setBrush(self._color); p.setPen(QPen(self._color.darker(150), 2))
        p.drawEllipse(QPointF(dx, dy), 6, 6)
        # center value
        p.setPen(QColor("#333"))
        p.setFont(QFont("Microsoft YaHei", max(7, int(r / 4)), QFont.Bold))
        p.drawText(QRectF(cx - r, cy - r * 0.2, r * 2, r * 0.4), Qt.AlignCenter,
                   f"{self._value:.0f}")
        p.end()

    def mousePressEvent(self, e):
        self._dragging = True
        self.setCursor(Qt.ClosedHandCursor)
        self._update_from_mouse(e.position())

    def mouseMoveEvent(self, e):
        if self._dragging: self._update_from_mouse(e.position())

    def mouseReleaseEvent(self, e):
        self._dragging = False
        self.setCursor(Qt.OpenHandCursor)

    def _update_from_mouse(self, pos):
        cx, cy = self.width() / 2, self.height() / 2
        ang = math.atan2(cy - pos.y(), pos.x() - cx) * 180 / math.pi
        # Map angle to value range
        a = (ang + 360) % 360
        start = self._start_angle
        span = self._span_angle
        ratio = ((a - start + 360) % 360) / span
        self.setValue(self._min + ratio * (self._max - self._min))

    def sizeHint(self): return QSize(80, 80)


class TimerDisplay(QWidget):
    """15. 倒计时/计时器 - 倒计时/正计时器"""
    _display_name = "计时器"
    timeout = Signal()
    valueChanged = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._total_seconds = 60
        self._remaining = 60
        self._running = False
        self._mode = "countdown"  # countdown | stopwatch
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self.setMinimumSize(120, 50)

    def setValue(self, v):
        self._total_seconds = int(v); self._remaining = int(v); self.update()
    def value(self): return self._remaining
    def setRange(self, mn, mx): self._total_seconds = mx; self._remaining = mx; self.update()

    def start(self):
        self._running = True
        self._timer.start(1000)

    def stop(self):
        self._running = False
        self._timer.stop()

    def reset(self):
        self.stop()
        self._remaining = self._total_seconds
        self.update()

    def _tick(self):
        if self._mode == "countdown":
            self._remaining -= 1
            if self._remaining <= 0:
                self._remaining = 0; self.stop(); self.timeout.emit()
        else:
            self._remaining += 1
        self.valueChanged.emit(self._remaining)
        self.update()

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor("#1e1e1e"))
        p.setBrush(QColor("#2a2a2a")); p.setPen(Qt.NoPen)
        p.drawRoundedRect(QRectF(self.rect().adjusted(2, 2, -2, -2)), 8, 8)
        mins = abs(self._remaining) // 60
        secs = abs(self._remaining) % 60
        txt = f"{mins:02d}:{secs:02d}"
        color = QColor("#E74C3C") if (self._mode == "countdown" and self._remaining < 10) else QColor("#00ff88")
        if self._remaining < 0: txt = "-" + txt
        p.setPen(color)
        p.setFont(QFont("Consolas", max(14, self.height() // 2), QFont.Bold))
        p.drawText(self.rect(), Qt.AlignCenter, txt)
        p.end()

    def sizeHint(self): return QSize(140, 50)