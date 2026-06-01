import math, time
from collections import deque
from PySide6.QtCore import Qt, Signal, QRect, QRectF, QPoint, QSize, QTimer
from PySide6.QtGui import (
    QPainter, QPen, QColor, QFont, QFontMetrics, QImage, QPixmap, QBrush,
)
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy


class CameraWidget(QWidget):
    """工业相机实时画面控件 — 支持外部推帧/SDK回调/设计时占位预览"""
    _display_name = "📷 工业相机"

    frame_updated = Signal(object)  # 发射原始帧数据供下游算法处理

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap = None
        self._status_text = "📷 相机未连接"
        self._fps_counter = 0
        self._last_fps_time = time.time()
        self._current_fps = 0.0
        self._source_label = ""

        # 设计时演示定时器（运行时由外部调用 updateFrame 替代）
        self._demo_timer = QTimer(self)
        self._demo_timer.setInterval(33)  # ~30fps
        self._demo_timer.timeout.connect(self._demo_tick)
        self._demo_phase = 0.0

        self.setMinimumSize(160, 120)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    # ── 公共接口（与 DataBinder / SDK 对接）──────────────────

    def setValue(self, v):
        """兼容 DataBinder 通用绑定：传入路径字符串或 numpy array"""
        if isinstance(v, str):
            self.load_image(v)
        elif hasattr(v, 'shape'):  # numpy ndarray
            self.updateFrame(v)

    def updateFrame(self, frame):
        """
        外部主动推送帧（SDK回调/采集线程安全调用）
        支持: numpy.ndarray (BGR/RGB), QImage, QPixmap
        """
        try:
            if hasattr(frame, 'shape'):  # numpy array
                h, w = frame.shape[:2]
                ch = frame.shape[2] if len(frame.shape) == 3 else 1
                if ch == 3:
                    # 假设 BGR → RGB
                    rgb = frame[:, :, ::-1].copy()
                    qimg = QImage(rgb.data, w, h, w * 3, QImage.Format_RGB888).copy()
                else:
                    qimg = QImage(frame.data, w, h, w, QImage.Format_Grayscale8).copy()
                self._pixmap = QPixmap.fromImage(qimg)
            elif isinstance(frame, QImage):
                self._pixmap = QPixmap.fromImage(frame)
            elif isinstance(frame, QPixmap):
                self._pixmap = frame
            else:
                return

            self._status_text = ""
            self._calc_fps()
            self.frame_updated.emit(frame)
            self.update()
        except Exception as e:
            self._status_text = f"❌ 帧解析失败: {e}"
            self.update()

    def load_image(self, path: str):
        """从文件加载静态图片"""
        pm = QPixmap(path)
        if pm.isNull():
            self._status_text = f"❌ 无法加载: {path}"
            self._pixmap = None
        else:
            self._pixmap = pm
            self._status_text = ""
            self._source_label = path.split("/")[-1].split("\\")[-1]
        self.update()

    def start(self, source="", fps=30):
        """
        启动相机（预留SDK接口）
        实际项目中替换为 SDK 初始化 + 回调 → updateFrame()
        设计时自动进入演示模式
        """
        self._source_label = str(source) if source else "Demo"
        self._demo_timer.start(int(1000 / max(1, fps)))
        self._status_text = ""
        self.update()

    def stop(self):
        """停止采集/演示"""
        self._demo_timer.stop()
        self._status_text = "⏹ 已停止"
        self.update()

    # ── 内部方法 ──────────────────────────────────────────────

    def _calc_fps(self):
        self._fps_counter += 1
        now = time.time()
        elapsed = now - self._last_fps_time
        if elapsed >= 1.0:
            self._current_fps = self._fps_counter / elapsed
            self._fps_counter = 0
            self._last_fps_time = now

    def _demo_tick(self):
        """设计时/演示模式：生成渐变测试图案"""
        self._demo_phase += 0.05
        w, h = max(self.width(), 160), max(self.height(), 120)
        img = QImage(w, h, QImage.Format_RGB888)
        r = int(127 + 127 * math.sin(self._demo_phase))
        g = int(127 + 127 * math.sin(self._demo_phase + 2.094))
        b = int(127 + 127 * math.sin(self._demo_phase + 4.189))
        img.fill(QColor(r, g, b))

        # 绘制时间戳模拟OSD
        p = QPainter(img)
        p.setPen(QColor(255, 255, 255, 200))
        p.setFont(QFont("Consolas", 14, QFont.Bold))
        ts = time.strftime("%H:%M:%S")
        p.drawText(10, 24, f"CAM-01 | {ts} | {self._current_fps:.1f} FPS")
        p.end()

        self._pixmap = QPixmap.fromImage(img)
        self._calc_fps()
        self.update()

    # ── 绘制 ──────────────────────────────────────────────────

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        w, h = self.width(), self.height()

        # 背景
        p.fillRect(0, 0, w, h, QColor("#1e1e1e"))

        if self._pixmap and not self._pixmap.isNull():
            # 等比缩放适配
            scaled = self._pixmap.scaled(
                w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            x = (w - scaled.width()) // 2
            y = (h - scaled.height()) // 2
            p.drawPixmap(x, y, scaled)

            # OSD: FPS + 来源
            p.setPen(QColor(0, 255, 0, 180))
            p.setFont(QFont("Consolas", 9))
            osd = f"{self._current_fps:.1f} FPS"
            if self._source_label:
                osd += f" | {self._source_label}"
            p.drawText(6, h - 6, osd)
        else:
            # 无画面时显示状态文字
            p.setPen(QColor("#888"))
            p.setFont(QFont("Microsoft YaHei", 12))
            p.drawText(QRectF(0, 0, w, h), Qt.AlignCenter, self._status_text)

            # 绘制边框提示
            pen = QPen(QColor("#333"), 1, Qt.DashLine)
            p.setPen(pen)
            p.drawRect(0, 0, w - 1, h - 1)

        p.end()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update()

    def sizeHint(self):
        return QSize(320, 240)

    def minimumSizeHint(self):
        return QSize(160, 120)