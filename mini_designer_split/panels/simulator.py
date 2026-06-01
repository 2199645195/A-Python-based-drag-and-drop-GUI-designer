"""mini_designer_split/panels/simulator.py — 数据模拟器面板"""

import math, random

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QPushButton, QComboBox,
    QLineEdit, QGroupBox, QProgressBar, QSlider, QSpinBox,
    QDoubleSpinBox, QLCDNumber, QCheckBox, QRadioButton,
)
from PySide6.QtGui import QColor

from ..config import BINDABLE_WIDGETS


class DataSimulatorPanel(QWidget):
    """设计时数据模拟器 — 手动输入或自动波动tag值，实时驱动控件"""

    WAVE_MODES = ["手动", "正弦波", "随机游走", "锯齿波"]

    def __init__(self, canvas, parent=None):
        super().__init__(parent)
        self.canvas = canvas
        self.setMinimumWidth(200)
        self.setMaximumWidth(400)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.header = QLabel("<b>🔬 数据模拟器</b>")
        self.header.setStyleSheet(
            "padding:4px 8px; font-size:12px;"
            " background:#f0f0f0; border-bottom:1px solid #ddd;"
        )
        layout.addWidget(self.header)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Tag", "当前值", "模式", "参数"])
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.Stretch
        )
        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeToContents
        )
        self.table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeToContents
        )
        self.table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.Stretch
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet(
            "QTableWidget{font-size:11px; gridline-color:#eee;}"
            " QTableWidget::item{padding:2px;}"
        )
        layout.addWidget(self.table)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(4)
        self.btn_refresh = QPushButton("🔄 刷新")
        self.btn_start = QPushButton("▶ 开始模拟")
        self.btn_stop = QPushButton("⏹ 停止")
        self.btn_stop.setEnabled(False)
        for btn in [self.btn_refresh, self.btn_start, self.btn_stop]:
            btn.setStyleSheet("QPushButton{padding:4px 8px; font-size:11px;}")
            btn_row.addWidget(btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._sim_data = {}  # tag -> {mode, value, phase, min, max, period}
        self._elapsed = 0.0
        self._running = False

        self.btn_refresh.clicked.connect(self.refresh)
        self.btn_start.clicked.connect(self.start)
        self.btn_stop.clicked.connect(self.stop)
        self.table.cellChanged.connect(self._on_cell_changed)

    def refresh(self):
        self._sim_data.clear()
        self.table.setRowCount(0)
        self._busy = True

        def scan(widgets):
            for w in widgets:
                tag = w.property("_tag")
                if tag and (
                    isinstance(w, BINDABLE_WIDGETS) or hasattr(w, 'setValue')
                ):
                    if tag not in self._sim_data:
                        cur_val = 0.0
                        try:
                            if hasattr(w, "value") and callable(w.value):
                                cur_val = float(w.value())
                            elif hasattr(w, "text") and callable(w.text):
                                try:
                                    cur_val = float(w.text())
                                except ValueError:
                                    cur_val = 0.0
                        except Exception:
                            pass
                        self._sim_data[tag] = {
                            "mode": "手动", "value": cur_val,
                            "phase": random.random() * 6.28,
                            "min": 0.0, "max": 100.0, "period": 5.0,
                            "widget": w,
                        }
                if hasattr(w, "_content_layout"):
                    children = [
                        w._content_layout.itemAt(i).widget()
                        for i in range(w._content_layout.count())
                        if w._content_layout.itemAt(i)
                        and w._content_layout.itemAt(i).widget()
                    ]
                    scan(children)

        scan(self.canvas._canvas_widgets)

        row = 0
        for tag, sd in self._sim_data.items():
            self.table.insertRow(row)
            ki = QTableWidgetItem(tag)
            ki.setFlags(ki.flags() & ~Qt.ItemIsEditable)
            ki.setBackground(QColor("#f5f5f5"))
            self.table.setItem(row, 0, ki)
            vi = QTableWidgetItem(str(sd["value"])[:8])
            self.table.setItem(row, 1, vi)
            combo = QComboBox()
            combo.addItems(self.WAVE_MODES)
            combo.setCurrentText(sd["mode"])
            combo.currentTextChanged.connect(
                lambda text, r=row, t=tag: self._on_mode_changed(t, text)
            )
            self.table.setCellWidget(row, 2, combo)
            param_text = (
                f"min={sd['min']:.0f} max={sd['max']:.0f} T={sd['period']:.1f}s"
            )
            pi = QTableWidgetItem(param_text)
            pi.setToolTip("格式: min=最小值 max=最大值 T=周期(秒)")
            self.table.setItem(row, 3, pi)
            row += 1

        self._busy = False

    def _on_mode_changed(self, tag, mode):
        if tag in self._sim_data:
            self._sim_data[tag]["mode"] = mode

    def _on_cell_changed(self, row, col):
        if self._busy or col != 3:
            return
        tag_item = self.table.item(row, 0)
        param_item = self.table.item(row, 1)
        if not tag_item:
            return
        tag = tag_item.text()
        if tag not in self._sim_data:
            return
        if col == 1 and param_item:
            try:
                self._sim_data[tag]["value"] = float(param_item.text())
            except ValueError:
                pass
            return
        param_text = (
            self.table.item(row, 3).text() if self.table.item(row, 3) else ""
        )
        for part in param_text.split():
            if "=" in part:
                k, v = part.split("=", 1)
                try:
                    if k == "min":
                        self._sim_data[tag]["min"] = float(v)
                    elif k == "max":
                        self._sim_data[tag]["max"] = float(v)
                    elif k in ("T", "t", "period"):
                        self._sim_data[tag]["period"] = float(v)
                except ValueError:
                    pass

    def start(self):
        self._running = True
        self._elapsed = 0.0
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self._timer.start(100)

    def stop(self):
        self._running = False
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self._timer.stop()

    def _tick(self):
        if not self._running:
            return
        self._elapsed += 0.1
        for tag, sd in self._sim_data.items():
            mode = sd["mode"]
            if mode == "手动":
                continue
            elif mode == "正弦波":
                freq = 1.0 / max(0.1, sd["period"])
                amplitude = (sd["max"] - sd["min"]) / 2.0
                center = (sd["max"] + sd["min"]) / 2.0
                sd["value"] = (
                    center
                    + amplitude * math.sin(
                        2 * math.pi * freq * self._elapsed + sd["phase"]
                    )
                )
            elif mode == "随机游走":
                step = (sd["max"] - sd["min"]) * 0.02 * random.uniform(-1, 1)
                sd["value"] = max(
                    sd["min"], min(sd["max"], sd["value"] + step)
                )
            elif mode == "锯齿波":
                period = max(0.1, sd["period"])
                sd["value"] = sd["min"] + (sd["max"] - sd["min"]) * (
                    (self._elapsed % period) / period
                )
            self._apply_value(tag, sd["value"])

        self._busy = True
        for row in range(self.table.rowCount()):
            tag_item = self.table.item(row, 0)
            if not tag_item:
                continue
            tag = tag_item.text()
            if tag in self._sim_data and self._sim_data[tag]["mode"] != "手动":
                val_str = f"{self._sim_data[tag]['value']:.2f}"
                vi = self.table.item(row, 1)
                if vi:
                    vi.setText(val_str)
        self._busy = False

    def _apply_value(self, tag, value):
        sd = self._sim_data.get(tag)
        if not sd:
            return
        w = sd.get("widget")
        if not w or not w.isVisible():
            return
        try:
            if isinstance(w, (QLabel, QLineEdit, QGroupBox)):
                w.setText(f"{value:.1f}")
            elif isinstance(w, (QProgressBar, QSlider)):
                w.setValue(int(value))
            elif isinstance(w, (QSpinBox, QDoubleSpinBox)):
                w.setValue(value)
            elif isinstance(w, QLCDNumber):
                w.display(value)
            elif isinstance(w, (QCheckBox, QRadioButton)):
                w.setChecked(value > (sd["max"] + sd["min"]) / 2.0)
            elif hasattr(w, 'addValue') and callable(getattr(w, 'addValue', None)):
                w.addValue(0, value)
        except Exception:
            pass
