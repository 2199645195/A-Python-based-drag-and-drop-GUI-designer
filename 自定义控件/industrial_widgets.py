#!/usr/bin/env python3
"""
Mini Designer v19 - 工业控件库合集
包含: 仪表盘、实时曲线、相机、塔灯、液位罐、LED灯、环形进度、拨码开关、
      状态按钮、柱状图、滑动开关、温度计、计时器、坐标指示器、电池、旋钮、数码管、管道流向
"""
import math, time
from PySide6.QtCore import Qt, Signal, QRectF, QPointF, QTimer, QSize
from PySide6.QtGui import (
    QPainter, QPen, QColor, QFont, QFontMetrics, QImage, QPixmap,
    QBrush, QLinearGradient, QRadialGradient, QConicalGradient, QPainterPath,
)
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QSizePolicy


# ═══════════════════════════════════════════════════════════════
# 1. 仪表盘控件
# ═══════════════════════════════════════════════════════════════
class GaugeWidget(QWidget):
    """工业圆形仪表 — 多阈值颜色、刻度、指针、数据绑定"""
    _display_name = "仪表盘"
    valueChanged = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._min_val = 0; self._max_val = 100; self._value = 50
        self._unit = ""; self._title = "仪表"
        self._gauge_color = QColor("#4A90D9")
        self._warning_color = QColor("#F39C12")
        self._danger_color = QColor("#E74C3C")
        self._warning_threshold = 70; self._danger_threshold = 90
        self._start_angle = 225; self._span_angle = 270
        self._tick_count = 10; self._decimals = 1
        self.setMinimumSize(120, 120)

    def setValue(self, v):
        self._value = max(self._min_val, min(self._max_val, float(v)))
        self.valueChanged.emit(self._value); self.update()
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
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        margin = 20; side = min(w, h) - margin * 2
        if side < 40: return
        cx, cy = w / 2.0, h / 2.0; radius = side / 2.0
        pen_w = max(6, int(radius / 10))
        bg_pen = QPen(QColor("#e8e8e8"), pen_w); bg_pen.setCapStyle(Qt.RoundCap)
        p.setPen(bg_pen); p.setBrush(Qt.NoBrush)
        p.drawArc(QRectF(cx - radius, cy - radius, radius * 2, radius * 2),
                  int(self._start_angle * 16), int(self._span_angle * 16))
        ratio = ((self._value - self._min_val) / (self._max_val - self._min_val)) if self._max_val > self._min_val else 0
        ratio = max(0.0, min(1.0, ratio))
        if self._value >= self._danger_threshold: arc_color = self._danger_color
        elif self._value >= self._warning_threshold: arc_color = self._warning_color
        else: arc_color = self._gauge_color
        val_pen = QPen(arc_color, pen_w); val_pen.setCapStyle(Qt.RoundCap)
        p.setPen(val_pen)
        p.drawArc(QRectF(cx - radius, cy - radius, radius * 2, radius * 2),
                  int(self._start_angle * 16), int(self._span_angle * ratio * 16))
        tick_pen = QPen(QColor("#999"), max(1, int(radius / 60)))
        p.setPen(tick_pen)
        for i in range(self._tick_count + 1):
            ang = (self._start_angle + self._span_angle * i / self._tick_count) * math.pi / 180.0
            inner_r = radius - pen_w - 4; outer_r = radius - 2
            x1 = cx + inner_r * math.cos(ang); y1 = cy - inner_r * math.sin(ang)
            x2 = cx + outer_r * math.cos(ang); y2 = cy - outer_r * math.sin(ang)
            p.drawLine(QPointF(x1, y1), QPointF(x2, y2))
        for i in range(0, self._tick_count + 1, max(1, self._tick_count // 5)):
            ang = (self._start_angle + self._span_angle * i / self._tick_count) * math.pi / 180.0
            val = self._min_val + (self._max_val - self._min_val) * i / self._tick_count
            label_r = radius - 14
            lx = cx + label_r * math.cos(ang); ly = cy - label_r * math.sin(ang)
            p.setFont(QFont("Microsoft YaHei", max(7, int(radius / 14))))
            p.setPen(QColor("#666"))
            p.drawText(int(lx - 14), int(ly - 8), 28, 16, int(Qt.AlignCenter), f"{val:.{self._decimals}f}")
            p.setPen(tick_pen)
        needle_angle = (self._start_angle + self._span_angle * ratio) * math.pi / 180.0
        needle_len = radius - max(8, int(radius / 8))
        nx = cx + needle_len * 0.8 * math.cos(needle_angle)
        ny = cy - needle_len * 0.8 * math.sin(needle_angle)
        needle_pen = QPen(QColor("#333"), max(2, int(radius / 40)))
        p.setPen(needle_pen); p.drawLine(QPointF(cx, cy), QPointF(nx, ny))
        hub_r = max(6, int(radius / 12))
        p.setBrush(QColor("#333")); p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(cx, cy), hub_r, hub_r)
        p.setBrush(QColor("#fff")); p.drawEllipse(QPointF(cx, cy), hub_r * 0.5, hub_r * 0.5)
        p.setPen(QColor("#333"))
        p.setFont(QFont("Microsoft YaHei", max(9, int(radius / 8)), QFont.Bold))
        val_text = f"{self._value:.{self._decimals}f}{self._unit}"
        fm = QFontMetrics(p.font()); val_y = cy + radius * 0.15
        tw = fm.horizontalAdvance(val_text)
        p.drawText(QRectF(cx - tw / 2.0, val_y - fm.height() / 2.0, tw * 1.0, fm.height() * 1.0),
                   Qt.AlignCenter, val_text)
        if self._title:
            p.setFont(QFont("Microsoft YaHei", max(7, int(radius / 16))))
            p.setPen(QColor("#888"))
            p.drawText(QRectF(cx - 50, val_y + max(14, int(radius / 12)), 100, 18), Qt.AlignCenter, self._title)
        p.end()

    def sizeHint(self): return QSize(160, 160)
    def minimumSizeHint(self): return QSize(100, 100)


# ═══════════════════════════════════════════════════════════════
# 2. 实时曲线控件
# ═══════════════════════════════════════════════════════════════
class CurveWidget(QWidget):
    """多通道实时滚动曲线"""
    _display_name = "实时曲线"
    MAX_POINTS = 300

    def __init__(self, parent=None):
        super().__init__(parent)
        self._channels = [[], []]
        self._colors = [QColor("#4A90D9"), QColor("#27AE60"), QColor("#F39C12"),
                        QColor("#E74C3C"), QColor("#9B59B6"), QColor("#1ABC9C")]
        self._names = ["CH1", "CH2"]
        self._timer = QTimer(self); self._timer.timeout.connect(self._auto_scroll)
        self.setMinimumSize(200, 120)

    def addValue(self, channel, value):
        if 0 <= channel < len(self._channels):
            self._channels[channel].append(float(value))
            if len(self._channels[channel]) > self.MAX_POINTS:
                self._channels[channel].pop(0)
            self.update()

    def setValue(self, v):
        """兼容 DataBinder: 传入数值更新通道0"""
        try: self.addValue(0, float(v))
        except: pass

    def start(self): self._timer.start(100)
    def stop(self): self._timer.stop()

    def _auto_scroll(self):
        """预览模式自动滚动（实际运行时由外部推送）"""
        pass

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        margin_l, margin_r, margin_t, margin_b = 40, 10, 10, 20
        cw, ch = w - margin_l - margin_r, h - margin_t - margin_b
        # 背景
        p.fillRect(0, 0, w, h, QColor("#fafafa"))
        p.setPen(QPen(QColor("#e0e0e0"), 1))
        for i in range(5):
            y = margin_t + ch * i / 4
            p.drawLine(margin_l, y, margin_l + cw, y)
        # 计算Y轴范围
        all_vals = [v for ch in self._channels for v in ch]
        if all_vals:
            y_min, y_max = min(all_vals), max(all_vals)
            pad = (y_max - y_min) * 0.1 or 1
            y_min -= pad; y_max += pad
        else:
            y_min, y_max = 0, 100
        # Y轴标签
        p.setPen(QColor("#999")); p.setFont(QFont("Arial", 8))
        for i in range(5):
            val = y_max - (y_max - y_min) * i / 4
            y = margin_t + ch * i / 4
            p.drawText(0, y - 8, margin_l - 4, 16, Qt.AlignRight | Qt.AlignVCenter, f"{val:.1f}")
        # 绘制曲线
        for ci, data in enumerate(self._channels):
            if len(data) < 2: continue
            color = self._colors[ci % len(self._colors)]
            pen = QPen(color, 2); p.setPen(pen)
            path = QPainterPath()
            for di, val in enumerate(data):
                x = margin_l + cw * di / max(1, len(data) - 1)
                y = margin_t + ch * (1 - (val - y_min) / max(0.001, y_max - y_min))
                if di == 0: path.moveTo(x, y)
                else: path.lineTo(x, y)
            p.drawPath(path)
        # 图例
        lx = margin_l + 4
        for ci, name in enumerate(self._names[:len(self._channels)]):
            color = self._colors[ci % len(self._colors)]
            p.setPen(color); p.setFont(QFont("Arial", 9))
            p.drawLine(lx, h - 8, lx + 16, h - 8)
            p.drawText(lx + 20, h - 14, 60, 14, Qt.AlignLeft | Qt.AlignVCenter, name)
            lx += 80
        p.end()

    def sizeHint(self): return QSize(320, 180)


# ═══════════════════════════════════════════════════════════════
# 3. 工业相机控件 (纯PySide6版)
# ═══════════════════════════════════════════════════════════════
class CameraWidget(QWidget):
    """工业相机实时画面控件 — 支持外部推帧/SDK回调/设计时占位预览"""
    _display_name = "📷 工业相机"
    frame_updated = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap = None
        self._status_text = "📷 相机未连接"
        self._fps_counter = 0; self._last_fps_time = time.time(); self._current_fps = 0.0
        self._source_label = ""
        self._demo_timer = QTimer(self); self._demo_timer.setInterval(33)
        self._demo_timer.timeout.connect(self._demo_tick)
        self._demo_phase = 0.0
        self.setMinimumSize(160, 120)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def setValue(self, v):
        if isinstance(v, str): self.load_image(v)
        elif hasattr(v, 'shape'): self.updateFrame(v)

    def updateFrame(self, frame):
        try:
            if hasattr(frame, 'shape'):
                h, w = frame.shape[:2]
                ch = frame.shape[2] if len(frame.shape) == 3 else 1
                if ch == 3:
                    rgb = frame[:, :, ::-1].copy()
                    qimg = QImage(rgb.data, w, h, w * 3, QImage.Format_RGB888).copy()
                else:
                    qimg = QImage(frame.data, w, h, w, QImage.Format_Grayscale8).copy()
                self._pixmap = QPixmap.fromImage(qimg)
            elif isinstance(frame, QImage): self._pixmap = QPixmap.fromImage(frame)
            elif isinstance(frame, QPixmap): self._pixmap = frame
            else: return
            self._status_text = ""; self._calc_fps()
            self.frame_updated.emit(frame); self.update()
        except Exception as ex:
            self._status_text = f"❌ 帧解析失败: {ex}"; self.update()

    def load_image(self, path):
        pm = QPixmap(path)
        if pm.isNull():
            self._status_text = f"❌ 无法加载: {path}"; self._pixmap = None
        else:
            self._pixmap = pm; self._status_text = ""
            self._source_label = path.split("/")[-1].split("\\")[-1]
        self.update()

    def start(self, source="", fps=30):
        self._source_label = str(source) if source else "Demo"
        self._demo_timer.start(int(1000 / max(1, fps)))
        self._status_text = ""; self.update()

    def stop(self):
        self._demo_timer.stop(); self._status_text = "⏹ 已停止"; self.update()

    def _calc_fps(self):
        self._fps_counter += 1; now = time.time()
        elapsed = now - self._last_fps_time
        if elapsed >= 1.0:
            self._current_fps = self._fps_counter / elapsed
            self._fps_counter = 0; self._last_fps_time = now

    def _demo_tick(self):
        self._demo_phase += 0.05
        w, h = max(self.width(), 160), max(self.height(), 120)
        img = QImage(w, h, QImage.Format_RGB888)
        r = int(127 + 127 * math.sin(self._demo_phase))
        g = int(127 + 127 * math.sin(self._demo_phase + 2.094))
        b = int(127 + 127 * math.sin(self._demo_phase + 4.189))
        img.fill(QColor(r, g, b))
        p = QPainter(img)
        p.setPen(QColor(255, 255, 255, 200))
        p.setFont(QFont("Consolas", 14, QFont.Bold))
        ts = time.strftime("%H:%M:%S")
        p.drawText(10, 24, f"CAM-01 | {ts} | {self._current_fps:.1f} FPS")
        p.end()
        self._pixmap = QPixmap.fromImage(img); self._calc_fps(); self.update()

    def paintEvent(self, event):
        p = QPainter(self); p.setRenderHint(QPainter.SmoothPixmapTransform)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, QColor("#1e1e1e"))
        if self._pixmap and not self._pixmap.isNull():
            scaled = self._pixmap.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            x = (w - scaled.width()) // 2; y = (h - scaled.height()) // 2
            p.drawPixmap(x, y, scaled)
            p.setPen(QColor(0, 255, 0, 180)); p.setFont(QFont("Consolas", 9))
            osd = f"{self._current_fps:.1f} FPS"
            if self._source_label: osd += f" | {self._source_label}"
            p.drawText(6, h - 6, osd)
        else:
            p.setPen(QColor("#888")); p.setFont(QFont("Microsoft YaHei", 12))
            p.drawText(QRectF(0, 0, w, h), Qt.AlignCenter, self._status_text)
            pen = QPen(QColor("#333"), 1, Qt.DashLine); p.setPen(pen)
            p.drawRect(0, 0, w - 1, h - 1)
        p.end()

    def resizeEvent(self, event): super().resizeEvent(event); self.update()
    def sizeHint(self): return QSize(320, 240)
    def minimumSizeHint(self): return QSize(160, 120)


# ═══════════════════════════════════════════════════════════════
# 4. 三色报警塔灯
# ═══════════════════════════════════════════════════════════════
class TowerLightWidget(QWidget):
    """设备运行状态指示（红/黄/绿 + 蜂鸣器图标）"""
    _display_name = "🚦 塔灯"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._states = {"green": False, "yellow": False, "red": False, "buzzer": False}
        self.setMinimumSize(60, 180)

    def setValue(self, v):
        if isinstance(v, str):
            for k in self._states: self._states[k] = k in v.lower()
        elif isinstance(v, dict): self._states.update(v)
        self.update()

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        colors = [("green", "#27AE60", "#1e8449"), ("yellow", "#F39C12", "#d68910"), ("red", "#E74C3C", "#c0392b")]
        light_h = min(w, (h - 40) // 3)
        for i, (name, on_c, off_c) in enumerate(colors):
            y = 10 + i * (light_h + 4)
            color = QColor(on_c) if self._states.get(name) else QColor(off_c).darker(300)
            p.setBrush(color); p.setPen(Qt.NoPen)
            p.drawRoundedRect(QRectF((w - light_h) / 2, y, light_h, light_h), light_h // 4, light_h // 4)
            if self._states.get(name):
                p.setBrush(QColor(on_c).lighter(150))
                p.drawEllipse(QRectF((w - light_h * 0.4) / 2, y + light_h * 0.3, light_h * 0.4, light_h * 0.4))
        p.end()


# ═══════════════════════════════════════════════════════════════
# 5. 垂直液位罐
# ═══════════════════════════════════════════════════════════════
class TankLevelWidget(QWidget):
    """储罐液位/料位可视化显示"""
    _display_name = "🌡️ 液位罐"
    valueChanged = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._level = 50; self._max = 100; self._unit = "%"; self._title = "储罐"
        self.setMinimumSize(80, 200)

    def setValue(self, v):
        self._level = max(0, min(self._max, float(v)))
        self.valueChanged.emit(self._level); self.update()

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        margin = 20; tank_w = w - margin * 2; tank_h = h - margin * 2 - 30
        p.setPen(QPen(QColor("#666"), 2)); p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(QRectF(margin, margin + 20, tank_w, tank_h), 8, 8)
        ratio = self._level / max(1, self._max)
        liquid_h = tank_h * ratio
        grad = QLinearGradient(0, margin + 20 + tank_h - liquid_h, 0, margin + 20 + tank_h)
        grad.setColorAt(0, QColor("#4A90D9")); grad.setColorAt(1, QColor("#2E6DA4"))
        p.setBrush(grad); p.setPen(Qt.NoPen)
        p.drawRoundedRect(QRectF(margin + 2, margin + 20 + tank_h - liquid_h, tank_w - 4, liquid_h - 2), 6, 6)
        p.setPen(QPen(QColor("#999"), 1))
        for i in range(11):
            y = margin + 20 + tank_h * (1 - i / 10)
            p.drawLine(margin + tank_w, y, margin + tank_w + 6, y)
            if i % 5 == 0:
                p.setFont(QFont("Arial", 8))
                p.drawText(margin + tank_w + 8, y + 4, f"{i * 10}%")
        p.setPen(QColor("#333")); p.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        p.drawText(QRectF(0, 4, w, 18), Qt.AlignCenter, self._title)
        p.drawText(QRectF(0, h - 18, w, 18), Qt.AlignCenter, f"{self._level:.1f}{self._unit}")
        p.end()


# ═══════════════════════════════════════════════════════════════
# 6. LED指示灯
# ═══════════════════════════════════════════════════════════════
class LedIndicatorWidget(QWidget):
    """数字量IO状态、通信连接指示"""
    _display_name = "💡 LED指示灯"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._on = False; self._color_on = "#00ff00"; self._label = ""
        self.setMinimumSize(40, 40)

    def setValue(self, v): self._on = bool(v); self.update()
    def setChecked(self, v): self.setValue(v)

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        s = min(self.width(), self.height()) - 8
        color = QColor(self._color_on) if self._on else QColor("#333")
        p.setBrush(color); p.setPen(QPen(QColor("#555"), 1))
        p.drawEllipse(QRectF(4, 4, s, s))
        if self._on:
            p.setBrush(QColor(255, 255, 255, 100))
            p.drawEllipse(QRectF(s * 0.25 + 4, s * 0.2 + 4, s * 0.3, s * 0.25))
        if self._label:
            p.setPen(QColor("#ccc")); p.setFont(QFont("Arial", 8))
            p.drawText(QRectF(0, s + 4, self.width(), 14), Qt.AlignCenter, self._label)
        p.end()


# ═══════════════════════════════════════════════════════════════
# 7. 环形进度条
# ═══════════════════════════════════════════════════════════════
class RingProgressWidget(QWidget):
    """OEE、完成率、电池电量等百分比展示"""
    _display_name = "⭕ 环形进度"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 0; self._max = 100; self._title = ""; self._color = "#4A90D9"
        self.setMinimumSize(100, 100)

    def setValue(self, v): self._value = max(0, min(self._max, float(v))); self.update()

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        s = min(self.width(), self.height()) - 10
        cx, cy = self.width() / 2, self.height() / 2
        pen_w = max(6, s // 10)
        p.setPen(QPen(QColor("#e0e0e0"), pen_w)); p.setBrush(Qt.NoBrush)
        p.drawArc(QRectF(cx - s / 2, cy - s / 2, s, s), 0, 360 * 16)
        ratio = self._value / max(1, self._max)
        p.setPen(QPen(QColor(self._color), pen_w, Qt.SolidLine))
        p.drawArc(QRectF(cx - s / 2, cy - s / 2, s, s), 90 * 16, int(-360 * 16 * ratio))
        p.setPen(QColor("#333")); p.setFont(QFont("Arial", max(12, s // 5), QFont.Bold))
        p.drawText(QRectF(0, cy - s // 6, self.width(), s // 3), Qt.AlignCenter, f"{ratio * 100:.0f}%")
        if self._title:
            p.setFont(QFont("Microsoft YaHei", max(8, s // 12)))
            p.setPen(QColor("#888"))
            p.drawText(QRectF(0, cy + s // 5, self.width(), s // 6), Qt.AlignCenter, self._title)
        p.end()


# ═══════════════════════════════════════════════════════════════
# 8. 工业拨码开关
# ═══════════════════════════════════════════════════════════════
class DipSwitchWidget(QWidget):
    """参数配置、地址设定、模式选择"""
    _display_name = "🔲 拨码开关"
    valueChanged = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._bits = 8; self._value = 0
        self.setMinimumSize(200, 60)

    def setValue(self, v):
        self._value = int(v) & ((1 << self._bits) - 1)
        self.valueChanged.emit(self._value); self.update()
    def value(self): return self._value

    def mousePressEvent(self, e):
        sw = self.width() / self._bits
        idx = int(e.position().x() / sw)
        if 0 <= idx < self._bits:
            self._value ^= (1 << idx)
            self.valueChanged.emit(self._value); self.update()

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        sw = self.width() / self._bits; sh = self.height() - 20
        for i in range(self._bits):
            x = i * sw + 2; on = bool(self._value & (1 << i))
            p.setBrush(QColor("#333")); p.setPen(Qt.NoPen)
            p.drawRoundedRect(QRectF(x, 10, sw - 4, sh), 3, 3)
            knob_y = 12 if on else 10 + sh - 14
            p.setBrush(QColor("#E74C3C") if on else QColor("#888"))
            p.drawRoundedRect(QRectF(x + 2, knob_y, sw - 8, 12), 2, 2)
            p.setPen(QColor("#999")); p.setFont(QFont("Arial", 7))
            p.drawText(QRectF(x, self.height() - 14, sw, 14), Qt.AlignCenter, str(i))
        p.end()


# ═══════════════════════════════════════════════════════════════
# 9. 带状态反馈的工业按钮
# ═══════════════════════════════════════════════════════════════
class StateButtonWidget(QPushButton):
    """运行/停止/故障/离线 四态按钮"""
    _display_name = "🔘 状态按钮"
    stateChanged = Signal(str)
    STATES = {
        "idle": ("#95a5a6", "⏸ 待机", False),
        "running": ("#27ae60", "▶ 运行中", True),
        "warning": ("#f39c12", "⚠ 警告", True),
        "error": ("#e74c3c", "✕ 故障", True),
        "offline": ("#7f8c8d", "☁ 离线", False),
    }

    def __init__(self, parent=None):
        super().__init__("⏸ 待机", parent)
        self._state = "idle"
        self.setMinimumSize(120, 40)
        self.setCursor(Qt.PointingHandCursor)
        self.clicked.connect(lambda: self.setValue("running" if self._state == "idle" else "idle"))
        self.setValue("idle")

    def setValue(self, state):
        state = str(state).lower().strip()
        if state not in self.STATES: return
        self._state = state
        color, text, active = self.STATES[state]
        self.setText(text)
        self.setStyleSheet(f"""
            QPushButton {{ background:{color}; color:#fff; border:none; border-radius:6px;
                          font-size:13px; font-weight:bold; padding:8px 16px; }}
            QPushButton:hover {{ filter:brightness(1.1); }}
            QPushButton:pressed {{ filter:brightness(0.9); }}
        """)
        self.setEnabled(active)
        self.stateChanged.emit(state)

    def value(self): return self._state


# ═══════════════════════════════════════════════════════════════
# 10. 多通道柱状图
# ═══════════════════════════════════════════════════════════════
class BarChartWidget(QWidget):
    """多通道当前值对比"""
    _display_name = "📊 柱状图"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data = {"CH1": 65, "CH2": 42, "CH3": 88, "CH4": 30}
        self._colors = ["#4A90D9", "#27AE60", "#F39C12", "#E74C3C", "#9B59B6", "#1ABC9C"]
        self._max_val = 100
        self.setMinimumSize(200, 150)

    def setValue(self, v):
        if isinstance(v, dict): self._data = v
        elif isinstance(v, (int, float)):
            keys = list(self._data.keys())
            if keys: self._data[keys[0]] = float(v)
        self.update()

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        margin_l, margin_b, margin_t = 40, 30, 10
        chart_w, chart_h = w - margin_l - 10, h - margin_b - margin_t
        p.setPen(QColor("#999")); p.setFont(QFont("Arial", 8))
        for i in range(5):
            y = margin_t + chart_h * (1 - i / 4)
            p.drawLine(margin_l - 4, y, margin_l, y)
            p.drawText(0, y - 8, margin_l - 6, 16, Qt.AlignRight | Qt.AlignVCenter, f"{self._max_val * i // 4}")
        p.drawLine(margin_l, margin_t, margin_l, margin_t + chart_h)
        p.drawLine(margin_l, margin_t + chart_h, margin_l + chart_w, margin_t + chart_h)
        n = len(self._data)
        if n == 0: return
        bar_w = min(40, chart_w // n - 8)
        gap = (chart_w - bar_w * n) / (n + 1)
        for i, (label, val) in enumerate(self._data.items()):
            x = margin_l + gap + i * (bar_w + gap)
            ratio = max(0, min(1, float(val) / self._max_val))
            bar_h = chart_h * ratio
            color = QColor(self._colors[i % len(self._colors)])
            p.setBrush(color); p.setPen(Qt.NoPen)
            p.drawRoundedRect(QRectF(x, margin_t + chart_h - bar_h, bar_w, bar_h), 3, 3)
            p.setPen(color.darker(120)); p.setFont(QFont("Arial", 9, QFont.Bold))
            p.drawText(QRectF(x, margin_t + chart_h - bar_h - 18, bar_w, 16), Qt.AlignCenter, f"{val:.0f}")
            p.setPen(QColor("#666")); p.setFont(QFont("Microsoft YaHei", 8))
            p.drawText(QRectF(x, margin_t + chart_h + 4, bar_w, 20), Qt.AlignCenter, label)
        p.end()


# ═══════════════════════════════════════════════════════════════
# 11. 滑动开关
# ═══════════════════════════════════════════════════════════════
class ToggleSwitchWidget(QWidget):
    """iOS风格滑动开关，支持动画"""
    _display_name = "🎚️ 滑动开关"
    toggled = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._on = False; self._anim_pos = 0.0
        self._timer = QTimer(self); self._timer.timeout.connect(self._animate)
        self.setMinimumSize(60, 30); self.setMaximumHeight(36)
        self.setCursor(Qt.PointingHandCursor)

    def setValue(self, v): self.setChecked(bool(v))
    def setChecked(self, checked):
        if self._on == checked: return
        self._on = checked; self._timer.start(16); self.toggled.emit(self._on)
    def isChecked(self): return self._on
    def value(self): return self._on

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton: self.setChecked(not self._on)

    def _animate(self):
        target = 1.0 if self._on else 0.0
        diff = target - self._anim_pos
        if abs(diff) < 0.05: self._anim_pos = target; self._timer.stop()
        else: self._anim_pos += diff * 0.25
        self.update()

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height(); r = h / 2
        bg_color = QColor("#27ae60") if self._anim_pos > 0.5 else QColor("#ccc")
        p.setBrush(bg_color); p.setPen(Qt.NoPen)
        p.drawRoundedRect(QRectF(0, 0, w, h), r, r)
        knob_x = r + self._anim_pos * (w - 2 * r)
        p.setBrush(Qt.white)
        p.drawEllipse(QRectF(knob_x - r * 0.8, h * 0.1, r * 1.6, h * 0.8))
        p.end()


# ═══════════════════════════════════════════════════════════════
# 12. 温度计控件
# ═══════════════════════════════════════════════════════════════
class ThermometerWidget(QWidget):
    """温度显示，带水银柱效果和阈值变色"""
    _display_name = "🌡️ 温度计"
    valueChanged = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 25; self._min = -10; self._max = 50
        self._unit = "°C"; self._title = "温度"
        self.setMinimumSize(50, 200)

    def setValue(self, v):
        self._value = max(self._min, min(self._max, float(v)))
        self.valueChanged.emit(self._value); self.update()
    def setRange(self, mn, mx): self._min = float(mn); self._max = float(mx); self.update()
    def setUnit(self, u): self._unit = str(u); self.update()

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        tube_w = min(20, w // 3); cx = w // 2
        bulb_r = tube_w; tube_top = 20; tube_bot = h - bulb_r - 10
        ratio = (self._value - self._min) / max(1, self._max - self._min)
        if ratio > 0.8: color = QColor("#e74c3c")
        elif ratio > 0.5: color = QColor("#f39c12")
        else: color = QColor("#4A90D9")
        p.setPen(QPen(QColor("#bbb"), 2)); p.setBrush(QColor("#f8f8f8"))
        p.drawRoundedRect(QRectF(cx - tube_w // 2, tube_top, tube_w, tube_bot - tube_top), tube_w // 2, tube_w // 2)
        p.drawEllipse(QPointF(cx, tube_bot), bulb_r, bulb_r)
        fill_h = (tube_bot - tube_top) * max(0, min(1, ratio))
        p.setBrush(color); p.setPen(Qt.NoPen)
        p.drawRoundedRect(QRectF(cx - tube_w // 4, tube_bot - fill_h, tube_w // 2, fill_h), tube_w // 4, tube_w // 4)
        p.drawEllipse(QPointF(cx, tube_bot), bulb_r * 0.7, bulb_r * 0.7)
        p.setPen(QColor("#999")); p.setFont(QFont("Arial", 7))
        for i in range(11):
            y = tube_top + (tube_bot - tube_top) * (1 - i / 10)
            p.drawLine(cx + tube_w // 2, y, cx + tube_w // 2 + 6, y)
            if i % 5 == 0:
                val = self._min + (self._max - self._min) * i / 10
                p.drawText(cx + tube_w // 2 + 8, y - 8, 40, 16, Qt.AlignLeft | Qt.AlignVCenter, f"{val:.0f}")
        p.setPen(QColor("#333")); p.setFont(QFont("Microsoft YaHei", 9, QFont.Bold))
        p.drawText(QRectF(0, 0, w, 18), Qt.AlignCenter, self._title)
        p.drawText(QRectF(0, h - 16, w, 16), Qt.AlignCenter, f"{self._value:.1f}{self._unit}")
        p.end()


# ═══════════════════════════════════════════════════════════════
# 13. 数字倒计时/计时器
# ═══════════════════════════════════════════════════════════════
class CountdownWidget(QWidget):
    """设备节拍时间、报警倒计时"""
    _display_name = "⏱️ 计时器"
    timeout = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._seconds = 0; self._running = False; self._count_down = False
        self._timer = QTimer(self); self._timer.timeout.connect(self._tick)
        self.setMinimumSize(160, 50)

    def setValue(self, v):
        if isinstance(v, (int, float)): self._seconds = int(v)
        elif isinstance(v, str) and ":" in v:
            parts = v.split(":"); self._seconds = int(parts[0]) * 60 + int(parts[1])
        self.update()
    def start(self, count_down=False): self._count_down = count_down; self._running = True; self._timer.start(1000)
    def stop(self): self._running = False; self._timer.stop()
    def reset(self): self._seconds = 0; self.update()

    def _tick(self):
        if self._count_down:
            if self._seconds > 0: self._seconds -= 1
            else: self.stop(); self.timeout.emit()
        else: self._seconds += 1
        self.update()

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, QColor("#1a1a2e"))
        m, s = divmod(abs(self._seconds), 60); hh, mm = divmod(m, 60)
        txt = f"{hh:02d}:{mm:02d}:{s:02d}" if hh else f"{mm:02d}:{s:02d}"
        color = "#e74c3c" if self._count_down and self._seconds <= 10 else "#00ff88"
        p.setPen(QColor(color)); p.setFont(QFont("Consolas", min(h // 2, 28), QFont.Bold))
        p.drawText(QRectF(0, 0, w, h), Qt.AlignCenter, txt)
        if not self._running and self._seconds > 0:
            p.setPen(QColor("#ffffff40")); p.setFont(QFont("Arial", 9))
            p.drawText(QRectF(0, h - 14, w, 14), Qt.AlignCenter, "PAUSED")
        p.end()


# ═══════════════════════════════════════════════════════════════
# 14. 十字准星/坐标指示器
# ═══════════════════════════════════════════════════════════════
class CrosshairWidget(QWidget):
    """视觉检测、运动控制XY坐标显示"""
    _display_name = "🎯 坐标指示器"
    positionChanged = Signal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._x = 50; self._y = 50
        self._color = "#00ff88"
        self.setMinimumSize(150, 150)
        self.setMouseTracking(True)

    def setValue(self, v):
        if isinstance(v, (list, tuple)) and len(v) >= 2:
            self._x, self._y = float(v[0]), float(v[1])
        elif isinstance(v, dict):
            self._x = float(v.get("x", self._x)); self._y = float(v.get("y", self._y))
        self.update()

    def mouseMoveEvent(self, e):
        self._x = e.position().x() / max(1, self.width()) * 100
        self._y = e.position().y() / max(1, self.height()) * 100
        self.positionChanged.emit(self._x, self._y); self.update()

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, QColor("#0d0d0d"))
        p.setPen(QColor("#1a1a1a"))
        for i in range(0, w, 20): p.drawLine(i, 0, i, h)
        for i in range(0, h, 20): p.drawLine(0, i, w, i)
        cx = self._x / 100 * w; cy = self._y / 100 * h
        pen = QPen(QColor(self._color), 1); p.setPen(pen)
        p.drawLine(cx, 0, cx, h); p.drawLine(0, cy, w, cy)
        p.drawEllipse(QPointF(cx, cy), 8, 8)
        p.setPen(QColor(self._color)); p.setFont(QFont("Consolas", 10))
        p.drawText(4, 14, f"X:{self._x:.1f} Y:{self._y:.1f}")
        p.end()


# ═══════════════════════════════════════════════════════════════
# 15. 电池电量指示器
# ═══════════════════════════════════════════════════════════════
class BatteryWidget(QWidget):
    """AGV/UPS电量显示，带低电量告警"""
    _display_name = "🔋 电池电量"
    valueChanged = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 80; self._max = 100; self._charging = False
        self.setMinimumSize(60, 30)

    def setValue(self, v):
        if isinstance(v, str) and "+" in v:
            self._charging = True; v = v.replace("+", "")
        else: self._charging = False
        self._value = max(0, min(self._max, float(v)))
        self.valueChanged.emit(self._value); self.update()

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        bw, bh = w - 8, h - 4
        p.setPen(QPen(QColor("#666"), 2)); p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(QRectF(2, 2, bw, bh), 4, 4)
        p.fillRect(bw + 2, h // 2 - 4, 4, 8, QColor("#666"))
        ratio = self._value / max(1, self._max)
        if ratio > 0.5: color = QColor("#27AE60")
        elif ratio > 0.2: color = QColor("#F39C12")
        else: color = QColor("#E74C3C")
        fill_w = max(0, (bw - 6) * ratio)
        p.setBrush(color); p.setPen(Qt.NoPen)
        p.drawRoundedRect(QRectF(5, 5, fill_w, bh - 6), 2, 2)
        if self._charging:
            p.setPen(QColor("#fff")); p.setFont(QFont("Arial", max(10, bh // 2), QFont.Bold))
            p.drawText(QRectF(2, 2, bw, bh), Qt.AlignCenter, "⚡")
        else:
            p.setPen(QColor("#fff")); p.setFont(QFont("Arial", max(8, bh // 3)))
            p.drawText(QRectF(2, 2, bw, bh), Qt.AlignCenter, f"{self._value:.0f}%")
        p.end()


# ═══════════════════════════════════════════════════════════════
# 16. 精密旋钮编码器
# ═══════════════════════════════════════════════════════════════
class RotaryEncoderWidget(QWidget):
    """鼠标拖拽旋转的精密参数调节旋钮"""
    _display_name = "🎛️ 精密旋钮"
    valueChanged = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 0; self._min = 0; self._max = 100; self._step = 1
        self._title = ""; self._drag_start_y = None; self._drag_start_val = None
        self.setMinimumSize(80, 80); self.setCursor(Qt.ClosedHandCursor)

    def setValue(self, v):
        self._value = max(self._min, min(self._max, float(v)))
        self.valueChanged.emit(self._value); self.update()
    def setRange(self, mn, mx): self._min = float(mn); self._max = float(mx); self.update()
    def setStep(self, s): self._step = max(0.01, float(s))

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_start_y = e.position().y(); self._drag_start_val = self._value
            self.setCursor(Qt.BlankCursor)

    def mouseMoveEvent(self, e):
        if self._drag_start_y is not None:
            delta = self._drag_start_y - e.position().y()
            self.setValue(self._drag_start_val + delta * self._step)

    def mouseReleaseEvent(self, e):
        self._drag_start_y = None; self.setCursor(Qt.ClosedHandCursor)

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        s = min(self.width(), self.height()) - 8; cx, cy = self.width() / 2, self.height() / 2
        r = s / 2
        p.setPen(QPen(QColor("#ccc"), 1))
        for i in range(20):
            ang = (225 + 270 * i / 19) * math.pi / 180
            x1, y1 = cx + r * 0.85 * math.cos(ang), cy - r * 0.85 * math.sin(ang)
            x2, y2 = cx + r * math.cos(ang), cy - r * math.sin(ang)
            p.drawLine(QPointF(x1, y1), QPointF(x2, y2))
        grad = QRadialGradient(cx, cy, r * 0.7)
        grad.setColorAt(0, QColor("#555")); grad.setColorAt(1, QColor("#222"))
        p.setBrush(grad); p.setPen(QPen(QColor("#444"), 2))
        p.drawEllipse(QPointF(cx, cy), r * 0.65, r * 0.65)
        ratio = (self._value - self._min) / max(0.001, self._max - self._min)
        ang = (225 + 270 * ratio) * math.pi / 180
        px, py = cx + r * 0.5 * math.cos(ang), cy - r * 0.5 * math.sin(ang)
        p.setPen(QPen(QColor("#4A90D9"), 3, Qt.SolidLine))
        p.drawLine(QPointF(cx, cy), QPointF(px, py))
        p.setPen(QColor("#ddd")); p.setFont(QFont("Arial", max(9, s // 7), QFont.Bold))
        p.drawText(QRectF(0, cy + r * 0.1, self.width(), r * 0.4), Qt.AlignCenter, f"{self._value:.1f}")
        if self._title:
            p.setFont(QFont("Microsoft YaHei", max(7, s // 10)))
            p.setPen(QColor("#999"))
            p.drawText(QRectF(0, cy + r * 0.45, self.width(), r * 0.3), Qt.AlignCenter, self._title)
        p.end()


# ═══════════════════════════════════════════════════════════════
# 17. 段码数码管
# ═══════════════════════════════════════════════════════════════
class SegmentDisplayWidget(QWidget):
    """复古/工业风格数字显示 - 终极修复版"""
    _display_name = "📟 数码管"
    
    # 7段数码管几何定义 (0~1 相对坐标)，留有余量防止贴边
    SEGMENTS = {
        'a': [(0.15, 0.05), (0.85, 0.05)], # Top
        'b': [(0.90, 0.10), (0.90, 0.45)], # Top-Right
        'c': [(0.90, 0.55), (0.90, 0.90)], # Bottom-Right
        'd': [(0.15, 0.95), (0.85, 0.95)], # Bottom
        'e': [(0.10, 0.55), (0.10, 0.90)], # Bottom-Left
        'f': [(0.10, 0.10), (0.10, 0.45)], # Top-Left
        'g': [(0.15, 0.50), (0.85, 0.50)]  # Middle
    }
    
    DIGIT_MAP = {
        '0': 'abcdef', '1': 'bc', '2': 'abged', '3': 'abgcd', '4': 'fgbc',
        '5': 'afgcd', '6': 'afgcde', '7': 'abc', '8': 'abcdefg', '9': 'abcdfg', 
        '-': 'g', ' ': '', 'E': 'adefg', 'r': 'eg', 'o': 'abdeg'
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._text = "0"
        self._color_on = "#FF2020"   # 亮红色（高可见度）
        self._color_off = "#444444"  # 中灰色（熄灭状态），与暗背景有区分
        self._digits = 4
        self._decimal = 0
        # 设置合理的最小尺寸，防止过小无法绘制
        self.setMinimumSize(120, 40)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        # 启用自动背景填充，确保在浅色画布上也能看到数码管背景
        self.setAutoFillBackground(True)
        pal = self.palette()
        pal.setColor(self.backgroundRole(), QColor("#1a1a1a"))
        self.setPalette(pal)

    def setValue(self, v):
        """兼容 DataBinder: 支持 float, int, str"""
        if v is None or v == "":
            self._text = " " * self._digits
            self.update()
            return
            
        try:
            val = float(v)
            # 格式化字符串，例如 4位1小数: {:>4.1f}
            fmt = f"{{:>{self._digits}.{self._decimal}f}}"
            formatted = fmt.format(val)
            # 截取有效位数，防止溢出
            self._text = formatted[:self._digits + (1 if self._decimal > 0 else 0)]
        except (ValueError, TypeError):
            # 非数字直接显示字符串
            self._text = str(v)[:self._digits]
        
        # 强制重绘
        self.update()

    def value(self):
        """供模拟器读取当前值"""
        try: 
            # 移除空格后尝试转换
            clean_text = self._text.replace(" ", "").replace("-", "")
            return float(clean_text) if clean_text else 0.0
        except: 
            return 0.0

    def setDigits(self, n): 
        self._digits = max(1, int(n))
        self.update()
        
    def setDecimal(self, d): 
        self._decimal = max(0, int(d))
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        
        w, h = self.width(), self.height()
        
        # 1. 计算每个数字的宽度和高度，留出边距
        margin_x = 4
        margin_y = 4
        usable_w = w - 2 * margin_x
        usable_h = h - 2 * margin_y
        
        if usable_w <= 0 or usable_h <= 0:
            p.end()
            return

        dw = usable_w / max(1, self._digits)
        dh = usable_h
        
        # 右对齐显示：如果文本长度不足位数，前面补空格
        display_text = self._text.rjust(self._digits)
        
        for i, ch in enumerate(display_text[:self._digits]):
            # 计算当前数字的局部坐标原点
            ox = margin_x + i * dw
            oy = margin_y
            
            # 获取该字符对应的亮段
            active_segs = self.DIGIT_MAP.get(ch.lower(), '')
            
            for seg_name, pts in self.SEGMENTS.items():
                # 判断该段是否点亮
                is_on = seg_name in active_segs
                color = QColor(self._color_on) if is_on else QColor(self._color_off)
                
                # 线段宽度随控件高度自适应，保证高可见度
                pen_width = max(3, int(dh * 0.12))
                pen = QPen(color, pen_width, Qt.SolidLine)
                p.setPen(pen)
                
                # 将相对坐标 (0~1) 转换为绝对像素坐标
                x1 = ox + pts[0][0] * dw
                y1 = oy + pts[0][1] * dh
                x2 = ox + pts[1][0] * dw
                y2 = oy + pts[1][1] * dh
                
                p.drawLine(QPointF(x1, y1), QPointF(x2, y2))
                
        p.end()
# ═══════════════════════════════════════════════════════════════
# 18. 管道流向指示器
# ═══════════════════════════════════════════════════════════════
class PipeFlowWidget(QWidget):
    """流程工业管道介质流动方向和状态"""
    _display_name = "🚥 管道流向"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._flowing = False; self._direction = "right"
        self._color = "#4A90D9"; self._phase = 0.0
        self._timer = QTimer(self); self._timer.timeout.connect(self._animate)
        self.setMinimumSize(120, 30)

    def setValue(self, v):
        self._flowing = bool(v) if not isinstance(v, str) else v.lower() not in ("stop", "0", "false", "")
        if self._flowing and not self._timer.isActive(): self._timer.start(80)
        elif not self._flowing: self._timer.stop(); self._phase = 0
        self.update()

    def setDirection(self, d): self._direction = d; self.update()
    def setColor(self, c): self._color = c; self.update()
    def _animate(self): self._phase += 0.3; self.update()

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        is_h = self._direction in ("left", "right")
        pipe_w = min(h, w) * 0.4 if is_h else min(w, h) * 0.4
        p.setBrush(QColor("#555")); p.setPen(Qt.NoPen)
        if is_h: p.drawRoundedRect(QRectF(0, (h - pipe_w) / 2, w, pipe_w), pipe_w / 4, pipe_w / 4)
        else: p.drawRoundedRect(QRectF((w - pipe_w) / 2, 0, pipe_w, h), pipe_w / 4, pipe_w / 4)
        if self._flowing:
            p.setPen(QPen(QColor(self._color), max(2, pipe_w * 0.15)))
            arrow_count = max(2, int((w if is_h else h) / 30))
            for i in range(arrow_count):
                offset = ((i / arrow_count) + self._phase * (1 if self._direction in ("right", "down") else -1)) % 1.0
                if is_h:
                    ax = offset * w; ay = h / 2
                    dx = 6 if self._direction == "right" else -6
                    p.drawLine(QPointF(ax - dx, ay - 4), QPointF(ax, ay))
                    p.drawLine(QPointF(ax - dx, ay + 4), QPointF(ax, ay))
                else:
                    ax = w / 2; ay = offset * h
                    dy = 6 if self._direction == "down" else -6
                    p.drawLine(QPointF(ax - 4, ay - dy), QPointF(ax, ay))
                    p.drawLine(QPointF(ax + 4, ay - dy), QPointF(ax, ay))
        else:
            p.setPen(QColor("#777")); p.setFont(QFont("Arial", max(8, pipe_w // 3)))
            p.drawText(QRectF(0, 0, w, h), Qt.AlignCenter, "STOP")
        p.end()
    # ═══════════════════════════════════════════════════════════════
# 19. 步进/伺服电机状态指示器
# ═══════════════════════════════════════════════════════════════
class MotorStatusWidget(QWidget):
    """电机运行状态可视化：转速环 + 方向箭头 + 故障闪烁"""
    _display_name = "⚙️ 电机状态"
    valueChanged = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rpm = 0; self._max_rpm = 3000; self._direction = "cw"  # cw/ccw/stop
        self._fault = False; self._title = "M-01"
        self._blink_phase = 0.0
        self._timer = QTimer(self); self._timer.timeout.connect(self._animate)
        self.setMinimumSize(120, 120)

    def setValue(self, v):
        if isinstance(v, dict):
            self._rpm = float(v.get("rpm", self._rpm))
            self._direction = str(v.get("dir", self._direction))
            self._fault = bool(v.get("fault", self._fault))
        elif isinstance(v, (int, float)):
            self._rpm = float(v)
        self.valueChanged.emit(self._rpm)
        if self._fault and not self._timer.isActive(): self._timer.start(200)
        elif not self._fault: self._timer.stop(); self._blink_phase = 0
        self.update()

    def _animate(self):
        self._blink_phase += 1.0; self.update()

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2; r = min(w, h) / 2 - 8

        # 故障闪烁背景
        if self._fault and int(self._blink_phase) % 2 == 0:
            p.fillRect(0, 0, w, h, QColor("#E74C3C"))

        # 外圈
        p.setPen(QPen(QColor("#555"), 3)); p.setBrush(QColor("#2a2a2a"))
        p.drawEllipse(QPointF(cx, cy), r, r)

        # 转速弧
        ratio = max(0, min(1, self._rpm / max(1, self._max_rpm)))
        if ratio > 0.8: arc_color = QColor("#E74C3C")
        elif ratio > 0.5: arc_color = QColor("#F39C12")
        else: arc_color = QColor("#4A90D9")
        pen_w = max(4, r / 8)
        p.setPen(QPen(arc_color, pen_w, Qt.SolidLine)); p.setBrush(Qt.NoBrush)
        start_ang = 225 if self._direction != "ccw" else 315
        span = int(-270 * 16 * ratio) if self._direction != "ccw" else int(270 * 16 * ratio)
        p.drawArc(QRectF(cx - r + pen_w, cy - r + pen_w, (r - pen_w) * 2, (r - pen_w) * 2),
                  start_ang * 16, span)

        # 方向箭头
        p.setPen(QPen(QColor("#ddd"), max(2, r / 15), Qt.SolidLine))
        arrow_r = r * 0.45
        if self._direction == "cw":
            ang = math.pi / 4
            ax, ay = cx + arrow_r * math.cos(ang), cy - arrow_r * math.sin(ang)
            p.drawLine(QPointF(cx, cy), QPointF(ax, ay))
            p.drawLine(QPointF(ax, ay), QPointF(ax - 8, ay - 4))
            p.drawLine(QPointF(ax, ay), QPointF(ax + 2, ay - 10))
        elif self._direction == "ccw":
            ang = 3 * math.pi / 4
            ax, ay = cx + arrow_r * math.cos(ang), cy - arrow_r * math.sin(ang)
            p.drawLine(QPointF(cx, cy), QPointF(ax, ay))
            p.drawLine(QPointF(ax, ay), QPointF(ax + 8, ay - 4))
            p.drawLine(QPointF(ax, ay), QPointF(ax - 2, ay - 10))
        else:
            p.setPen(QColor("#888")); p.setFont(QFont("Arial", max(8, r // 5)))
            p.drawText(QRectF(cx - r * 0.4, cy - r * 0.15, r * 0.8, r * 0.3),
                       Qt.AlignCenter, "STOP")

        # RPM数值
        p.setPen(QColor("#fff")); p.setFont(QFont("Consolas", max(9, r // 4), QFont.Bold))
        p.drawText(QRectF(0, cy + r * 0.15, w, r * 0.35), Qt.AlignCenter, f"{self._rpm:.0f}")
        p.setFont(QFont("Arial", max(7, r // 7))); p.setPen(QColor("#aaa"))
        p.drawText(QRectF(0, cy + r * 0.45, w, r * 0.2), Qt.AlignCenter, "RPM")

        # 标题
        if self._title:
            p.setFont(QFont("Microsoft YaHei", max(7, r // 7)))
            p.setPen(QColor("#ccc"))
            p.drawText(QRectF(0, 2, w, 16), Qt.AlignCenter, self._title)
        p.end()


# ═══════════════════════════════════════════════════════════════
# 20. 阀门开度指示器
# ═══════════════════════════════════════════════════════════════
class ValvePositionWidget(QWidget):
    """蝶阀/球阀开度可视化，带流向箭头"""
    _display_name = "🔧 阀门开度"
    valueChanged = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._position = 0  # 0~100%
        self._title = "V-101"; self._flowing = False
        self.setMinimumSize(100, 80)

    def setValue(self, v):
        self._position = max(0, min(100, float(v)))
        self.valueChanged.emit(self._position); self.update()

    def setFlowing(self, f): self._flowing = bool(f); self.update()

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        pipe_h = min(20, h // 4)

        # 管道
        p.setBrush(QColor("#555")); p.setPen(Qt.NoPen)
        p.drawRect(0, cy - pipe_h // 2, w, pipe_h)

        # 阀体（圆形）
        valve_r = min(w, h) // 3
        p.setBrush(QColor("#444")); p.setPen(QPen(QColor("#666"), 2))
        p.drawEllipse(QPointF(cx, cy), valve_r, valve_r)

        # 蝶板（根据开度旋转）
        angle = 90 - self._position * 0.9  # 0%=垂直(关闭), 100%=水平(全开)
        rad = math.radians(angle)
        half_len = valve_r * 0.85
        x1 = cx + half_len * math.cos(rad); y1 = cy - half_len * math.sin(rad)
        x2 = cx - half_len * math.cos(rad); y2 = cy + half_len * math.sin(rad)
        color = QColor("#27AE60") if self._position > 80 else (
                QColor("#F39C12") if self._position > 20 else QColor("#E74C3C"))
        p.setPen(QPen(color, max(3, valve_r // 6), Qt.SolidLine))
        p.drawLine(QPointF(x1, y1), QPointF(x2, y2))

        # 开度百分比
        p.setPen(QColor("#fff")); p.setFont(QFont("Arial", max(8, valve_r // 3), QFont.Bold))
        p.drawText(QRectF(cx - valve_r, cy - valve_r, valve_r * 2, valve_r * 2),
                   Qt.AlignCenter, f"{self._position:.0f}%")

        # 流向箭头
        if self._flowing and self._position > 5:
            p.setPen(QPen(QColor("#4A90D9"), 2))
            for dx in [-w // 3, w // 3]:
                ax = cx + dx
                p.drawLine(QPointF(ax - 6, cy - 4), QPointF(ax, cy))
                p.drawLine(QPointF(ax - 6, cy + 4), QPointF(ax, cy))

        # 标题
        if self._title:
            p.setPen(QColor("#ccc")); p.setFont(QFont("Microsoft YaHei", max(7, h // 10)))
            p.drawText(QRectF(0, 0, w, 14), Qt.AlignCenter, self._title)
        p.end()


# ═══════════════════════════════════════════════════════════════
# 21. 信号强度/WiFi指示器
# ═══════════════════════════════════════════════════════════════
class SignalStrengthWidget(QWidget):
    """通信信号强度条状指示"""
    _display_name = "📶 信号强度"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._level = 0; self._max_level = 5; self._label = ""
        self.setMinimumSize(60, 40)

    def setValue(self, v):
        self._level = max(0, min(self._max_level, int(float(v))))
        self.update()

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        bar_count = self._max_level
        bar_w = max(4, (w - 8) // bar_count - 2)
        gap = (w - 8 - bar_w * bar_count) / max(1, bar_count - 1) if bar_count > 1 else 0
        base_y = h - 6

        for i in range(bar_count):
            x = 4 + i * (bar_w + gap)
            bar_h = (h - 12) * (i + 1) / bar_count
            active = i < self._level
            if active:
                if self._level <= 1: color = QColor("#E74C3C")
                elif self._level <= 2: color = QColor("#F39C12")
                else: color = QColor("#27AE60")
            else:
                color = QColor("#444")
            p.setBrush(color); p.setPen(Qt.NoPen)
            p.drawRoundedRect(QRectF(x, base_y - bar_h, bar_w, bar_h), 2, 2)

        if self._label:
            p.setPen(QColor("#ccc")); p.setFont(QFont("Arial", max(7, h // 5)))
            p.drawText(QRectF(0, 0, w, 12), Qt.AlignCenter, self._label)
        p.end()


# ═══════════════════════════════════════════════════════════════
# 22. 迷你趋势火花线 (Sparkline)
# ═══════════════════════════════════════════════════════════════
class SparklineWidget(QWidget):
    """紧凑型数据趋势线，适合嵌入表格或卡片"""
    _display_name = "📈 火花线"
    MAX_POINTS = 60

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data = []; self._color = "#4A90D9"
        self._min_val = None; self._max_val = None
        self.setMinimumSize(120, 30); self.setMaximumHeight(50)

    def setValue(self, v):
        try: val = float(v)
        except: return
        self._data.append(val)
        if len(self._data) > self.MAX_POINTS: self._data.pop(0)
        if self._min_val is None or val < self._min_val: self._min_val = val
        if self._max_val is None or val > self._max_val: self._max_val = val
        self.update()

    def reset(self):
        self._data.clear(); self._min_val = None; self._max_val = None; self.update()

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, QColor("#fafafa"))

        if len(self._data) < 2: 
            p.setPen(QColor("#ccc")); p.setFont(QFont("Arial", 9))
            p.drawText(QRectF(0, 0, w, h), Qt.AlignCenter, "—")
            p.end(); return

        rng = max(0.001, (self._max_val or 0) - (self._min_val or 0))
        pad = h * 0.1
        path = QPainterPath()
        for i, val in enumerate(self._data):
            x = w * i / max(1, len(self._data) - 1)
            y = h - pad - (val - (self._min_val or 0)) / rng * (h - 2 * pad)
            if i == 0: path.moveTo(x, y)
            else: path.lineTo(x, y)

        # 填充渐变
        grad = QLinearGradient(0, 0, 0, h)
        c = QColor(self._color)
        grad.setColorAt(0, QColor(c.red(), c.green(), c.blue(), 80))
        grad.setColorAt(1, QColor(c.red(), c.green(), c.blue(), 0))
        fill_path = QPainterPath(path)
        fill_path.lineTo(w, h); fill_path.lineTo(0, h); fill_path.closeSubpath()
        p.setBrush(grad); p.setPen(Qt.NoPen); p.drawPath(fill_path)

        # 线条
        p.setPen(QPen(QColor(self._color), 1.5)); p.setBrush(Qt.NoBrush)
        p.drawPath(path)

        # 最新值标注
        last = self._data[-1]
        p.setPen(QColor(self._color)); p.setFont(QFont("Arial", max(8, h // 3), QFont.Bold))
        p.drawText(QRectF(w - 50, 0, 48, h), Qt.AlignRight | Qt.AlignVCenter, f"{last:.1f}")
        p.end()


# ═══════════════════════════════════════════════════════════════
# 23. 告警消息横幅
# ═══════════════════════════════════════════════════════════════
class AlarmBannerWidget(QWidget):
    """顶部/底部滚动告警横幅，支持多级别"""
    _display_name = "🚨 告警横幅"
    alarm_clicked = Signal(str)

    LEVELS = {
        "info": ("#3498db", "#ebf5fb", "ℹ️"),
        "warning": ("#F39C12", "#fef9e7", "⚠️"),
        "danger": ("#E74C3C", "#fdedec", "🚨"),
        "success": ("#27AE60", "#eafaf1", "✅"),
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._message = ""; self._level = "info"
        self._scroll_offset = 0; self._auto_scroll = False
        self._timer = QTimer(self); self._timer.timeout.connect(self._tick)
        self.setMinimumSize(300, 32); self.setMaximumHeight(48)
        self.setCursor(Qt.PointingHandCursor)

    def setValue(self, v):
        if isinstance(v, dict):
            self._message = str(v.get("msg", ""))
            self._level = str(v.get("level", "info"))
        else:
            self._message = str(v)
        self._auto_scroll = len(self._message) > 40
        if self._auto_scroll and not self._timer.isActive():
            self._timer.start(50)
        elif not self._auto_scroll:
            self._timer.stop(); self._scroll_offset = 0
        self.update()

    def _tick(self):
        self._scroll_offset += 1; self.update()

    def mousePressEvent(self, e):
        if self._message: self.alarm_clicked.emit(self._message)

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        fg, bg, icon = self.LEVELS.get(self._level, self.LEVELS["info"])

        p.fillRect(0, 0, w, h, QColor(bg))
        p.setPen(QColor(fg)); p.setFont(QFont("Microsoft YaHei", max(10, h // 3), QFont.Bold))

        text = f"{icon}  {self._message}"
        fm = QFontMetrics(p.font())
        tw = fm.horizontalAdvance(text)

        if self._auto_scroll and tw > w:
            total = tw + w
            x = w - (self._scroll_offset % total)
            p.drawText(x, h // 2 + fm.ascent() // 3, text)
            if x + tw < 0:
                p.drawText(x + total, h // 2 + fm.ascent() // 3, text)
        else:
            p.drawText(QRectF(8, 0, w - 16, h), Qt.AlignVCenter, text)

        # 底部边线
        p.setPen(QColor(fg)); p.drawLine(0, h - 1, w, h - 1)
        p.end()


# ═══════════════════════════════════════════════════════════════
# 24. 雷达/极坐标扫描显示器
# ═══════════════════════════════════════════════════════════════
class RadarScanWidget(QWidget):
    """极坐标扫描显示，适用于AGV定位、传感器探测范围"""
    _display_name = "📡 雷达扫描"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._angle = 0.0; self._targets = []  # [(angle, distance, label)]
        self._max_range = 100; self._sweep_speed = 2.0
        self._timer = QTimer(self); self._timer.timeout.connect(self._tick)
        self._timer.start(30)
        self.setMinimumSize(160, 160)

    def setValue(self, v):
        """接收目标列表: [{"a": 45, "d": 60, "l": "T1"}, ...]"""
        if isinstance(v, list):
            self._targets = []
            for item in v:
                if isinstance(item, dict):
                    self._targets.append((
                        float(item.get("a", 0)),
                        float(item.get("d", 0)),
                        str(item.get("l", ""))
                    ))
            self.update()

    def setMaxRange(self, r): self._max_range = max(1, float(r)); self.update()

    def _tick(self):
        self._angle = (self._angle + self._sweep_speed) % 360; self.update()

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2; r = min(w, h) / 2 - 6

        # 深色背景
        p.fillRect(0, 0, w, h, QColor("#0a0a0a"))

        # 同心圆网格
        p.setPen(QPen(QColor("#1a3a1a"), 1))
        for i in range(1, 5):
            cr = r * i / 4
            p.drawEllipse(QPointF(cx, cy), cr, cr)
        # 十字线
        p.drawLine(cx, cy - r, cx, cy + r)
        p.drawLine(cx - r, cy, cx + r, cy)

        # 扫描扇形拖尾
        sweep_path = QPainterPath()
        sweep_path.moveTo(cx, cy)
        for da in range(0, 40, 2):
            a = math.radians(self._angle - da)
            sx = cx + r * math.cos(a); sy = cy - r * math.sin(a)
            sweep_path.lineTo(sx, sy)
        sweep_path.closeSubpath()
        grad = QConicalGradient(cx, cy, self._angle)
        grad.setColorAt(0.0, QColor(0, 255, 0, 0))
        grad.setColorAt(0.08, QColor(0, 255, 0, 60))
        grad.setColorAt(0.11, QColor(0, 255, 0, 0))
        p.setBrush(grad); p.setPen(Qt.NoPen); p.drawPath(sweep_path)

        # 扫描线
        rad = math.radians(self._angle)
        lx = cx + r * math.cos(rad); ly = cy - r * math.sin(rad)
        p.setPen(QPen(QColor("#00ff00"), 2))
        p.drawLine(QPointF(cx, cy), QPointF(lx, ly))

        # 目标点
        for ta, td, tl in self._targets:
            dist_ratio = min(1, td / max(1, self._max_range))
            tx = cx + r * dist_ratio * math.cos(math.radians(ta))
            ty = cy - r * dist_ratio * math.sin(math.radians(ta))
            # 距离扫描线越近越亮
            diff = abs((self._angle - ta) % 360)
            if diff > 180: diff = 360 - diff
            alpha = max(40, int(255 * max(0, 1 - diff / 60)))
            p.setBrush(QColor(0, 255, 0, alpha)); p.setPen(Qt.NoPen)
            p.drawEllipse(QPointF(tx, ty), 4, 4)
            if tl and alpha > 100:
                p.setPen(QColor(0, 255, 0, alpha))
                p.setFont(QFont("Consolas", 8))
                p.drawText(tx + 6, ty - 4, tl)

        # 距离标注
        p.setPen(QColor("#335533")); p.setFont(QFont("Arial", 7))
        for i in range(1, 5):
            val = self._max_range * i / 4
            p.drawText(cx + 2, cy - r * i / 4 + 10, f"{val:.0f}")
        p.end()
    # ═══════════════════════════════════════════════════════════════
# 25. CNC轴位置/光栅尺指示器
# ═══════════════════════════════════════════════════════════════
class AxisPositionWidget(QWidget):
    """数控机床/运动控制轴位置显示，带刻度尺和零点标记"""
    _display_name = "📏 轴位置"
    valueChanged = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 0.0; self._unit = "mm"; self._axis_label = "X"
        self._min_val = -500; self._max_val = 500; self._decimals = 3
        self.setMinimumSize(280, 50); self.setMaximumHeight(70)

    def setValue(self, v):
        self._value = float(v)
        self.valueChanged.emit(self._value); self.update()

    def setRange(self, mn, mx): self._min_val = float(mn); self._max_val = float(mx); self.update()
    def setAxisLabel(self, lbl): self._axis_label = str(lbl); self.update()
    def setUnit(self, u): self._unit = str(u); self.update()
    def setDecimals(self, d): self._decimals = max(0, int(d)); self.update()

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        # 背景
        p.fillRect(0, 0, w, h, QColor("#1a1a2e"))
        # 轴标签
        p.setPen(QColor("#4A90D9")); p.setFont(QFont("Arial", max(14, h // 3), QFont.Bold))
        p.drawText(QRectF(4, 0, 30, h), Qt.AlignCenter, self._axis_label)
        # 数值显示区
        val_text = f"{self._value:.{self._decimals}f}"
        p.setPen(QColor("#00ff88")); p.setFont(QFont("Consolas", max(16, h // 2.5), QFont.Bold))
        p.drawText(QRectF(36, 0, w - 100, h), Qt.AlignVCenter | Qt.AlignRight, val_text)
        # 单位
        p.setPen(QColor("#888")); p.setFont(QFont("Arial", max(9, h // 5)))
        p.drawText(QRectF(w - 58, 0, 54, h), Qt.AlignVCenter | Qt.AlignLeft, self._unit)
        # 底部刻度条
        bar_y = h - 10; bar_h = 6; bar_x = 36; bar_w = w - 100
        p.setBrush(QColor("#333")); p.setPen(Qt.NoPen)
        p.drawRoundedRect(QRectF(bar_x, bar_y, bar_w, bar_h), 3, 3)
        # 当前位置指示
        ratio = (self._value - self._min_val) / max(0.001, self._max_val - self._min_val)
        ratio = max(0, min(1, ratio))
        pos_x = bar_x + bar_w * ratio
        p.setBrush(QColor("#4A90D9"))
        p.drawEllipse(QPointF(pos_x, bar_y + bar_h / 2), 5, 5)
        # 零点标记
        zero_ratio = (0 - self._min_val) / max(0.001, self._max_val - self._min_val)
        if 0 <= zero_ratio <= 1:
            zx = bar_x + bar_w * zero_ratio
            p.setPen(QPen(QColor("#F39C12"), 1))
            p.drawLine(zx, bar_y - 2, zx, bar_y + bar_h + 2)
        p.end()


# ═══════════════════════════════════════════════════════════════
# 26. 半导体晶圆/圆形布局显示器
# ═══════════════════════════════════════════════════════════════
class WaferMapWidget(QWidget):
    """晶圆Die Map / 圆形区域热力图显示"""
    _display_name = "💿 晶圆图"
    die_clicked = Signal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows = 12; self._cols = 12
        self._data = {}  # {(r,c): value}
        self._title = "Wafer Map"; self._notch_angle = 270
        self.setMinimumSize(180, 180)

    def setValue(self, v):
        """接收字典 {(row,col): value} 或二维列表"""
        if isinstance(v, dict):
            self._data = {tuple(k): float(val) for k, val in v.items()}
        elif isinstance(v, list):
            self._data = {}
            for r, row_data in enumerate(v):
                if isinstance(row_data, (list, tuple)):
                    for c, val in enumerate(row_data):
                        self._data[(r, c)] = float(val)
        self.update()

    def setGridSize(self, rows, cols): self._rows = int(rows); self._cols = int(cols); self.update()
    def setTitle(self, t): self._title = str(t); self.update()

    def mousePressEvent(self, e):
        cx, cy = self.width() / 2, self.height() / 2
        r = min(cx, cy) - 12
        dx = e.position().x() - cx; dy = e.position().y() - cy
        if dx * dx + dy * dy > r * r: return
        cell_size = r * 2 / max(self._rows, self._cols)
        col = int((dx + r) / cell_size); row = int((dy + r) / cell_size)
        if 0 <= row < self._rows and 0 <= col < self._cols:
            self.die_clicked.emit(row, col)

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2; radius = min(cx, cy) - 12

        # 晶圆底色
        p.setBrush(QColor("#2a2a3a")); p.setPen(QPen(QColor("#555"), 2))
        p.drawEllipse(QPointF(cx, cy), radius, radius)

        # Notch缺口
        notch_rad = math.radians(self._notch_angle)
        nx = cx + radius * math.cos(notch_rad)
        ny = cy - radius * math.sin(notch_rad)
        p.setBrush(QColor("#1a1a2e")); p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(nx, ny), 6, 6)

        # Die网格
        cell_size = radius * 2 / max(self._rows, self._cols)
        start_x = cx - radius; start_y = cy - radius
        all_vals = list(self._data.values())
        v_min = min(all_vals) if all_vals else 0
        v_max = max(all_vals) if all_vals else 1
        rng = max(0.001, v_max - v_min)

        for r in range(self._rows):
            for c in range(self._cols):
                dx = start_x + c * cell_size + cell_size / 2 - cx
                dy = start_y + r * cell_size + cell_size / 2 - cy
                if dx * dx + dy * dy > (radius - 2) ** 2: continue
                x = start_x + c * cell_size + 1
                y = start_y + r * cell_size + 1
                s = cell_size - 2
                val = self._data.get((r, c))
                if val is not None:
                    ratio = (val - v_min) / rng
                    red = int(50 + 205 * ratio)
                    green = int(200 * (1 - ratio))
                    blue = int(50 + 100 * (1 - ratio))
                    color = QColor(red, green, blue)
                else:
                    color = QColor("#333")
                p.setBrush(color); p.setPen(Qt.NoPen)
                p.drawRect(QRectF(x, y, s, s))

        # 标题
        if self._title:
            p.setPen(QColor("#ccc")); p.setFont(QFont("Microsoft YaHei", max(8, radius // 10)))
            p.drawText(QRectF(0, 0, w, 16), Qt.AlignCenter, self._title)
        p.end()


# ═══════════════════════════════════════════════════════════════
# 27. 堆垛/料仓料位指示器
# ═══════════════════════════════════════════════════════════════
class SiloLevelWidget(QWidget):
    """筒仓/料斗料位可视化，带锥形底部和填充动画"""
    _display_name = "🏗️ 料仓料位"
    valueChanged = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._level = 65; self._max_level = 100; self._unit = "%"
        self._title = "SILO-01"; self._material_color = "#D4AC0D"
        self._phase = 0.0
        self._timer = QTimer(self); self._timer.timeout.connect(self._animate)
        self._timer.start(80)
        self.setMinimumSize(80, 200)

    def setValue(self, v):
        self._level = max(0, min(self._max_level, float(v)))
        self.valueChanged.emit(self._level); self.update()

    def _animate(self): self._phase += 0.15; self.update()

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        margin = 10; silo_w = w - margin * 2
        top_y = margin + 20; body_h = h - margin * 2 - 50
        cone_h = 30

        # 仓体边框
        p.setPen(QPen(QColor("#666"), 2)); p.setBrush(Qt.NoBrush)
        p.drawRect(QRectF(margin, top_y, silo_w, body_h))
        # 锥形底部
        p.drawLine(margin, top_y + body_h, margin + silo_w / 2, top_y + body_h + cone_h)
        p.drawLine(margin + silo_w, top_y + body_h, margin + silo_w / 2, top_y + body_h + cone_h)

        # 物料填充
        ratio = self._level / max(1, self._max_level)
        fill_h = body_h * ratio
        fill_top = top_y + body_h - fill_h

        grad = QLinearGradient(0, fill_top, 0, top_y + body_h)
        base_color = QColor(self._material_color)
        grad.setColorAt(0, base_color.lighter(120))
        grad.setColorAt(1, base_color)
        p.setBrush(grad); p.setPen(Qt.NoPen)
        p.drawRect(QRectF(margin + 2, fill_top, silo_w - 4, fill_h))

        # 物料表面波纹效果
        if ratio > 0.02:
            wave_path = QPainterPath()
            wave_path.moveTo(margin + 2, fill_top)
            for wx in range(int(silo_w - 4)):
                wy = fill_top + 3 * math.sin((wx + self._phase * 20) * 0.1)
                wave_path.lineTo(margin + 2 + wx, wy)
            wave_path.lineTo(margin + silo_w - 2, fill_top + 10)
            wave_path.lineTo(margin + 2, fill_top + 10)
            wave_path.closeSubpath()
            p.setBrush(base_color.lighter(140))
            p.drawPath(wave_path)

        # 刻度线
        p.setPen(QPen(QColor("#999"), 1))
        for i in range(11):
            y = top_y + body_h * (1 - i / 10)
            p.drawLine(margin + silo_w, y, margin + silo_w + 6, y)
            if i % 5 == 0:
                p.setFont(QFont("Arial", 8))
                p.drawText(margin + silo_w + 8, y + 4, f"{i * 10}%")

        # 标题和当前值
        p.setPen(QColor("#333")); p.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        p.drawText(QRectF(0, 2, w, 18), Qt.AlignCenter, self._title)
        p.drawText(QRectF(0, h - 16, w, 16), Qt.AlignCenter, f"{self._level:.1f}{self._unit}")
        p.end()


# ═══════════════════════════════════════════════════════════════
# 28. 能效/功率因数仪表盘
# ═══════════════════════════════════════════════════════════════
class PowerFactorWidget(QWidget):
    """电力监控专用：功率因数/能效等级弧形仪表"""
    _display_name = "⚡ 能效仪表"
    valueChanged = Signal(float)

    ZONES = [
        (0.0, 0.6, "#E74C3C", "差"),
        (0.6, 0.8, "#F39C12", "中"),
        (0.8, 0.95, "#27AE60", "良"),
        (0.95, 1.0, "#4A90D9", "优"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 0.85; self._title = "PF"; self._unit = ""
        self.setMinimumSize(140, 100)

    def setValue(self, v):
        self._value = max(0, min(1.0, float(v)))
        self.valueChanged.emit(self._value); self.update()

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w / 2, h - 10
        r = min(w / 2, h) - 14
        pen_w = max(8, r / 6)
        start_ang = 180; span_ang = 180

        # 分段弧
        for z_min, z_max, color, label in self.ZONES:
            a_start = start_ang + span_ang * z_min
            a_span = span_ang * (z_max - z_min)
            p.setPen(QPen(QColor(color), pen_w, Qt.SolidLine)); p.setBrush(Qt.NoBrush)
            p.drawArc(QRectF(cx - r, cy - r, r * 2, r * 2), int(a_start * 16), int(a_span * 16))

        # 指针
        needle_ang = (start_ang + span_ang * self._value) * math.pi / 180
        nl = r - pen_w / 2 - 4
        nx = cx + nl * math.cos(needle_ang)
        ny = cy - nl * math.sin(needle_ang)
        p.setPen(QPen(QColor("#fff"), max(2, r / 20), Qt.SolidLine))
        p.drawLine(QPointF(cx, cy), QPointF(nx, ny))
        p.setBrush(QColor("#fff")); p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(cx, cy), max(4, r / 12), max(4, r / 12))

        # 数值
        p.setPen(QColor("#fff")); p.setFont(QFont("Consolas", max(14, r / 3), QFont.Bold))
        p.drawText(QRectF(cx - r, cy - r * 0.6, r * 2, r * 0.5), Qt.AlignCenter, f"{self._value:.2f}")
        # 标题
        if self._title:
            p.setFont(QFont("Microsoft YaHei", max(8, r / 6)))
            p.setPen(QColor("#aaa"))
            p.drawText(QRectF(cx - r, cy - r * 0.9, r * 2, r * 0.3), Qt.AlignCenter, self._title)
        # 区间标签
        p.setFont(QFont("Arial", max(7, r / 8)))
        for z_min, z_max, color, label in self.ZONES:
            mid_ang = (start_ang + span_ang * (z_min + z_max) / 2) * math.pi / 180
            lr = r + pen_w / 2 + 8
            lx = cx + lr * math.cos(mid_ang)
            ly = cy - lr * math.sin(mid_ang)
            p.setPen(QColor(color))
            p.drawText(QRectF(lx - 12, ly - 8, 24, 16), Qt.AlignCenter, label)
        p.end()


# ═══════════════════════════════════════════════════════════════
# 29. 传送带/产线速度指示器
# ═══════════════════════════════════════════════════════════════
class ConveyorSpeedWidget(QWidget):
    """传送带运行状态+速度可视化，带滚动纹理动画"""
    _display_name = "🏭 传送带"
    valueChanged = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._speed = 0; self._max_speed = 100; self._unit = "m/min"
        self._running = False; self._direction = "right"
        self._phase = 0.0; self._title = "CV-01"
        self._timer = QTimer(self); self._timer.timeout.connect(self._animate)
        self.setMinimumSize(240, 60)

    def setValue(self, v):
        if isinstance(v, dict):
            self._speed = float(v.get("speed", self._speed))
            self._running = bool(v.get("running", self._speed > 0))
            self._direction = str(v.get("dir", self._direction))
        else:
            self._speed = float(v)
            self._running = self._speed > 0
        self.valueChanged.emit(self._speed)
        if self._running and not self._timer.isActive():
            self._timer.start(30)
        elif not self._running:
            self._timer.stop(); self._phase = 0
        self.update()

    def _animate(self):
        speed_ratio = self._speed / max(1, self._max_speed)
        delta = speed_ratio * 3.0 * (1 if self._direction == "right" else -1)
        self._phase += delta; self.update()

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        belt_y = 20; belt_h = h - 36

        # 皮带底色
        p.setBrush(QColor("#333")); p.setPen(Qt.NoPen)
        p.drawRoundedRect(QRectF(4, belt_y, w - 8, belt_h), 4, 4)

        # 滚动纹理
        if self._running:
            p.setPen(QPen(QColor("#555"), 2))
            stripe_gap = 20
            offset = self._phase % stripe_gap
            for sx in range(-stripe_gap, w + stripe_gap, stripe_gap):
                x = sx + offset
                p.drawLine(x, belt_y + 2, x + 8, belt_y + belt_h - 2)

        # 滚筒两端
        roller_r = belt_h / 2
        p.setBrush(QColor("#666")); p.setPen(QPen(QColor("#888"), 1))
        p.drawEllipse(QPointF(4 + roller_r, belt_y + belt_h / 2), roller_r, roller_r)
        p.drawEllipse(QPointF(w - 4 - roller_r, belt_y + belt_h / 2), roller_r, roller_r)

        # 速度文字
        speed_color = "#00ff88" if self._running else "#888"
        p.setPen(QColor(speed_color)); p.setFont(QFont("Consolas", max(11, belt_h // 2), QFont.Bold))
        txt = f"{self._speed:.1f} {self._unit}" if self._running else "STOPPED"
        p.drawText(QRectF(0, belt_y, w, belt_h), Qt.AlignCenter, txt)

        # 方向箭头
        if self._running:
            p.setPen(QPen(QColor("#4A90D9"), 2))
            arrow_y = belt_y + belt_h + 8
            if self._direction == "right":
                p.drawLine(w // 2 - 15, arrow_y, w // 2 + 15, arrow_y)
                p.drawLine(w // 2 + 10, arrow_y - 4, w // 2 + 15, arrow_y)
                p.drawLine(w // 2 + 10, arrow_y + 4, w // 2 + 15, arrow_y)
            else:
                p.drawLine(w // 2 + 15, arrow_y, w // 2 - 15, arrow_y)
                p.drawLine(w // 2 - 10, arrow_y - 4, w // 2 - 15, arrow_y)
                p.drawLine(w // 2 - 10, arrow_y + 4, w // 2 - 15, arrow_y)

        # 标题
        if self._title:
            p.setPen(QColor("#ccc")); p.setFont(QFont("Microsoft YaHei", max(8, h // 7)))
            p.drawText(QRectF(0, 0, w, 18), Qt.AlignCenter, self._title)
        p.end()


# ═══════════════════════════════════════════════════════════════
# 30. 网络/IO吞吐量双通道仪表
# ═══════════════════════════════════════════════════════════════
class DualThroughputWidget(QWidget):
    """上传/下载或输入/输出双向流量实时显示"""
    _display_name = "🔄 双向流量"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tx = 0; self._rx = 0; self._max_val = 1000
        self._tx_label = "TX"; self._rx_label = "RX"; self._unit = "KB/s"
        self.setMinimumSize(160, 80)

    def setValue(self, v):
        if isinstance(v, dict):
            self._tx = float(v.get("tx", self._tx))
            self._rx = float(v.get("rx", self._rx))
        elif isinstance(v, (list, tuple)) and len(v) >= 2:
            self._tx = float(v[0]); self._rx = float(v[1])
        self.update()

    def setMaxValue(self, mx): self._max_val = max(1, float(mx)); self.update()
    def setLabels(self, tx, rx): self._tx_label = str(tx); self._rx_label = str(rx); self.update()
    def setUnit(self, u): self._unit = str(u); self.update()

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        mid_y = h / 2

        # TX (上方，向右)
        tx_ratio = max(0, min(1, self._tx / self._max_val))
        tx_color = QColor("#4A90D9")
        p.setBrush(QColor("#1a2a3a")); p.setPen(Qt.NoPen)
        p.drawRoundedRect(QRectF(4, 4, w - 8, mid_y - 6), 4, 4)
        bar_w = (w - 12) * tx_ratio
        p.setBrush(tx_color)
        p.drawRoundedRect(QRectF(6, 6, bar_w, mid_y - 10), 3, 3)
        p.setPen(QColor("#fff")); p.setFont(QFont("Consolas", max(9, h // 7), QFont.Bold))
        p.drawText(QRectF(6, 4, w - 12, mid_y - 6), Qt.AlignVCenter | Qt.AlignRight,
                   f"{self._tx:.0f} {self._unit}")
        p.setPen(tx_color); p.setFont(QFont("Arial", max(8, h // 8), QFont.Bold))
        p.drawText(QRectF(6, 4, 40, mid_y - 6), Qt.AlignVCenter | Qt.AlignLeft, self._tx_label)

        # RX (下方，向左)
        rx_ratio = max(0, min(1, self._rx / self._max_val))
        rx_color = QColor("#27AE60")
        p.setBrush(QColor("#1a3a2a")); p.setPen(Qt.NoPen)
        p.drawRoundedRect(QRectF(4, mid_y + 2, w - 8, mid_y - 6), 4, 4)
        bar_w = (w - 12) * rx_ratio
        p.setBrush(rx_color)
        p.drawRoundedRect(QRectF(w - 6 - bar_w, mid_y + 4, bar_w, mid_y - 10), 3, 3)
        p.setPen(QColor("#fff")); p.setFont(QFont("Consolas", max(9, h // 7), QFont.Bold))
        p.drawText(QRectF(6, mid_y + 2, w - 12, mid_y - 6), Qt.AlignVCenter | Qt.AlignLeft,
                   f"{self._rx:.0f} {self._unit}")
        p.setPen(rx_color); p.setFont(QFont("Arial", max(8, h // 8), QFont.Bold))
        p.drawText(QRectF(w - 46, mid_y + 2, 40, mid_y - 6), Qt.AlignVCenter | Qt.AlignRight, self._rx_label)
        p.end()
    