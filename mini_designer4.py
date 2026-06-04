#!/usr/bin/env python3
# coding: utf-8
"""
mini_designer.py — 工业GUI设计器 (控件树拖拽/撤销重做/批量移动/预览/图表/仪表/数据模拟)
新增P16: 撤销重做工具栏按钮 | P17: 控件树拖拽改变父子关系 | P18: 多选批量移动
保留: P15数据模拟 | P14实时曲线 | P13仪表盘 | P11预览模式 | P10控件树 | P12信号槽/栅格 | P7工业模板 | P5数据绑定
"""
import sys, os, re, json, math, random, importlib.util, base64
from collections import defaultdict, deque
from abc import ABC, abstractmethod
import time

def _setup_pyside6():
    if os.name != "nt": return
    os.environ["QT_OPENGL"] = "software"
    import importlib.util as _ilu, site
    pyside_root = shiboken_root = None
    seen = set()
    for mod in ("PySide6", "shiboken6"):
        spec = _ilu.find_spec(mod)
        if spec and spec.origin:
            root = os.path.abspath(os.path.dirname(spec.origin))
            if mod == "PySide6": pyside_root = root
            else: shiboken_root = root
    for base in site.getsitepackages():
        for pkg in ("PySide6", "shiboken6"):
            d = os.path.join(base, pkg)
            if d not in seen and os.path.isdir(d):
                seen.add(d)
                if pkg == "PySide6" and not pyside_root: pyside_root = d
                if pkg == "shiboken6" and not shiboken_root: shiboken_root = d
    for d in (pyside_root, shiboken_root):
        if d and os.path.isdir(d):
            try: os.add_dll_directory(d)
            except OSError: pass
    if pyside_root:
        plugins = os.path.join(pyside_root, "plugins")
        os.environ["QT_PLUGIN_PATH"] = plugins
        os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = os.path.join(plugins, "platforms")

_setup_pyside6()

from PySide6.QtCore import Qt, QMimeData, QEvent, Signal, QRect, QPoint, QSize, QTimer, QSettings, QRectF, QPointF
from PySide6.QtGui import QDrag, QColor, QFont, QPainter, QPen, QKeySequence, QShortcut, QBrush, QFontMetrics, QPixmap, QPainterPath
from PySide6.QtCore import qInstallMessageHandler
qInstallMessageHandler(lambda mode, ctx, msg: None)

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QListWidget, QListWidgetItem, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QTextEdit, QPushButton, QLabel, QLineEdit, QComboBox,
    QGroupBox, QFrame, QStyleFactory, QMessageBox, QCheckBox, QRadioButton,
    QSpinBox, QDoubleSpinBox, QSlider, QProgressBar, QTextEdit as QWTextEdit,
    QDateEdit, QTimeEdit, QTabWidget, QScrollArea, QToolButton, QSizePolicy,
    QFileDialog, QDialogButtonBox, QCalendarWidget, QDial, QLCDNumber,
    QCommandLinkButton, QTextBrowser, QStackedWidget, QTreeWidget, QTreeWidgetItem, QMenu,
    QToolBar, QDialog, QPlainTextEdit, QInputDialog, QTabBar ,QFormLayout, QColorDialog 
)

# ── 全局配置 ─────────────────────────────────────────────────────
DEFAULT_QSS = """
QMainWindow { background: #fafafa; }
QWidget { font-family: "Microsoft YaHei", "Segoe UI", sans-serif; font-size: 13px; color: #333; }
QPushButton, QToolButton, QCommandLinkButton { background: #fff; border: 1px solid #d0d0d0; padding: 6px 16px; border-radius: 6px; }
QPushButton:hover, QToolButton:hover, QCommandLinkButton:hover { background: #e8f0fe; border-color: #4A90D9; }
QPushButton:pressed, QToolButton:pressed { background: #d0e4f7; }
QListWidget, QTableWidget, QTextEdit, QWTextEdit, QTextBrowser, QTreeWidget { background: #fff; border: 1px solid #e0e0e0; border-radius: 4px; outline: none; }
QHeaderView::section { background: #f5f5f5; border: 1px solid #e0e0e0; padding: 4px; font-weight: bold; }
QGroupBox { border: 1px solid #e0e0e0; margin-top: 10px; padding-top: 14px; border-radius: 6px; }
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; color: #666; }
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit, QTimeEdit { background: #fff; border: 1px solid #d0d0d0; padding: 5px 8px; border-radius: 4px; }
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus, QTimeEdit:focus { border-color: #4A90D9; }
QProgressBar { border: 1px solid #d0d0d0; background: #f5f5f5; text-align: center; border-radius: 4px; min-height: 20px; }
QProgressBar::chunk { background: #4A90D9; border-radius: 3px; }
QSlider::groove:horizontal { height: 6px; background: #e0e0e0; border-radius: 3px; }
QSlider::handle:horizontal { width: 16px; height: 16px; margin: -5px 0; background: #4A90D9; border-radius: 8px; }
QSlider::sub-page:horizontal { background: #4A90D9; border-radius: 3px; }
QCheckBox, QRadioButton { spacing: 6px; }
QCheckBox::indicator, QRadioButton::indicator { width: 16px; height: 16px; }
QTabWidget::pane { border: 1px solid #e0e0e0; background: #fff; border-radius: 4px; }
QTabBar::tab { background: #f5f5f5; padding: 6px 16px; border: 1px solid #e0e0e0; margin-right: 2px; }
QTabBar::tab:selected { background: #4A90D9; color: white; }
QCalendarWidget { background: #fff; border: 1px solid #e0e0e0; }
QLCDNumber { background: #f5f5f5; border: 1px solid #e0e0e0; border-radius: 4px; }
QDial { background: transparent; }
QDialogButtonBox QPushButton { min-width: 80px; }
QScrollArea { border: none; }
QFrame[frameShape="4"], QFrame[frameShape="5"] { color: #d0d0d0; max-height: 2px; }
QSplitter::handle { background: #e0e0e0; }
QSplitter::handle:horizontal { width: 3px; }
QSplitter::handle:vertical { height: 3px; }
QListWidget::item:selected, QTreeWidget::item:selected, QTableWidget::item:selected { background: #4A90D9; color: white; }
QPushButton[role="primary"], QToolButton[role="primary"], QCommandLinkButton[role="primary"] { background: #4A90D9; color: white; border: none; }
QPushButton[role="primary"]:hover, QToolButton[role="primary"]:hover, QCommandLinkButton[role="primary"]:hover { background: #357ABD; }
QPushButton[role="danger"], QToolButton[role="danger"], QCommandLinkButton[role="danger"] { background: #E74C3C; color: white; border: none; }
QPushButton[role="danger"]:hover, QToolButton[role="danger"]:hover, QCommandLinkButton[role="danger"]:hover { background: #C0392B; }
QPushButton[role="success"], QToolButton[role="success"] { background: #27AE60; color: white; border: none; }
QPushButton[role="success"]:hover, QToolButton[role="success"]:hover { background: #219A52; }
QPushButton[role="warning"], QToolButton[role="warning"] { background: #F39C12; color: white; border: none; }
QPushButton[role="warning"]:hover, QToolButton[role="warning"]:hover { background: #D68910; }
QPushButton[role="outline"], QToolButton[role="outline"] { background: transparent; border: 1px solid #4A90D9; color: #4A90D9; }
QPushButton[role="outline"]:hover, QToolButton[role="outline"]:hover { background: rgba(74,144,217,0.1); }
QPushButton[role="ghost"], QToolButton[role="ghost"] { background: transparent; border: none; color: #666; }
QPushButton[role="ghost"]:hover, QToolButton[role="ghost"]:hover { background: #f0f0f0; color: #333; }
QLineEdit[role="error"], QComboBox[role="error"], QSpinBox[role="error"], QDoubleSpinBox[role="error"], QDateEdit[role="error"], QTimeEdit[role="error"] { border-color: #E74C3C; background: #fff5f5; }
QLineEdit[role="success"], QComboBox[role="success"] { border-color: #27AE60; background: #f0fff4; }
QLineEdit[role="readonly"] { background: #f5f5f5; color: #888; }
QProgressBar[role="success"]::chunk { background: #27AE60; }
QProgressBar[role="warning"]::chunk { background: #F39C12; }
QProgressBar[role="danger"]::chunk { background: #E74C3C; }
QSlider[role="success"]::handle:horizontal, QSlider[role="success"]::sub-page:horizontal { background: #27AE60; }
QSlider[role="warning"]::handle:horizontal, QSlider[role="warning"]::sub-page:horizontal { background: #F39C12; }
QSlider[role="danger"]::handle:horizontal, QSlider[role="danger"]::sub-page:horizontal { background: #E74C3C; }
QGroupBox[role="highlight"] { border-color: #4A90D9; }
QGroupBox[role="highlight"]::title { color: #4A90D9; font-weight: bold; }
QGroupBox[role="danger"] { border-color: #E74C3C; }
QGroupBox[role="danger"]::title { color: #E74C3C; }
QLabel[role="h1"] { font-size: 24px; font-weight: bold; color: #111; }
QLabel[role="h2"] { font-size: 18px; font-weight: bold; color: #222; }
QLabel[role="h3"] { font-size: 15px; font-weight: bold; color: #333; }
QLabel[role="subtitle"] { font-size: 13px; color: #666; }
QLabel[role="caption"] { font-size: 11px; color: #999; }
QLabel[role="danger"] { color: #E74C3C; }
QLabel[role="success"] { color: #27AE60; }
QLabel[role="warning"] { color: #F39C12; }
QLCDNumber[role="success"] { color: #27AE60; }
QLCDNumber[role="danger"] { color: #E74C3C; }
QLCDNumber[role="warning"] { color: #F39C12; }
QListWidget[role="borderless"], QTreeWidget[role="borderless"], QTableWidget[role="borderless"] { border: none; background: transparent; }
QListWidget[role="highlight"]::item:selected, QTreeWidget[role="highlight"]::item:selected { background: #E74C3C; }
QTreeWidget[role="compact"]::item { padding: 2px 0; min-height: 22px; }
QTableWidget[role="striped"]::item:nth-child(even) { background: #f9f9f9; }
QSplitter[role="thin"]::handle:horizontal { width: 1px; background: #e0e0e0; }
QSplitter[role="thin"]::handle:vertical { height: 1px; background: #e0e0e0; }
QSplitter[role="thick"]::handle:horizontal { width: 6px; background: #d0d0d0; }
QSplitter[role="thick"]::handle:vertical { height: 6px; background: #d0d0d0; }
QToolBar { border-bottom: 1px solid #e0e0e0; padding: 2px; }
QToolBar QToolButton { padding: 4px 8px; margin: 1px; }
"""

ACTIVE_QSS = DEFAULT_QSS
DARK_MODE = False

DARK_QSS = """
QMainWindow { background: #1e1e2e; }
QWidget { font-family: "Microsoft YaHei", "Segoe UI", sans-serif; font-size: 13px; color: #cdd6f4; }
QPushButton, QToolButton, QCommandLinkButton { background: #313244; border: 1px solid #45475a; padding: 6px 16px; border-radius: 6px; color: #cdd6f4; }
QPushButton:hover, QToolButton:hover, QCommandLinkButton:hover { background: #45475a; border-color: #89b4fa; }
QPushButton:pressed, QToolButton:pressed { background: #585b70; }
QListWidget, QTableWidget, QTextEdit, QWTextEdit, QTextBrowser, QTreeWidget { background: #313244; border: 1px solid #45475a; border-radius: 4px; outline: none; color: #cdd6f4; }
QHeaderView::section { background: #45475a; border: 1px solid #585b70; padding: 4px; font-weight: bold; color: #cdd6f4; }
QGroupBox { border: 1px solid #45475a; margin-top: 10px; padding-top: 14px; border-radius: 6px; color: #cdd6f4; }
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; color: #a6adc8; }
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit, QTimeEdit { background: #313244; border: 1px solid #45475a; padding: 5px 8px; border-radius: 4px; color: #cdd6f4; }
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus, QTimeEdit:focus { border-color: #89b4fa; }
QProgressBar { border: 1px solid #45475a; background: #1e1e2e; text-align: center; border-radius: 4px; min-height: 20px; color: #cdd6f4; }
QProgressBar::chunk { background: #89b4fa; border-radius: 3px; }
QSlider::groove:horizontal { height: 6px; background: #45475a; border-radius: 3px; }
QSlider::handle:horizontal { width: 16px; height: 16px; margin: -5px 0; background: #89b4fa; border-radius: 8px; }
QSlider::sub-page:horizontal { background: #89b4fa; border-radius: 3px; }
QCheckBox, QRadioButton { spacing: 6px; color: #cdd6f4; }
QCheckBox::indicator, QRadioButton::indicator { width: 16px; height: 16px; }
QTabWidget::pane { border: 1px solid #45475a; background: #313244; border-radius: 4px; }
QTabBar::tab { background: #313244; padding: 6px 16px; border: 1px solid #45475a; margin-right: 2px; color: #a6adc8; }
QTabBar::tab:selected { background: #89b4fa; color: #1e1e2e; }
QCalendarWidget { background: #313244; border: 1px solid #45475a; color: #cdd6f4; }
QLCDNumber { background: #1e1e2e; border: 1px solid #45475a; border-radius: 4px; color: #89b4fa; }
QDial { background: transparent; }
QScrollArea { border: none; }
QFrame[frameShape="4"], QFrame[frameShape="5"] { color: #45475a; max-height: 2px; }
QSplitter::handle { background: #45475a; }
QSplitter::handle:horizontal { width: 3px; }
QSplitter::handle:vertical { height: 3px; }
QListWidget::item:selected, QTreeWidget::item:selected, QTableWidget::item:selected { background: #89b4fa; color: #1e1e2e; }
QGroupBox[role="highlight"] { border-color: #89b4fa; }
QGroupBox[role="highlight"]::title { color: #89b4fa; font-weight: bold; }
QGroupBox[role="danger"] { border-color: #f38ba8; }
QGroupBox[role="danger"]::title { color: #f38ba8; }
QLabel[role="h1"] { font-size: 24px; font-weight: bold; color: #cdd6f4; }
QLabel[role="h2"] { font-size: 18px; font-weight: bold; color: #cdd6f4; }
QLabel[role="h3"] { font-size: 15px; font-weight: bold; color: #cdd6f4; }
QLabel[role="subtitle"] { font-size: 13px; color: #a6adc8; }
QLabel[role="caption"] { font-size: 11px; color: #6c7086; }
QLabel[role="danger"] { color: #f38ba8; }
QLabel[role="success"] { color: #a6e3a1; }
QLabel[role="warning"] { color: #fab387; }
QLCDNumber[role="success"] { color: #a6e3a1; }
QLCDNumber[role="danger"] { color: #f38ba8; }
QLCDNumber[role="warning"] { color: #fab387; }
QListWidget[role="borderless"], QTreeWidget[role="borderless"], QTableWidget[role="borderless"] { border: none; background: transparent; }
QToolBar { border-bottom: 1px solid #45475a; padding: 2px; background: #1e1e2e; }
QToolBar QToolButton { padding: 4px 8px; margin: 1px; color: #cdd6f4; }
QMenu { background: #313244; border: 1px solid #45475a; color: #cdd6f4; }
QMenu::item:selected { background: #89b4fa; color: #1e1e2e; }
QStatusBar { font-size: 11px; color: #a6adc8; border-top: 1px solid #45475a; background: #181825; }
QToolTip { background: #313244; color: #cdd6f4; border: 1px solid #45475a; }
"""

WIDGET_ROLES = {
    "QPushButton": ["default","primary","success","warning","danger","outline","ghost"],
    "QToolButton": ["default","primary","success","warning","danger","outline","ghost"],
    "QCommandLinkButton": ["default","primary","danger"],
    "QLineEdit": ["default","error","success","readonly"],
    "QComboBox": ["default","error","success"],
    "QSpinBox": ["default","error"], "QDoubleSpinBox": ["default","error"],
    "QDateEdit": ["default","error"], "QTimeEdit": ["default","error"],
    "QProgressBar": ["default","success","warning","danger"],
    "QSlider": ["default","success","warning","danger"],
    "QGroupBox": ["default","highlight","danger"],
    "QLabel": ["default","h1","h2","h3","subtitle","caption","danger","success","warning"],
    "QLCDNumber": ["default","success","warning","danger"],
    "QListWidget": ["default","borderless","highlight"],
    "QTreeWidget": ["default","borderless","compact"],
    "QTableWidget": ["default","borderless","striped"],
    "QSplitter": ["default","thin","thick"],
}

BINDABLE_WIDGETS = (QLabel, QLineEdit, QLCDNumber, QProgressBar, QSlider, QSpinBox, QDoubleSpinBox, QCheckBox, QRadioButton, QGroupBox)

WIDGET_SIGNALS = {
    "QPushButton": ["clicked()", "pressed()", "released()", "toggled(bool)"],
    "QToolButton": ["clicked()", "pressed()", "released()", "toggled(bool)"],
    "QCheckBox": ["stateChanged(int)", "toggled(bool)", "clicked()"],
    "QRadioButton": ["toggled(bool)", "clicked()"],
    "QComboBox": ["currentIndexChanged(int)", "currentTextChanged(str)", "activated(int)"],
    "QLineEdit": ["textChanged(str)", "editingFinished()", "returnPressed()"],
    "QSpinBox": ["valueChanged(int)", "valueChanged(str)"],
    "QDoubleSpinBox": ["valueChanged(double)", "valueChanged(str)"],
    "QSlider": ["valueChanged(int)", "sliderMoved(int)", "sliderReleased()"],
    "QProgressBar": ["valueChanged(int)"],
    "QTabWidget": ["currentChanged(int)", "tabCloseRequested(int)"],
    "QListWidget": ["currentRowChanged(int)", "itemClicked(QListWidgetItem*)", "itemDoubleClicked(QListWidgetItem*)"],
    "QTreeWidget": ["currentItemChanged(QTreeWidgetItem*,QTreeWidgetItem*)", "itemClicked(QTreeWidgetItem*,int)"],
    "QTableWidget": ["cellClicked(int,int)", "cellDoubleClicked(int,int)", "currentCellChanged(int,int,int,int)"],
    "QDial": ["valueChanged(int)", "sliderMoved(int)"],
    "QLCDNumber": ["overflow()"],
    "QCommandLinkButton": ["clicked()", "pressed()", "released()"],
    "QDateEdit": ["dateChanged(QDate)", "dateTimeChanged(QDateTime)"],
    "QTimeEdit": ["timeChanged(QTime)", "dateTimeChanged(QDateTime)"],
}

MIME_TYPE = "application/x-designer-widget-v19"
HANDLE_SIZE, HANDLE_HALF, MIN_W, MIN_H = 8, 4, 30, 24
HANDLE_CURSORS = {"tl":Qt.SizeFDiagCursor,"tc":Qt.SizeVerCursor,"tr":Qt.SizeBDiagCursor,"ml":Qt.SizeHorCursor,"mr":Qt.SizeHorCursor,"bl":Qt.SizeBDiagCursor,"bc":Qt.SizeVerCursor,"br":Qt.SizeFDiagCursor}
VIEWPORT_WIDGETS = (QTableWidget, QTreeWidget, QListWidget, QTextEdit, QWTextEdit, QTextBrowser)
SNAP_THRESHOLD = 5
ARROW_STEP = 1
DESIGN_WIDTH = 800
DESIGN_HEIGHT = 600
GRID_SIZE = 10

SIZE_POLICY_MAP = {
    "Preferred": QSizePolicy.Preferred, "Fixed": QSizePolicy.Fixed,
    "Minimum": QSizePolicy.Minimum, "Maximum": QSizePolicy.Maximum,
    "Expanding": QSizePolicy.Expanding, "MinimumExpanding": QSizePolicy.MinimumExpanding,
    "Ignored": QSizePolicy.Ignored,
}
SIZE_POLICY_NAMES = list(SIZE_POLICY_MAP.keys())

def _policy_to_str(policy):
    for name, val in SIZE_POLICY_MAP.items():
        if policy == val: return name
    return "Preferred"

BUILTIN_CATEGORIES = [
    ("按钮类", [("按钮",QPushButton,{"text":"按钮"}),("工具按钮",QToolButton,{"text":"工具"}),("命令链接按钮",QCommandLinkButton,{"text":"命令链接"}),("对话框按钮组",QDialogButtonBox,{}),("复选框",QCheckBox,{"text":"复选框"}),("单选按钮",QRadioButton,{"text":"单选按钮"})]),
    ("文本与标签", [("标签",QLabel,{"text":"标签文本"}),("链接标签",QLabel,{"text":"<a href='#'>链接文本</a>","openExternalLinks":True}),("单行输入框",QLineEdit,{"placeholderText":"请输入..."}),("多行文本框",QWTextEdit,{"placeholderText":"多行文本..."}),("只读文本浏览器",QTextBrowser,{})]),
    ("选择器", [("下拉框",QComboBox,{"items":["选项1","选项2","选项3"]}),("整数微调框",QSpinBox,{"range":(0,999),"value":0}),("浮点微调框",QDoubleSpinBox,{"range":(0.0,99.9),"decimals":2}),("日期选择器",QDateEdit,{}),("时间选择器",QTimeEdit,{}),("日历控件",QCalendarWidget,{}),("列表控件",QListWidget,{}),("树形控件",QTreeWidget,{}),("表格控件",QTableWidget,{})]),
    ("数值与进度", [("滑块",QSlider,{"orientation":Qt.Horizontal}),("进度条",QProgressBar,{"value":45}),("旋钮",QDial,{}),("液晶数字显示",QLCDNumber,{})]),
    ("容器与布局", [("分组框",QGroupBox,{"title":"分组标题"}),("标签页容器",QTabWidget,{}),("堆叠容器",QStackedWidget,{}),("滚动区域",QScrollArea,{}),("分割面板",QSplitter,{"orientation":Qt.Horizontal}),("垂直布局容器",None,{"layout":"vbox"}),("水平布局容器",None,{"layout":"hbox"})]),
    ("框架与分隔", [("框架",QFrame,{"frameShape":QFrame.StyledPanel}),("水平分隔线",QFrame,{"frameShape":QFrame.HLine}),("垂直分隔线",QFrame,{"frameShape":QFrame.VLine})]),
]

# ══════════════════════════════════════════════════════════════
# P20: 工业级多通道趋势曲线 (内置版 + X轴时间 + 属性全控)
# ══════════════════════════════════════════════════════════════
# P20: 工业级多通道趋势曲线 (内置版 + X轴时间 + 属性全控)
# 【最终修复版】解决了缩放导致的绘制偏移和滚动不刷新问题
class MultiTrendWidget(QWidget):
    """工业级多通道实时趋势曲线"""
    _display_name = "多通道趋势曲线"
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_OpaquePaintEvent, True)
        self.setAttribute(Qt.WA_NoSystemBackground, False)
        self.setMinimumSize(200, 150)
        
        # ── 数据存储 ──
        self._channels = [
            {"name": "温度", "color": QColor("#4A90D9"), "data": deque(maxlen=600)},
            {"name": "压力", "color": QColor("#E74C3C"), "data": deque(maxlen=600)},
        ]
        
        # ── 属性初始化 ──
        self._x_range = 60          # 屏幕上显示的帧数（数据点数）
        self._y_min = 0.0
        self._y_max = 100.0
        self._auto_scale_y = False
        self._grid_density_x = 6
        self._grid_density_y = 5
        
        # ── 外观配色 ──
        self._bg_color = QColor("#1a1a2e")
        self._grid_color = QColor("#333355")
        self._text_color = QColor("#aaaacc")
        self._border_color = QColor("#444466")
        
        # ── 运行状态 ──
        self._running = False
        self._demo_timer = QTimer(self)
        self._demo_timer.timeout.connect(self._demo_tick)
        self._demo_phase = 0.0
        # 用于 X 轴滚动时间显示
        self._tick_count = 0
        
    # ── 公开API ──
    def addValue(self, channel_index, value):
        if 0 <= channel_index < len(self._channels):
            self._channels[channel_index]["data"].append(float(value))
            if self.isVisible():
                self.update()

    def start(self):
        """启动实时模拟"""
        if not self._running:
            self._running = True
            if not self._demo_timer.isActive():
                self._demo_timer.start(50)  # 20 FPS

    def stop(self):
        """停止实时模拟"""
        if self._running:
            self._running = False
            self._demo_timer.stop()

    def _demo_tick(self):
        """定时器回调：生成模拟数据并推进时间轴"""
        if not self.isVisible():
            return
        self._demo_phase += 0.05
        self._tick_count += 1
        for i in range(min(2, len(self._channels))):
            val = 50 + 30 * math.sin(self._demo_phase + i * 1.5) + random.uniform(-2, 2)
            self.addValue(i, val)

    # ── 属性Setter (供属性面板调用) ──
    def set_x_range(self, v):
        try: self._x_range = max(10, int(v)); self.update()
        except: pass
    def set_y_min(self, v):
        try: self._y_min = float(v); self._auto_scale_y = False; self.update()
        except: pass
    def set_y_max(self, v):
        try: self._y_max = float(v); self._auto_scale_y = False; self.update()
        except: pass
    def set_auto_scale_y(self, v):
        self._auto_scale_y = bool(v); self.update()
    def set_grid_density_x(self, v):
        try: self._grid_density_x = max(2, min(20, int(v))); self.update()
        except: pass
    def set_grid_density_y(self, v):
        try: self._grid_density_y = max(2, min(20, int(v))); self.update()
        except: pass
    def set_bg_color(self, c):
        try: self._bg_color = QColor(c); self.update()
        except: pass
    def set_grid_color(self, c):
        try: self._grid_color = QColor(c); self.update()
        except: pass
    def set_text_color(self, c):
        try: self._text_color = QColor(c); self.update()
        except: pass

    # ── 核心绘制 ──
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.TextAntialiasing, True)
        
        # 保存并重置变换矩阵，防止受 DesignerCanvas 的 scale() 影响
        p.save()
        p.resetTransform()
        
        w, h = self.width(), self.height()
        if w < 10 or h < 10:
            p.restore()
            return

        ml, mr, mt, mb = 50, 15, 20, 35
        pw, ph = w - ml - mr, h - mt - mb

        # 背景
        p.fillRect(self.rect(), self._bg_color)

        # 计算 Y 轴范围
        y_min, y_max = self._y_min, self._y_max
        if self._auto_scale_y and self._channels:
            all_vals = [v for ch in self._channels for v in ch["data"]]
            if all_vals:
                y_min, y_max = min(all_vals), max(all_vals)
                pad = (y_max - y_min) * 0.1 or 5.0
                y_min -= pad; y_max += pad

        y_range = y_max - y_min if y_max != y_min else 1.0

        # 绘制网格
        p.setPen(QPen(self._grid_color, 1, Qt.DotLine))
        for i in range(self._grid_density_y + 1):
            gy = mt + ph * i / self._grid_density_y
            p.drawLine(ml, int(gy), ml + pw, int(gy))
        for i in range(self._grid_density_x + 1):
            gx = ml + pw * i / self._grid_density_x
            p.drawLine(int(gx), mt, int(gx), mt + ph)

        # 绘制边框
        p.setPen(QPen(self._border_color, 1.5))
        p.drawRect(ml, mt, int(pw), int(ph))

        # 裁剪区域，防止曲线画出边界
        p.setClipRect(ml, mt, int(pw), int(ph))

        # ── 【核心修复】滚动曲线绘制 ──
        # 固定每个数据点在 X 轴上占的像素，不随数据量变化
        # 这样新数据从右侧进入，旧数据向左推出，实现真正的滚动效果
        visible_chs = [ch for ch in self._channels if ch["data"]]
        for ch in visible_chs:
            data = list(ch["data"])
            n = len(data)
            if n < 2:
                continue

            # 固定步长：始终用 _x_range 等分绘图宽度
            step_x = pw / max(1, self._x_range - 1)

            # 只取最新的 _x_range 个点（数据不足时取全部）
            visible_n = min(n, self._x_range)
            visible_data = data[-visible_n:]

            # 数据不足时左侧空白，最新点始终在最右侧
            # visible_data 已经是 data[-visible_n:]，即最新的 visible_n 个点
            # 第 0 个点画在最左，最新的第 visible_n-1 个点画在最右

            path = QPainterPath()
            for j, val in enumerate(visible_data):
                px = ml + j * step_x
                normalized_val = (val - y_min) / y_range
                py = mt + ph * (1.0 - normalized_val)
                if j == 0:
                    path.moveTo(px, py)
                else:
                    path.lineTo(px, py)

            p.setPen(QPen(ch["color"], 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.drawPath(path)

        p.setClipping(False)

        # 绘制 Y 轴标签
        p.setPen(QPen(self._text_color, 1))
        font = QFont("Consolas", 8)
        p.setFont(font)
        for i in range(self._grid_density_y + 1):
            val = y_max - (y_range * i / self._grid_density_y)
            gy = mt + ph * i / self._grid_density_y
            p.drawText(2, int(gy) - 4, ml - 6, 12, Qt.AlignRight | Qt.AlignVCenter, f"{val:.1f}")

        # 绘制 X 轴时间标签：最右格=当前累计秒数，往左每格减 time_step_s
        timer_interval_s = 0.05  # 50ms per tick
        # 每个X格代表多少秒
        time_step_s = (self._x_range * timer_interval_s) / self._grid_density_x
        current_time_s = self._tick_count * timer_interval_s
        for i in range(self._grid_density_x + 1):
            # i=grid_density_x 为最右，对应当前时刻
            t_sec = current_time_s - (self._grid_density_x - i) * time_step_s
            t_sec = max(0.0, t_sec)
            gx = ml + pw * i / self._grid_density_x
            p.drawLine(int(gx), mt + ph, int(gx), mt + ph + 4)
            label = f"{int(t_sec)}s" if t_sec < 60 else f"{int(t_sec // 60)}:{int(t_sec % 60):02d}"
            p.drawText(int(gx) - 15, mt + ph + 18, 30, 14, Qt.AlignCenter, label)

        # 图例
        lx, ly = ml + 10, mt + 8
        legend_font = QFont("Microsoft YaHei", 8)
        p.setFont(legend_font)
        for ch in visible_chs[:4]:
            p.setPen(QPen(ch["color"], 2))
            p.drawLine(lx, ly + 6, lx + 16, ly + 6)
            p.setPen(QPen(self._text_color, 1))
            p.drawText(lx + 20, ly + 3, ch["name"])
            ly += 16

        p.restore()  # 恢复变换矩阵

    def sizeHint(self): return QSize(400, 250)
    def minimumSizeHint(self): return QSize(150, 100)
# ══════════════════════════════════════════════════════════════
# 自定义控件加载
# ══════════════════════════════════════════════════════════════
CUSTOM_WIDGETS = []


def get_all_categories():
    cats = list(BUILTIN_CATEGORIES)
    # 【修改】直接使用 MultiTrendWidget，名称保持为"实时趋势曲线"以兼容旧习惯
    MultiTrendWidget._display_name = "实时趋势曲线" 
    cats.insert(4, ("📈 工业图表", [("实时趋势曲线", MultiTrendWidget, {})]))
    
    if CUSTOM_WIDGETS:
        custom_items = [(name, cls, kwargs) for name, cls, kwargs, _ in CUSTOM_WIDGETS]
        cats.append(("⭐ 自定义控件", custom_items))
        
    try:
        from svg_import import register_all_svg_widgets
        svg_items = register_all_svg_widgets()
        if svg_items:
            cats.append(("🎨 SVG 图元库", svg_items))
    except Exception:
        pass
    return cats

def get_display_to_entry():
    mapping = {}
    for _, items in BUILTIN_CATEGORIES:
        for item in items: mapping[item[0]] = item
    # 修改此处：使用内置 CurveWidget
    mapping["实时趋势曲线"] = ("实时趋势曲线", MultiTrendWidget, {})
    for name, cls, kwargs, filepath in CUSTOM_WIDGETS: mapping[name] = (name, cls, kwargs, filepath)
    # 添加 SVG 图元
    try:
        from svg_import import register_all_svg_widgets
        for name, cls, kwargs in register_all_svg_widgets():
            mapping[name] = (name, cls, kwargs)
    except Exception:
        pass
    return mapping

NAME_TO_PREFIX = {"按钮":"btn","工具按钮":"tool_btn","命令链接按钮":"cmd_link","对话框按钮组":"btn_box","复选框":"checkbox","单选按钮":"radio","标签":"label","链接标签":"link_label","单行输入框":"line_edit","多行文本框":"text_edit","只读文本浏览器":"text_browser","下拉框":"combo","整数微调框":"spin_box","浮点微调框":"double_spin","日期选择器":"date_edit","时间选择器":"time_edit","日历控件":"calendar","列表控件":"list_widget","树形控件":"tree_widget","表格控件":"table_widget","滑块":"slider","进度条":"progress","旋钮":"dial","液晶数字显示":"lcd","分组框":"group_box","标签页容器":"tab_widget","堆叠容器":"stacked","滚动区域":"scroll_area","分割面板":"splitter","垂直布局容器":"vbox_container","水平布局容器":"hbox_container","框架":"frame","水平分隔线":"h_line","垂直分隔线":"v_line","实时趋势曲线":"trend"}
DEFAULT_SIZES = {"按钮":QSize(120,36),"工具按钮":QSize(80,30),"命令链接按钮":QSize(200,48),"对话框按钮组":QSize(260,40),"复选框":QSize(120,28),"单选按钮":QSize(120,28),"标签":QSize(100,30),"链接标签":QSize(120,30),"单行输入框":QSize(160,32),"多行文本框":QSize(220,120),"只读文本浏览器":QSize(240,140),"下拉框":QSize(130,32),"整数微调框":QSize(120,32),"浮点微调框":QSize(130,32),"日期选择器":QSize(140,32),"时间选择器":QSize(140,32),"日历控件":QSize(280,220),"列表控件":QSize(200,150),"树形控件":QSize(220,180),"表格控件":QSize(280,180),"滑块":QSize(180,30),"进度条":QSize(200,28),"旋钮":QSize(80,80),"液晶数字显示":QSize(120,50),"分组框":QSize(200,140),"标签页容器":QSize(280,180),"堆叠容器":QSize(240,160),"滚动区域":QSize(220,160),"分割面板":QSize(300,160),"垂直布局容器":QSize(220,180),"水平布局容器":QSize(300,100),"框架":QSize(160,100),"水平分隔线":QSize(200,3),"垂直分隔线":QSize(3,120),"实时趋势曲线":QSize(360,200)}

def _esc(s): return s.replace("\\","\\\\").replace('"','\\"')
def _sanitize(name): return re.sub(r"_+","_",re.sub(r"[^a-zA-Z0-9_]","_",name)).strip("_").lower() or "widget"

def _load_user_templates():
    """从文件加载用户模板"""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "user_templates.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return {}

def _save_user_templates():
    """保存用户模板到文件"""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "user_templates.json")
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(USER_TEMPLATES, f, ensure_ascii=False, indent=2)
    except: pass

USER_TEMPLATES = _load_user_templates()

INDUSTRIAL_TEMPLATES = {
    "🖥️ 暗色监控面板": {"description": "深色背景数值监控面板", "widgets": [
        {"type": "框架", "x": 0, "y": 0, "w": 280, "h": 160, "styleSheet": "QFrame{background:#1e1e1e;border:1px solid #333;border-radius:8px;}", "anchor_left": True, "anchor_top": True},
        {"type": "标签", "x": 16, "y": 12, "w": 200, "h": 24, "text": "📊 实时温度监控", "styleSheet": "color:#aaa;font-size:14px;font-weight:bold;background:transparent;border:none;", "tag": "panel_title"},
        {"type": "液晶数字显示", "x": 16, "y": 48, "w": 160, "h": 64, "styleSheet": "QLCDNumber{background:#0d0d0d;border:1px solid #333;border-radius:4px;color:#00ff88;}", "tag": "temp_value", "role": "success"},
        {"type": "标签", "x": 184, "y": 64, "w": 60, "h": 32, "text": "°C", "styleSheet": "color:#00ff88;font-size:24px;font-weight:bold;background:transparent;border:none;", "tag": "temp_unit"},
        {"type": "进度条", "x": 16, "y": 124, "w": 248, "h": 20, "styleSheet": "QProgressBar{background:#0d0d0d;border:1px solid #333;border-radius:4px;text-align:center;color:#aaa;}QProgressBar::chunk{background:#00ff88;border-radius:3px;}", "tag": "temp_bar", "role": "success"},
    ]},
    "🏭 设备状态卡片": {"description": "设备运行状态指示卡", "widgets": [
        {"type": "框架", "x": 0, "y": 0, "w": 240, "h": 140, "styleSheet": "QFrame{background:#fff;border:1px solid #e0e0e0;border-radius:8px;}", "anchor_left": True, "anchor_top": True},
        {"type": "标签", "x": 16, "y": 12, "w": 160, "h": 24, "text": "⚙️ CNC-01 数控机床", "styleSheet": "font-size:14px;font-weight:bold;color:#333;background:transparent;border:none;", "tag": "device_name"},
        {"type": "框架", "x": 192, "y": 14, "w": 20, "h": 20, "styleSheet": "QFrame{background:#27AE60;border-radius:10px;border:2px solid #219A52;}", "tag": "device_status_light"},
        {"type": "标签", "x": 16, "y": 48, "w": 100, "h": 20, "text": "运行状态:", "styleSheet": "color:#666;font-size:12px;background:transparent;border:none;"},
        {"type": "标签", "x": 80, "y": 48, "w": 100, "h": 20, "text": "运行中", "styleSheet": "color:#27AE60;font-size:12px;font-weight:bold;background:transparent;border:none;", "tag": "device_status_text", "role": "success"},
        {"type": "按钮", "x": 16, "y": 100, "w": 100, "h": 28, "text": "查看详情", "role": "primary", "tag": "btn_device_detail"},
        {"type": "按钮", "x": 124, "y": 100, "w": 100, "h": 28, "text": "紧急停止", "role": "danger", "tag": "btn_device_stop"},
    ]},
    "🚨 报警指示灯组": {"description": "三级报警指示灯", "widgets": [
        {"type": "框架", "x": 0, "y": 0, "w": 320, "h": 100, "styleSheet": "QFrame{background:#2c2c2c;border:1px solid #444;border-radius:8px;}", "anchor_left": True, "anchor_top": True},
        {"type": "标签", "x": 16, "y": 8, "w": 200, "h": 20, "text": "🚨 系统报警状态", "styleSheet": "color:#ccc;font-size:12px;font-weight:bold;background:transparent;border:none;"},
        {"type": "框架", "x": 20, "y": 40, "w": 24, "h": 24, "styleSheet": "QFrame{background:#27AE60;border-radius:12px;border:2px solid #1e8449;}", "tag": "alarm_normal_light"},
        {"type": "标签", "x": 50, "y": 42, "w": 50, "h": 20, "text": "正常", "styleSheet": "color:#27AE60;font-size:12px;background:transparent;border:none;", "tag": "alarm_normal_text", "role": "success"},
        {"type": "框架", "x": 110, "y": 40, "w": 24, "h": 24, "styleSheet": "QFrame{background:#555;border-radius:12px;border:2px solid #444;}", "tag": "alarm_warning_light"},
        {"type": "标签", "x": 140, "y": 42, "w": 50, "h": 20, "text": "警告", "styleSheet": "color:#888;font-size:12px;background:transparent;border:none;", "tag": "alarm_warning_text", "role": "warning"},
        {"type": "框架", "x": 200, "y": 40, "w": 24, "h": 24, "styleSheet": "QFrame{background:#555;border-radius:12px;border:2px solid #444;}", "tag": "alarm_fault_light"},
        {"type": "标签", "x": 230, "y": 42, "w": 50, "h": 20, "text": "故障", "styleSheet": "color:#888;font-size:12px;background:transparent;border:none;", "tag": "alarm_fault_text", "role": "danger"},
        {"type": "按钮", "x": 230, "y": 68, "w": 74, "h": 24, "text": "消音", "role": "outline", "tag": "btn_alarm_mute"},
    ]},
    "🎛️ PID控制面板": {"description": "PID参数显示与设定值/实际值/输出值", "widgets": [
        {"type": "框架", "x": 0, "y": 0, "w": 340, "h": 200, "styleSheet": "QFrame{background:#f8f9fa;border:1px solid #dee2e6;border-radius:8px;}", "anchor_left": True, "anchor_top": True},
        {"type": "标签", "x": 12, "y": 8, "w": 200, "h": 22, "text": "🎛️ PID回路控制 — TC-101", "styleSheet": "font-size:13px;font-weight:bold;color:#333;background:transparent;border:none;", "tag": "pid_title"},
        {"type": "标签", "x": 16, "y": 40, "w": 80, "h": 20, "text": "设定值(SV):", "styleSheet": "color:#666;font-size:12px;background:transparent;border:none;"},
        {"type": "单行输入框", "x": 100, "y": 38, "w": 100, "h": 24, "tag": "pid_sv", "styleSheet": "font-weight:bold;font-size:12px;"},
        {"type": "标签", "x": 212, "y": 40, "w": 60, "h": 20, "text": "°C", "styleSheet": "color:#666;font-size:12px;background:transparent;border:none;"},
        {"type": "标签", "x": 16, "y": 68, "w": 80, "h": 20, "text": "实际值(PV):", "styleSheet": "color:#666;font-size:12px;background:transparent;border:none;"},
        {"type": "液晶数字显示", "x": 100, "y": 64, "w": 100, "h": 32, "tag": "pid_pv", "role": "success"},
        {"type": "标签", "x": 212, "y": 72, "w": 60, "h": 20, "text": "°C", "styleSheet": "color:#666;font-size:12px;background:transparent;border:none;"},
        {"type": "标签", "x": 16, "y": 104, "w": 80, "h": 20, "text": "输出值(MV):", "styleSheet": "color:#666;font-size:12px;background:transparent;border:none;"},
        {"type": "进度条", "x": 100, "y": 104, "w": 160, "h": 20, "tag": "pid_mv", "role": "success"},
        {"type": "标签", "x": 16, "y": 134, "w": 50, "h": 18, "text": "Kp:", "styleSheet": "color:#888;font-size:11px;background:transparent;border:none;"},
        {"type": "单行输入框", "x": 48, "y": 132, "w": 60, "h": 20, "tag": "pid_kp", "styleSheet": "font-size:11px;"},
        {"type": "标签", "x": 116, "y": 134, "w": 30, "h": 18, "text": "Ki:", "styleSheet": "color:#888;font-size:11px;background:transparent;border:none;"},
        {"type": "单行输入框", "x": 140, "y": 132, "w": 60, "h": 20, "tag": "pid_ki", "styleSheet": "font-size:11px;"},
        {"type": "标签", "x": 208, "y": 134, "w": 35, "h": 18, "text": "Kd:", "styleSheet": "color:#888;font-size:11px;background:transparent;border:none;"},
        {"type": "单行输入框", "x": 236, "y": 132, "w": 60, "h": 20, "tag": "pid_kd", "styleSheet": "font-size:11px;"},
        {"type": "按钮", "x": 16, "y": 164, "w": 80, "h": 26, "text": "自动模式", "role": "primary", "tag": "pid_auto_btn"},
        {"type": "按钮", "x": 104, "y": 164, "w": 80, "h": 26, "text": "手动模式", "role": "outline", "tag": "pid_manual_btn"},
        {"type": "按钮", "x": 220, "y": 164, "w": 80, "h": 26, "text": "紧急停止", "role": "danger", "tag": "pid_stop_btn"},
    ]},
    "⛽ 泵阀管路图": {"description": "泵/阀门状态指示与控制", "widgets": [
        {"type": "框架", "x": 0, "y": 0, "w": 360, "h": 160, "styleSheet": "QFrame{background:#f5f5f5;border:1px solid #ccc;border-radius:8px;}", "anchor_left": True, "anchor_top": True},
        {"type": "标签", "x": 12, "y": 8, "w": 200, "h": 22, "text": "⛽ 冷却水泵系统 — PU-201", "styleSheet": "font-size:13px;font-weight:bold;color:#333;background:transparent;border:none;", "tag": "pump_title"},
        {"type": "框架", "x": 20, "y": 44, "w": 80, "h": 80, "styleSheet": "QFrame{background:#fff;border:2px solid #4A90D9;border-radius:40px;}", "tag": "pump_status_frame"},
        {"type": "标签", "x": 32, "y": 62, "w": 56, "h": 40, "text": "PUMP\n运行中", "styleSheet": "color:#27AE60;font-size:11px;font-weight:bold;background:transparent;border:none;", "tag": "pump_status", "role": "success"},
        {"type": "框架", "x": 130, "y": 60, "w": 16, "h": 48, "styleSheet": "QFrame{background:#27AE60;border:1px solid #1e8449;border-radius:3px;}", "tag": "valve_in_light"},
        {"type": "标签", "x": 118, "y": 112, "w": 40, "h": 18, "text": "进水阀", "styleSheet": "color:#666;font-size:10px;background:transparent;border:none;", "tag": "valve_in_label"},
        {"type": "框架", "x": 176, "y": 60, "w": 16, "h": 48, "styleSheet": "QFrame{background:#F39C12;border:1px solid #D68910;border-radius:3px;}", "tag": "valve_out_light"},
        {"type": "标签", "x": 164, "y": 112, "w": 40, "h": 18, "text": "出水阀", "styleSheet": "color:#666;font-size:10px;background:transparent;border:none;", "tag": "valve_out_label"},
        {"type": "标签", "x": 230, "y": 44, "w": 60, "h": 18, "text": "流量:", "styleSheet": "color:#666;font-size:11px;background:transparent;border:none;"},
        {"type": "液晶数字显示", "x": 230, "y": 62, "w": 100, "h": 34, "tag": "pump_flow", "role": "success"},
        {"type": "标签", "x": 230, "y": 100, "w": 60, "h": 18, "text": "压力:", "styleSheet": "color:#666;font-size:11px;background:transparent;border:none;"},
        {"type": "进度条", "x": 230, "y": 118, "w": 100, "h": 18, "tag": "pump_pressure", "role": "success"},
        {"type": "按钮", "x": 16, "y": 130, "w": 70, "h": 22, "text": "启动", "role": "success", "tag": "pump_start_btn"},
        {"type": "按钮", "x": 92, "y": 130, "w": 70, "h": 22, "text": "停止", "role": "danger", "tag": "pump_stop_btn"},
        {"type": "按钮", "x": 168, "y": 130, "w": 70, "h": 22, "text": "复位", "role": "outline", "tag": "pump_reset_btn"},
    ]},
    "📊 数据表格面板": {"description": "多通道数据监控表格", "widgets": [
        {"type": "框架", "x": 0, "y": 0, "w": 380, "h": 180, "styleSheet": "QFrame{background:#fff;border:1px solid #e0e0e0;border-radius:8px;}", "anchor_left": True, "anchor_top": True},
        {"type": "标签", "x": 12, "y": 8, "w": 200, "h": 22, "text": "📊 多通道数据监控", "styleSheet": "font-size:13px;font-weight:bold;color:#333;background:transparent;border:none;"},
        {"type": "表格控件", "x": 8, "y": 34, "w": 364, "h": 110, "tag": "data_table"},
        {"type": "按钮", "x": 8, "y": 150, "w": 80, "h": 24, "text": "刷新数据", "role": "primary", "tag": "table_refresh_btn"},
        {"type": "按钮", "x": 96, "y": 150, "w": 80, "h": 24, "text": "导出CSV", "role": "outline", "tag": "table_export_btn"},
        {"type": "按钮", "x": 184, "y": 150, "w": 80, "h": 24, "text": "清空表格", "role": "ghost", "tag": "table_clear_btn"},
    ]},
}


class CustomWidgetLoader:
    @staticmethod
    def load_from_file(filepath):
        results = []
        try:
            spec = importlib.util.spec_from_file_location("_custom_widget_mod", filepath)
            if spec is None or spec.loader is None: return results
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            for attr_name in dir(mod):
                obj = getattr(mod, attr_name)
                if (isinstance(obj, type) and issubclass(obj, QWidget) and obj is not QWidget
                        and obj is not QFrame and obj is not QGroupBox and not attr_name.startswith("_")
                        and obj.__module__ == mod.__name__):
                    display = getattr(obj, '_display_name', None) or attr_name
                    results.append((display, obj, {}, filepath))
        except Exception as e: print(f"[CustomWidgetLoader] 加载失败 {filepath}: {e}")
        return results

    @staticmethod
    def register_widgets(filepaths):
        global CUSTOM_WIDGETS
        CUSTOM_WIDGETS.clear()
        for fp in filepaths: CUSTOM_WIDGETS.extend(CustomWidgetLoader.load_from_file(fp))
        return len(CUSTOM_WIDGETS)


class ThemeEditorDialog(QDialog):
    qss_changed = Signal(str)
    def __init__(self, current_qss, parent=None):
        super().__init__(parent); self.setWindowTitle("🎨 主题编辑器"); self.resize(700, 500)
        layout = QVBoxLayout(self)
        hint = QLabel("编辑 QSS 样式表，修改后自动实时预览到设计器画布")
        hint.setStyleSheet("color:#666; font-size:12px; padding:4px;"); layout.addWidget(hint)
        self.editor = QPlainTextEdit(); self.editor.setPlainText(current_qss)
        self.editor.setStyleSheet("QPlainTextEdit { font-family: 'Consolas', monospace; font-size: 12px; }")
        layout.addWidget(self.editor)
        btn_layout = QHBoxLayout()
        for label, slot in [("🔄 重置为默认", lambda: self.editor.setPlainText(DEFAULT_QSS)),
                            ("📂 从文件加载", self._load_from_file), ("💾 保存为文件", self._save_to_file),
                            ("✅ 应用并关闭", self.accept), ("❌ 取消", self.reject)]:
            btn = QPushButton(label); btn.clicked.connect(slot); btn_layout.addWidget(btn)
        layout.addLayout(btn_layout)
        self._debounce_timer = QTimer(self); self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(lambda: self.qss_changed.emit(self.editor.toPlainText()))
        self.editor.textChanged.connect(lambda: self._debounce_timer.start(300))
    def _load_from_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "加载QSS文件", "", "QSS Files (*.qss);;All Files (*)")
        if path:
            try:
                with open(path, "r", encoding="utf-8") as f: self.editor.setPlainText(f.read())
            except Exception as e: QMessageBox.warning(self, "加载失败", str(e))
    def _save_to_file(self):
        path, _ = QFileDialog.getSaveFileName(self, "保存QSS文件", "custom_theme.qss", "QSS Files (*.qss)")
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f: f.write(self.editor.toPlainText())
                QMessageBox.information(self, "保存成功", f"已保存至:\n{path}")
            except Exception as e: QMessageBox.warning(self, "保存失败", str(e))
    def get_qss(self): return self.editor.toPlainText()
class QssBuilderDialog(QDialog):
    """可视化 QSS 构建器 — 双击属性面板 styleSheet 字段触发"""
    
    # 不同控件类型支持的样式属性
    WIDGET_STYLE_MAP = {
        "QPushButton": ["bgColor", "borderRadius", "borderWidth", "borderColor", 
                        "fontSize", "fontColor", "hoverBg", "padding"],
        "QToolButton": ["bgColor", "borderRadius", "borderWidth", "borderColor", 
                        "fontSize", "fontColor", "hoverBg", "padding"],
        "QLineEdit": ["bgColor", "borderRadius", "borderWidth", "borderColor", 
                      "fontSize", "fontColor", "focusBorder", "padding"],
        "QComboBox": ["bgColor", "borderRadius", "borderWidth", "borderColor", 
                      "fontSize", "fontColor", "padding"],
        "QLabel": ["fontSize", "fontColor", "fontWeight", "bgColor"],
        "QGroupBox": ["bgColor", "borderRadius", "borderWidth", "borderColor", 
                      "titleColor", "padding"],
        "QProgressBar": ["bgColor", "borderRadius", "chunkColor", "height"],
        "QSlider": ["grooveColor", "handleColor", "handleSize"],
        "default": ["bgColor", "borderRadius", "borderWidth", "borderColor", 
                    "fontSize", "fontColor"]
    }
    
    def __init__(self, widget, parent=None):
        super().__init__(parent)
        self.target_widget = widget
        self.widget_class = type(widget).__name__
        self.setWindowTitle(f"🎨 QSS 构建器 — {self.widget_class}")
        self.resize(720, 480)
        
        # 解析现有样式
        self.current_style = self._parse_existing_qss(widget.styleSheet())
        
        layout = QHBoxLayout(self)
        layout.setSpacing(12)
        
        # ── 左侧：实时预览区 ──
        preview_panel = QVBoxLayout()
        preview_label = QLabel("<b>实时预览</b>")
        preview_label.setStyleSheet("font-size:12px; color:#666; padding:4px;")
        preview_panel.addWidget(preview_label)
        
        self.preview_container = QFrame()
        self.preview_container.setMinimumSize(280, 200)
        self.preview_container.setStyleSheet(
            "QFrame{background:#f5f5f5; border:1px dashed #ccc; border-radius:8px;}"
        )
        preview_layout = QVBoxLayout(self.preview_container)
        preview_layout.setAlignment(Qt.AlignCenter)
        
        # 先放一个占位符，避免构造阶段触发无效绘制
        self._preview_placeholder = QLabel("预览加载中...")
        self._preview_placeholder.setAlignment(Qt.AlignCenter)
        self._preview_placeholder.setStyleSheet("color:#999; font-size:12px;")
        preview_layout.addWidget(self._preview_placeholder)
        
        self.preview_widget = None  # 延迟创建
        preview_panel.addWidget(self.preview_container)
        
        # 生成的 QSS 代码显示
        code_label = QLabel("<b>生成代码</b>")
        code_label.setStyleSheet("font-size:12px; color:#666; padding:4px;")
        preview_panel.addWidget(code_label)
        
        self.code_display = QPlainTextEdit()
        self.code_display.setReadOnly(True)
        self.code_display.setMaximumHeight(120)
        self.code_display.setStyleSheet(
            "QPlainTextEdit{font-family:'Consolas',monospace; font-size:11px; "
            "background:#1e1e1e; color:#d4d4d4; border:1px solid #333; border-radius:4px; padding:6px;}"
        )
        preview_panel.addWidget(self.code_display)
        
        # ── 右侧：样式控制面板 ──
        control_panel = QVBoxLayout()
        control_header = QLabel("<b>样式参数</b>")
        control_header.setStyleSheet("font-size:12px; color:#666; padding:4px;")
        control_panel.addWidget(control_header)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{border:none;}")
        
        self.form_widget = QWidget()
        self.form_layout = QFormLayout(self.form_widget)
        self.form_layout.setSpacing(8)
        self.form_layout.setContentsMargins(4, 4, 4, 4)
        
        self.editors = {}
        # ⚠️ 注意：此处不再调用 self._build_editors()
        # 编辑器构建已延迟到 showEvent 中执行，避免构造阶段 QPainter 报错
        
        scroll.setWidget(self.form_widget)
        control_panel.addWidget(scroll)
        
        # 按钮栏
        btn_layout = QHBoxLayout()
        btn_reset = QPushButton("🔄 重置")
        btn_reset.clicked.connect(self._reset_to_default)
        btn_apply = QPushButton("✅ 应用")
        btn_apply.setStyleSheet(
            "QPushButton{background:#27AE60;color:#fff;border:none;border-radius:4px;"
            "padding:6px 18px;font-weight:bold;} QPushButton:hover{background:#219A52;}"
        )
        btn_apply.clicked.connect(self.accept)
        btn_cancel = QPushButton("❌ 取消")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_reset)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_apply)
        btn_layout.addWidget(btn_cancel)
        control_panel.addLayout(btn_layout)
        
        layout.addLayout(preview_panel, 1)
        layout.addLayout(control_panel, 1)
        
    
    
    def _create_preview_widget(self):
        cls = type(self.target_widget)
        try:
            w = cls()
            w.setMinimumSize(80, 30)  # ← 关键：防止零尺寸触发 QPainter 错误
            if hasattr(w, 'setText') and hasattr(self.target_widget, 'text'):
                w.setText(self.target_widget.text() or "预览文本")
            if hasattr(w, 'setTitle') and hasattr(self.target_widget, 'title'):
                w.setTitle(self.target_widget.title() or "预览标题")
            if isinstance(w, QProgressBar):
                w.setValue(65)
            if isinstance(w, QSlider):
                w.setValue(60)
            if isinstance(w, QComboBox):
                w.addItems(["选项1", "选项2"])
            w.setMinimumWidth(160)
            return w
        except Exception:
            fallback = QLabel("预览不可用")
            fallback.setAlignment(Qt.AlignCenter)
            fallback.setMinimumSize(80, 30)
            return fallback
    
    def _build_editors(self):
        """根据控件类型动态构建编辑器"""
        supported = self.WIDGET_STYLE_MAP.get(
            self.widget_class, self.WIDGET_STYLE_MAP["default"]
        )
        
        editor_configs = {
            "bgColor": ("背景色", "color", self.current_style.get("bgColor", "#ffffff")),
            "borderRadius": ("圆角(px)", "spin", self.current_style.get("borderRadius", 4), (0, 50)),
            "borderWidth": ("边框宽度(px)", "spin", self.current_style.get("borderWidth", 1), (0, 10)),
            "borderColor": ("边框颜色", "color", self.current_style.get("borderColor", "#d0d0d0")),
            "fontSize": ("字体大小(pt)", "spin", self.current_style.get("fontSize", 13), (6, 72)),
            "fontColor": ("字体颜色", "color", self.current_style.get("fontColor", "#333333")),
            "fontWeight": ("粗体", "check", self.current_style.get("fontWeight", False)),
            "hoverBg": ("悬停背景色", "color", self.current_style.get("hoverBg", "#e8f0fe")),
            "focusBorder": ("聚焦边框色", "color", self.current_style.get("focusBorder", "#4A90D9")),
            "padding": ("内边距(px)", "spin", self.current_style.get("padding", 6), (0, 30)),
            "titleColor": ("标题颜色", "color", self.current_style.get("titleColor", "#666666")),
            "chunkColor": ("进度条颜色", "color", self.current_style.get("chunkColor", "#4A90D9")),
            "height": ("高度(px)", "spin", self.current_style.get("height", 20), (8, 60)),
            "grooveColor": ("滑槽颜色", "color", self.current_style.get("grooveColor", "#e0e0e0")),
            "handleColor": ("滑块颜色", "color", self.current_style.get("handleColor", "#4A90D9")),
            "handleSize": ("滑块大小(px)", "spin", self.current_style.get("handleSize", 16), (8, 40)),
        }
        
        for prop in supported:
            if prop not in editor_configs:
                continue
            cfg = editor_configs[prop]
            label_text = cfg[0]
            editor_type = cfg[1]
            default_val = cfg[2]
            
            if editor_type == "color":
                editor = QPushButton()
                editor.setFixedSize(80, 28)
                editor.setStyleSheet(
                    f"QPushButton{{background:{default_val}; border:1px solid #aaa; border-radius:4px;}}"
                )
                editor.setProperty("_color", default_val)
                editor.clicked.connect(lambda checked, e=editor, p=prop: self._pick_color(e, p))
            elif editor_type == "spin":
                editor = QSpinBox()
                editor.setRange(*cfg[3])
                editor.setValue(int(default_val))
                editor.valueChanged.connect(lambda v, p=prop: self._on_value_changed(p, v))
            elif editor_type == "check":
                editor = QCheckBox()
                editor.setChecked(bool(default_val))
                editor.stateChanged.connect(lambda s, p=prop: self._on_value_changed(p, bool(s)))
            else:
                continue
            
            self.editors[prop] = editor
            self.form_layout.addRow(label_text + ":", editor)
    
    def _pick_color(self, btn, prop):
        from PySide6.QtWidgets import QColorDialog
        current = btn.property("_color")
        color = QColorDialog.getColor(QColor(current), self, f"选择{prop}颜色")
        if color.isValid():
                hex_color = color.name()
                btn.setProperty("_color", hex_color)
                btn.setStyleSheet(
                    f"QPushButton{{background:{hex_color}; border:1px solid #aaa; border-radius:4px;}}"
                )
                self._on_value_changed(prop, hex_color)
    
    def _on_value_changed(self, prop, value):
        self.current_style[prop] = value
        self._update_preview()
    
    def _update_preview(self):
        """重新生成 QSS 并应用到预览控件"""
        if self.preview_widget is None:
            return  # 防止预览控件未创建时报错
        qss = self._generate_qss()
        self.preview_widget.setStyleSheet(qss)
        self.code_display.setPlainText(qss)
    
    def _generate_qss(self):
        """根据当前参数生成 QSS 字符串"""
        s = self.current_style
        cls = self.widget_class
        lines = []
        
        # 主样式块
        props = []
        if "bgColor" in s: props.append(f"background:{s['bgColor']};")
        if "borderRadius" in s: props.append(f"border-radius:{s['borderRadius']}px;")
        if "borderWidth" in s and "borderColor" in s:
            props.append(f"border:{s['borderWidth']}px solid {s['borderColor']};")
        if "fontSize" in s: props.append(f"font-size:{s['fontSize']}pt;")
        if "fontColor" in s: props.append(f"color:{s['fontColor']};")
        if "fontWeight" in s and s["fontWeight"]: props.append("font-weight:bold;")
        if "padding" in s: props.append(f"padding:{s['padding']}px;")
        
        if props:
            lines.append(f"{cls} {{ {' '.join(props)} }}")
        
        # 悬停状态
        if "hoverBg" in s:
            hover_props = [f"background:{s['hoverBg']};"]
            if "borderColor" in s:
                hover_props.append(f"border-color:{s['borderColor']};")
            lines.append(f"{cls}:hover {{ {' '.join(hover_props)} }}")
        
        # 聚焦状态
        if "focusBorder" in s:
            lines.append(f"{cls}:focus {{ border-color:{s['focusBorder']}; }}")
        
        # QGroupBox 标题
        if cls == "QGroupBox" and "titleColor" in s:
            lines.append(f"{cls}::title {{ color:{s['titleColor']}; }}")
        
        # QProgressBar chunk
        if cls == "QProgressBar":
            if "chunkColor" in s:
                cr = s.get("borderRadius", 3)
                lines.append(f"{cls}::chunk {{ background:{s['chunkColor']}; border-radius:{cr}px; }}")
            if "height" in s:
                lines.append(f"{cls} {{ min-height:{s['height']}px; }}")
        
        # QSlider
        if cls == "QSlider":
            if "grooveColor" in s:
                lines.append(f"{cls}::groove:horizontal {{ background:{s['grooveColor']}; height:6px; border-radius:3px; }}")
            if "handleColor" in s:
                hs = s.get("handleSize", 16)
                margin = -(hs // 2 - 3)
                lines.append(
                    f"{cls}::handle:horizontal {{ width:{hs}px; height:{hs}px; "
                    f"margin:{margin}px 0; background:{s['handleColor']}; border-radius:{hs//2}px; }}"
                )
        
        return "\n".join(lines)
    
    def _parse_existing_qss(self, qss_str):
        """简单解析现有 QSS，提取已知属性值"""
        result = {}
        if not qss_str:
            return result
        
        import re
        # 提取常见属性
        patterns = {
            "bgColor": r"background\s*:\s*(#[0-9a-fA-F]{3,8})",
            "borderRadius": r"border-radius\s*:\s*(\d+)px",
            "borderWidth": r"border\s*:\s*(\d+)px",
            "borderColor": r"border\s*:\s*\d+px\s+solid\s+(#[0-9a-fA-F]{3,8})",
            "fontSize": r"font-size\s*:\s*(\d+)p[tx]",
            "fontColor": r"(?<!-)color\s*:\s*(#[0-9a-fA-F]{3,8})",
            "fontWeight": r"font-weight\s*:\s*bold",
            "padding": r"padding\s*:\s*(\d+)px",
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, qss_str)
            if match:
                val = match.group(1) if match.lastindex else True
                if key in ("borderRadius", "borderWidth", "fontSize", "padding"):
                    try: val = int(val)
                    except: pass
                result[key] = val
        
        return result
    
    def _reset_to_default(self):
        self.current_style = {}
        for prop, editor in self.editors.items():
            if isinstance(editor, QPushButton):
                editor.setProperty("_color", "#ffffff")
                editor.setStyleSheet("QPushButton{background:#ffffff; border:1px solid #aaa; border-radius:4px;}")
            elif isinstance(editor, QSpinBox):
                defaults = {"borderRadius": 4, "borderWidth": 1, "fontSize": 13, 
                           "padding": 6, "height": 20, "handleSize": 16}
                editor.setValue(defaults.get(prop, 0))
            elif isinstance(editor, QCheckBox):
                editor.setChecked(False)
        self._update_preview()
    
    def get_qss(self):
        return self._generate_qss()
    def showEvent(self, event):
        """延迟初始化编辑器和预览控件，避免构造阶段 QPainter 报错"""
        super().showEvent(event)
        # 1. 先构建编辑器（窗口已就绪，颜色按钮 setStyleSheet 安全）
        if not self.editors:
            self._build_editors()
        # 2. 创建预览控件
        if self.preview_widget is None:
            layout = self.preview_container.layout()
            if hasattr(self, '_preview_placeholder') and self._preview_placeholder:
                layout.removeWidget(self._preview_placeholder)
                self._preview_placeholder.deleteLater()
                self._preview_placeholder = None
            self.preview_widget = self._create_preview_widget()
            layout.addWidget(self.preview_widget)
        # 3. 现在才应用初始样式
        self._update_preview()


class CallbackEditorDialog(QDialog):
    """回调函数编辑器 — 右键点击控件→编辑回调→自动集成到代码生成"""
    def __init__(self, canvas, slot_name, existing_code="", parent=None):
        super().__init__(parent)
        self.canvas = canvas
        self.slot_name = slot_name
        self.setWindowTitle(f"✏️ 编辑回调函数: {slot_name}")
        self.resize(700, 500)
        layout = QVBoxLayout(self)

        # 提示栏
        hint = QLabel(
            f"正在编辑回调函数: <b>{slot_name}</b>"
            "  按 <b>Ctrl+S</b> 保存  <b>ESC</b> 取消"
        )
        hint.setStyleSheet("color:#666; font-size:12px; padding:4px; background:#f5f5f5; border-radius:4px;")
        layout.addWidget(hint)

        # 代码编辑器
        self.editor = QPlainTextEdit()
        self.editor.setPlainText(existing_code or self._default_code())
        self.editor.setStyleSheet(
            "QPlainTextEdit {"
            "  font-family: 'Consolas', 'Courier New', monospace;"
            "  font-size: 13px;"
            "  background: #1e1e1e; color: #d4d4d4;"
            "  border: 1px solid #333; border-radius: 4px;"
            "  padding: 8px;"
            "}"
        )
        self.editor.setTabStopDistance(
            QFontMetrics(self.editor.font()).horizontalAdvance(' ') * 4
        )
        layout.addWidget(self.editor)

        # 帮助信息
        help_text = QLabel(
            "💡 提示: 在此编写该回调函数的完整代码。"
            "函数签名中的 <code>self</code> 即为生成的窗口实例，"
            "可通过 <code>self.btn_start</code> 等方式访问其他控件。"
        )
        help_text.setWordWrap(True)
        help_text.setStyleSheet("color:#888; font-size:11px; padding:4px;")
        layout.addWidget(help_text)

        # 按钮栏
        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("💾 保存并关闭")
        self.btn_save.setStyleSheet(
            "QPushButton{background:#27AE60;color:#fff;border:none;"
            "border-radius:4px;padding:6px 18px;font-size:13px;font-weight:bold;}"
            "QPushButton:hover{background:#219A52;}"
        )
        self.btn_cancel = QPushButton("❌ 取消")
        self.btn_cancel.setStyleSheet(
            "QPushButton{background:#f0f0f0;border:1px solid #ccc;"
            "border-radius:4px;padding:6px 18px;font-size:13px;}"
        )
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

        self.btn_save.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)

        # Ctrl+S 快捷键保存
        QShortcut(QKeySequence("Ctrl+S"), self).activated.connect(self.accept)

    def _default_code(self):
        return (f"def {self.slot_name}(self):\n"
                f"    # TODO: 在此编写 {self.slot_name} 的回调逻辑\n"
                f"    pass\n")

    def get_code(self):
        return self.editor.toPlainText()


class SignalSlotDialog(QDialog):
    def __init__(self, canvas, parent=None):
        super().__init__(parent)
        self.canvas = canvas
        self.setWindowTitle("🔗 信号/槽编辑器")
        self.resize(560, 500)
        layout = QVBoxLayout(self)
        self.conn_list = QListWidget()
        layout.addWidget(self.conn_list)

        # 连接列表右键菜单
        self.conn_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.conn_list.customContextMenuRequested.connect(self._show_conn_context_menu)

        form = QHBoxLayout()
        self.combo_source = QComboBox()
        self.combo_signal = QComboBox()
        self.edit_slot = QLineEdit()
        self.edit_slot.setPlaceholderText("槽函数名 (如 on_btn_start_clicked)")
        form.addWidget(QLabel("源:")); form.addWidget(self.combo_source)
        form.addWidget(QLabel("信号:")); form.addWidget(self.combo_signal)
        form.addWidget(QLabel("→"))
        form.addWidget(QLabel("槽:")); form.addWidget(self.edit_slot)
        layout.addLayout(form)
        btn_layout = QHBoxLayout()
        self.btn_add = QPushButton("➕ 添加连接")
        self.btn_remove = QPushButton("➖ 删除选中")
        self.btn_edit_callback = QPushButton("✏️ 编辑回调...")
        self.btn_close = QPushButton("关闭")
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_remove)
        btn_layout.addWidget(self.btn_edit_callback)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_close)
        layout.addLayout(btn_layout)
        self.btn_add.clicked.connect(self._add_connection)
        self.btn_remove.clicked.connect(self._remove_connection)
        self.btn_edit_callback.clicked.connect(self._edit_selected_callback)
        self.btn_close.clicked.connect(self.accept)
        self.combo_source.currentTextChanged.connect(self._on_source_changed)
        self._refresh_lists()

    def _show_conn_context_menu(self, pos):
        item = self.conn_list.itemAt(pos)
        if not item:
            return
        row = self.conn_list.row(item)
        if row < 0 or row >= len(self.canvas._signal_connections):
            return
        menu = QMenu(self)
        act_edit = menu.addAction("✏️ 编辑回调函数...")
        act_remove = menu.addAction("➖ 删除连接")
        chosen = menu.exec(self.conn_list.mapToGlobal(pos))
        if chosen == act_edit:
            self._edit_callback_at(row)
        elif chosen == act_remove:
            self._remove_at(row)

    def _remove_at(self, row):
        if 0 <= row < len(self.canvas._signal_connections):
            self.canvas._signal_connections.pop(row)
            self.canvas.widget_modified.emit()
            self._refresh_lists()

    def _edit_selected_callback(self):
        row = self.conn_list.currentRow()
        if row < 0 or row >= len(self.canvas._signal_connections):
            QMessageBox.warning(self, "提示", "请先选中一个连接")
            return
        self._edit_callback_at(row)

    def _edit_callback_at(self, row):
        conn = self.canvas._signal_connections[row]
        slot_name = conn["slot"]
        existing_code = self.canvas._callback_code.get(slot_name, "")
        dlg = CallbackEditorDialog(self.canvas, slot_name, existing_code, self)
        if dlg.exec() == QDialog.Accepted:
            self.canvas._callback_code[slot_name] = dlg.get_code()
            self.canvas.widget_modified.emit()

    def _get_all_widgets(self):
        result = []
        for w in self.canvas._canvas_widgets:
            if not w.property("_designer_hidden"):
                name = w.objectName() or type(w).__name__
                result.append((name, w))
        return result

    def _refresh_lists(self):
        self.conn_list.clear()
        widgets = self._get_all_widgets()
        self.combo_source.clear()
        for name, _ in widgets:
            self.combo_source.addItem(name)
        for conn in self.canvas._signal_connections:
            self.conn_list.addItem(f"{conn['source']}.{conn['signal']} → {conn['slot']}")

    def _on_source_changed(self, source_name):
        self.combo_signal.clear()
        widgets = self._get_all_widgets()
        for name, w in widgets:
            if name == source_name:
                cls_name = type(w).__name__
                signals = WIDGET_SIGNALS.get(cls_name, ["clicked()"])
                self.combo_signal.addItems(signals)
                break

    def _add_connection(self):
        source = self.combo_source.currentText()
        signal = self.combo_signal.currentText()
        slot = self.edit_slot.text().strip()
        if not source or not signal or not slot:
            QMessageBox.warning(self, "提示", "请填写完整的源、信号和槽函数名")
            return
        conn = {"source": source, "signal": signal, "slot": slot}
        self.canvas._signal_connections.append(conn)
        self.canvas.widget_modified.emit()
        self._refresh_lists()

    def _remove_connection(self):
        row = self.conn_list.currentRow()
        if row >= 0 and row < len(self.canvas._signal_connections):
            self.canvas._signal_connections.pop(row)
            self.canvas.widget_modified.emit()
            self._refresh_lists()


# ═══════════════════════════════════════════════════════════════
# P10: 控件树/层级面板 (WidgetTreePanel)
# ═══════════════════════════════════════════════════════════════
class _DragTree(QTreeWidget):
    """支持拖拽改变父子关系的树控件"""
    def __init__(self, panel, parent=None):
        super().__init__(parent)
        self._panel = panel
        self._highlight_item = None

    def dragMoveEvent(self, event):
        super().dragMoveEvent(event)
        # 高亮鼠标悬停的容器项
        item = self.itemAt(event.position().toPoint())
        if item != self._highlight_item:
            self._clear_highlight()
            if item:
                wid = item.data(0, Qt.UserRole)
                w = self._panel._find_widget_by_id(wid) if wid else None
                if w and hasattr(w, '_content_layout'):
                    self._highlight_item = item
                    item.setBackground(0, QColor("#d0e4f7"))

    def dragLeaveEvent(self, event):
        super().dragLeaveEvent(event)
        self._clear_highlight()

    def dropEvent(self, event):
        self._clear_highlight()
        old_state = self._panel._snapshot_tree()
        super().dropEvent(event)
        self._panel._sync_tree_to_canvas(old_state)

    def _clear_highlight(self):
        if self._highlight_item:
            self._highlight_item.setBackground(0, QColor(Qt.transparent))
            self._highlight_item = None


class WidgetTreePanel(QWidget):
    """控件层级树面板 — 显示父子关系，支持拖拽调整Z-order和父子关系"""
    item_selected = Signal(object)  # 发射 widget 对象

    def __init__(self, canvas, parent=None):
        super().__init__(parent)
        self.canvas = canvas
        self.setMinimumWidth(180); self.setMaximumWidth(300)
        layout = QVBoxLayout(self); layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(2)
        self.header = QLabel("<b>📁 控件层级</b>")
        self.header.setStyleSheet("padding:4px 8px; font-size:12px; background:#f0f0f0; border-bottom:1px solid #ddd;")
        layout.addWidget(self.header)

        self.tree = _DragTree(self)
        self.tree.setHeaderHidden(True)
        self.tree.setDragEnabled(True)
        self.tree.setAcceptDrops(True)
        self.tree.setDropIndicatorShown(True)
        self.tree.setDragDropMode(QAbstractItemView.InternalMove)
        self.tree.setDefaultDropAction(Qt.MoveAction)
        self.tree.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tree.setStyleSheet("QTreeWidget{font-size:12px;} QTreeWidget::item{padding:2px 4px;} QTreeWidget::item:selected{background:#4A90D9;color:#fff;}")
        layout.addWidget(self.tree)

        self.tree.itemClicked.connect(self._on_item_clicked)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)

    def rebuild(self):
        """从画布重建控件树"""
        self.tree.clear()
        for w in self.canvas._canvas_widgets:
            if w.property("_designer_hidden"):
                continue
            item = self._build_item(w)
            self.tree.addTopLevelItem(item)
            if hasattr(w, "_content_layout"):
                self._build_children(item, w._content_layout)

    def _build_item(self, w):
        name = w.objectName(); display = w.property("_display_name") or ""
        locked = "🔒" if w.property("_locked") else ""
        tag = w.property("_tag") or ""
        tag_str = f" [{tag}]" if tag else ""
        text = f"{locked}{name} ({display}{tag_str})"
        item = QTreeWidgetItem([text])
        item.setData(0, Qt.UserRole, id(w))
        if w.property("_locked"):
            item.setForeground(0, QColor("#999"))
        return item

    def _build_children(self, parent_item, layout):
        for i in range(layout.count()):
            child = layout.itemAt(i).widget()
            if child and not child.property("_designer_hidden"):
                child_item = self._build_item(child)
                parent_item.addChild(child_item)

    def _find_widget_by_id(self, wid):
        for w in self.canvas._canvas_widgets:
            if id(w) == wid:
                return w
            if hasattr(w, "_content_layout"):
                for i in range(w._content_layout.count()):
                    cw = w._content_layout.itemAt(i).widget()
                    if cw and id(cw) == wid:
                        return cw
        return None

    def _snapshot_tree(self):
        """记录树中每个widget的父子关系和顺序 {id(w): (id(parent_container_or_None), index)}"""
        snap = {}
        for ri in range(self.tree.topLevelItemCount()):
            ti = self.tree.topLevelItem(ri)
            wid = ti.data(0, Qt.UserRole)
            if wid: snap[wid] = (None, ri)
            self._snapshot_children(ti, snap)
        return snap

    def _snapshot_children(self, parent_item, snap):
        for ci in range(parent_item.childCount()):
            child = parent_item.child(ci)
            wid = child.data(0, Qt.UserRole)
            parent_wid = parent_item.data(0, Qt.UserRole)
            if wid: snap[wid] = (parent_wid, ci)
            self._snapshot_children(child, snap)

    def _sync_tree_to_canvas(self, old_state):
        """比较树的新旧状态，将变化同步到画布"""
        new_state = self._snapshot_tree()
        for wid, (new_parent_wid, new_idx) in new_state.items():
            old = old_state.get(wid)
            if old is None: continue  # 新控件，忽略
            old_parent_wid, old_idx = old
            if old_parent_wid == new_parent_wid and old_idx == new_idx:
                continue  # 未变化
            w = self._find_widget_by_id(wid)
            if not w: continue
            # 找到新旧父容器
            old_container = self._find_widget_by_id(old_parent_wid) if old_parent_wid else None
            new_container = self._find_widget_by_id(new_parent_wid) if new_parent_wid else None
            if old_container is None and new_container is None:
                # 同是顶层，仅改变在canvas列表中的顺序
                self._reorder_canvas_widget(w, new_idx)
            elif old_container and new_container is None:
                # 从容器移到画布顶层
                self.canvas.history.push(ExtractWidgetCmd(self.canvas, w, old_container, old_idx))
            elif old_container is None and new_container:
                # 从画布顶层移入容器
                self._move_into_container(w, new_container, new_idx)
            elif old_container and new_container:
                # 从一个容器移到另一个容器
                self._move_between_containers(w, old_container, new_container, new_idx)
        self.canvas.widget_modified.emit()
        self.rebuild()

    def _reorder_canvas_widget(self, w, new_idx):
        """调整顶层控件在_canvas_widgets中的顺序"""
        if w not in self.canvas._canvas_widgets: return
        self.canvas._canvas_widgets.remove(w)
        self.canvas._canvas_widgets.insert(min(new_idx, len(self.canvas._canvas_widgets)), w)
        w.raise_()

    def _move_into_container(self, w, container, idx):
        """将画布顶层控件移入容器"""
        if w not in self.canvas._canvas_widgets: return
        old_idx = self.canvas._canvas_widgets.index(w)
        self.canvas.history.push(_ReparentIntoContainerCmd(self.canvas, w, container, old_idx, idx))

    def _move_between_containers(self, w, old_container, new_container, new_idx):
        """在容器间移动控件"""
        old_idx = old_container._content_layout.indexOf(w) if hasattr(old_container, '_content_layout') else 0
        self.canvas.history.push(_ReparentBetweenContainersCmd(self.canvas, w, old_container, new_container, old_idx, new_idx))

    def _on_item_clicked(self, item, col):
        wid = item.data(0, Qt.UserRole)
        w = self._find_widget_by_id(wid)
        if w:
            self.canvas._select(w)
            self.item_selected.emit(w)

    def _show_context_menu(self, pos):
        item = self.tree.itemAt(pos)
        if not item: return
        wid = item.data(0, Qt.UserRole)
        w = self._find_widget_by_id(wid)
        if not w: return

        menu = QMenu(self)
        act_select = menu.addAction("🎯 选中控件")
        menu.addSeparator()

        parent = w.parent()
        in_container = parent and hasattr(parent, "_content_layout")
        if in_container:
            act_up = menu.addAction("⬆️ 上移")
            act_down = menu.addAction("⬇️ 下移")
            menu.addSeparator()
            act_extract = menu.addAction("📤 移出容器")
            menu.addSeparator()

        locked = bool(w.property("_locked"))
        act_lock = menu.addAction("🔓 解锁" if locked else "🔒 锁定")
        hidden = bool(w.property("_designer_hidden"))
        act_hide = menu.addAction("👁️ 显示" if hidden else "👁️‍🗨️ 隐藏")
        menu.addSeparator()
        act_delete = menu.addAction("🗑️ 删除控件")

        chosen = menu.exec(self.tree.mapToGlobal(pos))
        if not chosen: return

        if chosen == act_select:
            self.canvas._select(w)
        elif in_container and chosen == act_up:
            ly = parent._content_layout; idx = ly.indexOf(w)
            if idx > 0:
                self.canvas.history.push(ReorderWidgetCmd(parent, w, idx, idx - 1))
                self.canvas.widget_modified.emit()
        elif in_container and chosen == act_down:
            ly = parent._content_layout; idx = ly.indexOf(w)
            if idx < ly.count() - 1:
                self.canvas.history.push(ReorderWidgetCmd(parent, w, idx, idx + 1))
                self.canvas.widget_modified.emit()
        elif in_container and chosen == act_extract:
            ly = parent._content_layout; idx = ly.indexOf(w)
            self.canvas.history.push(ExtractWidgetCmd(self.canvas, w, parent, idx))
            self.canvas._deselect()
        elif chosen == act_lock:
            self.canvas._toggle_lock()
        elif chosen == act_hide:
            self.canvas._toggle_hide()
        elif chosen == act_delete:
            self.canvas._delete_selected()


# ═══════════════════════════════════════════════════════════════
# P15: 数据模拟器 (DataSimulatorPanel)
# ═══════════════════════════════════════════════════════════════
class DataSimulatorPanel(QWidget):
    """设计时数据模拟器 — 手动输入或自动波动tag值，实时驱动控件"""

    WAVE_MODES = ["手动", "正弦波", "随机游走", "锯齿波"]

    def __init__(self, canvas, parent=None):
        super().__init__(parent)
        self.canvas = canvas
        self.setMinimumWidth(200); self.setMaximumWidth(400)
        layout = QVBoxLayout(self); layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(4)

        self.header = QLabel("<b>🔬 数据模拟器</b>")
        self.header.setStyleSheet("padding:4px 8px; font-size:12px; background:#f0f0f0; border-bottom:1px solid #ddd;")
        layout.addWidget(self.header)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Tag", "当前值", "模式", "参数"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet("QTableWidget{font-size:11px; gridline-color:#eee;} QTableWidget::item{padding:2px;}")
        layout.addWidget(self.table)

        btn_row = QHBoxLayout(); btn_row.setSpacing(4)
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
        """扫描画布上所有带tag的可绑定控件"""
        self._sim_data.clear(); self.table.setRowCount(0); self._busy = True

        def scan(widgets):
            for w in widgets:
                tag = w.property("_tag")
                if tag and (isinstance(w, BINDABLE_WIDGETS) or hasattr(w, 'setValue')):
                    if tag not in self._sim_data:
                        cur_val = 0.0
                        try:
                            if hasattr(w, "value") and callable(w.value):
                                cur_val = float(w.value())
                            elif hasattr(w, "text") and callable(w.text):
                                try: cur_val = float(w.text())
                                except: cur_val = 0.0
                        except: pass
                        self._sim_data[tag] = {"mode": "手动", "value": cur_val, "phase": random.random() * 6.28,
                                               "min": 0.0, "max": 100.0, "period": 5.0, "widget": w}
                if hasattr(w, "_content_layout"):
                    children = [w._content_layout.itemAt(i).widget()
                               for i in range(w._content_layout.count())
                               if w._content_layout.itemAt(i) and w._content_layout.itemAt(i).widget()]
                    scan(children)
        scan(self.canvas._canvas_widgets)

        row = 0
        for tag, sd in self._sim_data.items():
            self.table.insertRow(row)
            ki = QTableWidgetItem(tag); ki.setFlags(ki.flags() & ~Qt.ItemIsEditable)
            ki.setBackground(QColor("#f5f5f5")); self.table.setItem(row, 0, ki)

            vi = QTableWidgetItem(str(sd["value"])[:8]); self.table.setItem(row, 1, vi)

            combo = QComboBox(); combo.addItems(self.WAVE_MODES); combo.setCurrentText(sd["mode"])
            combo.currentTextChanged.connect(lambda text, r=row, t=tag: self._on_mode_changed(t, text))
            self.table.setCellWidget(row, 2, combo)

            param_text = f"min={sd['min']:.0f} max={sd['max']:.0f} T={sd['period']:.1f}s"
            pi = QTableWidgetItem(param_text); pi.setToolTip("格式: min=最小值 max=最大值 T=周期(秒)")
            self.table.setItem(row, 3, pi)
            row += 1

        self._busy = False

    def _on_mode_changed(self, tag, mode):
        if tag in self._sim_data:
            self._sim_data[tag]["mode"] = mode

    def _on_cell_changed(self, row, col):
        if self._busy or col != 3: return
        tag_item = self.table.item(row, 0)
        param_item = self.table.item(row, 1)  # value column
        if not tag_item: return
        tag = tag_item.text()
        if tag not in self._sim_data: return

        # Parse value from column 1
        if col == 1 and param_item:
            try:
                self._sim_data[tag]["value"] = float(param_item.text())
            except ValueError: pass
            return

        # Parse parameters from column 3
        param_text = self.table.item(row, 3).text() if self.table.item(row, 3) else ""
        for part in param_text.split():
            if "=" in part:
                k, v = part.split("=", 1)
                try:
                    if k == "min": self._sim_data[tag]["min"] = float(v)
                    elif k == "max": self._sim_data[tag]["max"] = float(v)
                    elif k in ("T", "t", "period"): self._sim_data[tag]["period"] = float(v)
                except ValueError: pass

    def start(self):
        self._running = True; self._elapsed = 0.0
        self.btn_start.setEnabled(False); self.btn_stop.setEnabled(True)
        self._timer.start(100)  # 10Hz update

    def stop(self):
        self._running = False
        self.btn_start.setEnabled(True); self.btn_stop.setEnabled(False)
        self._timer.stop()

    def _tick(self):
        if not self._running: return
        self._elapsed += 0.1
        dt = 0.1

        for tag, sd in self._sim_data.items():
            mode = sd["mode"]
            if mode == "手动":
                continue  # 保持当前值不变
            elif mode == "正弦波":
                freq = 1.0 / max(0.1, sd["period"])
                amplitude = (sd["max"] - sd["min"]) / 2.0
                center = (sd["max"] + sd["min"]) / 2.0
                sd["value"] = center + amplitude * math.sin(2 * math.pi * freq * self._elapsed + sd["phase"])
            elif mode == "随机游走":
                step = (sd["max"] - sd["min"]) * 0.02 * random.uniform(-1, 1)
                sd["value"] = max(sd["min"], min(sd["max"], sd["value"] + step))
            elif mode == "锯齿波":
                period = max(0.1, sd["period"])
                sd["value"] = sd["min"] + (sd["max"] - sd["min"]) * ((self._elapsed % period) / period)

            self._apply_value(tag, sd["value"])

        # Update table values without triggering cellChanged
        self._busy = True
        for row in range(self.table.rowCount()):
            tag_item = self.table.item(row, 0)
            if not tag_item: continue
            tag = tag_item.text()
            if tag in self._sim_data and self._sim_data[tag]["mode"] != "手动":
                val_str = f"{self._sim_data[tag]['value']:.2f}"
                vi = self.table.item(row, 1)
                if vi: vi.setText(val_str)
        self._busy = False

    def _apply_value(self, tag, value):
        """将模拟值写入画布上的控件"""
        sd = self._sim_data.get(tag)
        if not sd: return
        w = sd.get("widget")
        if not w or not w.isVisible(): return
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


# ═══════════════════════════════════════════════════════════════
# P19: 撤销历史面板 (UndoHistoryPanel)
# ═══════════════════════════════════════════════════════════════
class UndoHistoryPanel(QWidget):
    """撤销历史面板 — 显示操作列表，点击回退到任意步骤"""

    def __init__(self, canvas, parent=None):
        super().__init__(parent)
        self.canvas = canvas
        self.setMinimumWidth(180); self.setMaximumWidth(400)
        layout = QVBoxLayout(self); layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(4)

        self.header = QLabel("<b>📜 撤销历史</b>")
        self.header.setStyleSheet("padding:4px 8px; font-size:12px; background:#f0f0f0; border-bottom:1px solid #ddd;")
        layout.addWidget(self.header)

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("QListWidget{font-size:11px;} QListWidget::item{padding:3px 6px;}")
        layout.addWidget(self.list_widget)

        btn_row = QHBoxLayout(); btn_row.setSpacing(4)
        self.btn_undo_step = QPushButton("↩ 回退一步")
        self.btn_redo_step = QPushButton("↪ 前进一步")
        self.btn_clear_history = QPushButton("清空历史")
        for btn in [self.btn_undo_step, self.btn_redo_step, self.btn_clear_history]:
            btn.setStyleSheet("QPushButton{padding:3px 8px; font-size:11px;}")
            btn_row.addWidget(btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.btn_undo_step.clicked.connect(self.canvas.undo)
        self.btn_redo_step.clicked.connect(self.canvas.redo)
        self.btn_clear_history.clicked.connect(self._clear_history)
        self.list_widget.itemClicked.connect(self._on_item_clicked)

    def refresh(self):
        self.list_widget.clear()
        for cmd in self.canvas.history.undo_stack:
            desc = getattr(cmd, 'description', '操作用') or '操作'
            item = QListWidgetItem(desc)
            item.setData(Qt.UserRole, id(cmd))
            self.list_widget.addItem(item)
        # 高亮当前栈顶（最新的操作）
        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(self.list_widget.count() - 1)
        self.btn_undo_step.setEnabled(self.canvas.history.can_undo())
        self.btn_redo_step.setEnabled(self.canvas.history.can_redo())

    def _on_item_clicked(self, item):
        """点击历史项：回退到该项（该步骤之后的所有操作被撤销）"""
        target_id = item.data(Qt.UserRole)
        # 找到目标命令在撤销栈中的位置
        target_idx = None
        for i, cmd in enumerate(self.canvas.history.undo_stack):
            if id(cmd) == target_id:
                target_idx = i
                break
        if target_idx is None: return
        # 从栈顶向回退，直到目标项成为栈顶
        current_top = len(self.canvas.history.undo_stack) - 1
        steps = current_top - target_idx
        for _ in range(steps):
            self.canvas.undo()
        self.canvas.widget_modified.emit()

    def _clear_history(self):
        self.canvas.history.undo_stack.clear()
        self.canvas.history.redo_stack.clear()
        self.canvas.widget_modified.emit()


# ── 撤销/重做命令系统 ────────────────────────────────────────────
class Command(ABC):
    description = ""
    @abstractmethod
    def execute(self): ...
    @abstractmethod
    def undo(self): ...

class AddWidgetCmd(Command):
    def __init__(self, canvas, display_name, pos):
        self.canvas, self.display_name, self.pos = canvas, display_name, pos; self.widget = None
        self.description = f"添加 {display_name}"
    def execute(self): self.widget = self.canvas._create_widget_internal(self.display_name, self.pos)
    def undo(self):
        if self.widget: self.canvas._remove_widget_internal(self.widget)

class DeleteWidgetCmd(Command):
    def __init__(self, canvas, widget):
        self.canvas, self.widget = canvas, widget
        self.display_name = widget.property("_display_name"); self.geo = widget.geometry()
        self.role = widget.property("role") or "default"; self.obj_name = widget.objectName()
        self.parent_container = None; p = widget.parent()
        if p and hasattr(p, "_content_layout"): self.parent_container = p
        self.locked = bool(widget.property("_locked")); self.hidden = bool(widget.property("_designer_hidden"))
        self.tag = widget.property("_tag") or ""
        self.description = f"删除 {self.obj_name}"
    def execute(self): self.canvas._remove_widget_internal(self.widget)
    def undo(self):
        w = self.canvas._create_widget_internal(self.display_name, self.geo.topLeft())
        if w:
            w.setGeometry(self.geo); w.setProperty("role", self.role); w.setObjectName(self.obj_name)
            w.style().unpolish(w); w.style().polish(w)
            w.setProperty("_locked", self.locked); w.setProperty("_designer_hidden", self.hidden)
            w.setProperty("_tag", self.tag)
            if self.hidden: w.hide()
            if self.parent_container and hasattr(self.parent_container, "_content_layout"):
                self.parent_container._content_layout.removeWidget(w); self.parent_container._content_layout.addWidget(w)
            self.widget = w

class MoveWidgetCmd(Command):
    def __init__(self, canvas, widget, old_pos, new_pos):
        self.canvas, self.widget, self.old_pos, self.new_pos = canvas, widget, old_pos, new_pos
        self.description = f"移动 {widget.objectName()}"
    def execute(self): self.widget.move(self.new_pos)
    def undo(self): self.widget.move(self.old_pos)

class ResizeWidgetCmd(Command):
    def __init__(self, canvas, widget, old_geo, new_geo):
        self.canvas, self.widget, self.old_geo, self.new_geo = canvas, widget, old_geo, new_geo
        self.description = f"缩放 {widget.objectName()}"
    def execute(self): self.widget.setGeometry(self.new_geo)
    def undo(self): self.widget.setGeometry(self.old_geo)

class PropertyChangeCmd(Command):
    def __init__(self, canvas, widget, prop, old_val, new_val):
        self.canvas, self.widget, self.prop = canvas, widget, prop
        self.old_val, self.new_val = old_val, new_val
        self.description = f"修改 {prop}: {old_val} → {new_val}"
    def execute(self): self.canvas._apply_property(self.widget, self.prop, self.new_val)
    def undo(self): self.canvas._apply_property(self.widget, self.prop, self.old_val)

class BatchPropertyChangeCmd(Command):
    def __init__(self, canvas, widgets, prop, old_vals, new_val):
        self.canvas, self.widgets, self.prop = canvas, widgets, prop
        self.old_vals, self.new_val = old_vals, new_val
        self.description = f"批量修改 {prop} ({len(widgets)}个)"
    def execute(self):
        for w in self.widgets: self.canvas._apply_property(w, self.prop, self.new_val)
    def undo(self):
        for w, old_val in zip(self.widgets, self.old_vals): self.canvas._apply_property(w, self.prop, old_val)

class BatchAlignCmd(Command):
    def __init__(self, canvas, widgets, old_geos, new_geos):
        self.canvas, self.widgets = canvas, widgets; self.old_geos, self.new_geos = old_geos, new_geos
        self.description = f"批量移动/对齐 ({len(widgets)}个)"
    def execute(self):
        for w, g in zip(self.widgets, self.new_geos): w.setGeometry(g)
    def undo(self):
        for w, g in zip(self.widgets, self.old_geos): w.setGeometry(g)

class ReorderWidgetCmd(Command):
    def __init__(self, container, widget, old_index, new_index):
        self.container, self.widget = container, widget; self.old_index, self.new_index = old_index, new_index
        self.description = f"调整顺序 {widget.objectName()}"
    def execute(self):
        ly = self.container._content_layout; ly.removeWidget(self.widget)
        ly.insertWidget(self.new_index, self.widget); self.widget.show(); ly.update()
    def undo(self):
        ly = self.container._content_layout; ly.removeWidget(self.widget)
        ly.insertWidget(self.old_index, self.widget); self.widget.show(); ly.update()

class ExtractWidgetCmd(Command):
    def __init__(self, canvas, widget, container, index_in_layout):
        self.canvas, self.widget, self.container = canvas, widget, container
        self.index_in_layout = index_in_layout; self.extract_pos = None
        self.description = f"移出容器 {widget.objectName()}"
    def execute(self):
        ly = self.container._content_layout; ly.removeWidget(self.widget)
        cr = self.container.geometry(); self.extract_pos = QPoint(cr.x()+cr.width()+10, cr.y())
        self.widget.setParent(self.canvas); self.widget.move(self.extract_pos)
        self.widget.resize(self.widget.sizeHint()); self.widget.show()
        self.canvas._install_filter_recursive(self.widget); self.canvas.widget_modified.emit()
    def undo(self):
        self.widget.setParent(self.container)
        self.container._content_layout.insertWidget(self.index_in_layout, self.widget)
        self.widget.show(); self.container._content_layout.update(); self.canvas.widget_modified.emit()

class InsertTemplateCmd(Command):
    def __init__(self, canvas, template_widgets, base_pos):
        self.canvas, self.template_widgets, self.base_pos = canvas, template_widgets, base_pos; self.created_widgets = []
        self.description = "插入工业模板"
    def execute(self):
        self.created_widgets = []
        for tw in self.template_widgets:
            pos = QPoint(self.base_pos.x() + tw["x"], self.base_pos.y() + tw["y"])
            w = self.canvas._create_widget_internal(tw.get("type") or tw.get("display_name"), pos, center=False)
            if not w: continue
            w.resize(tw.get("w", 100), tw.get("h", 30))
            if "text" in tw and hasattr(w, "setText"): w.setText(tw["text"])
            if "title" in tw and hasattr(w, "setTitle"): w.setTitle(tw["title"])
            if "styleSheet" in tw: w.setStyleSheet(tw["styleSheet"])
            if "tag" in tw: w.setProperty("_tag", tw["tag"])
            if "role" in tw: w.setProperty("role", tw["role"]); w.style().unpolish(w); w.style().polish(w)
            if "objectName" in tw: w.setObjectName(tw["objectName"])
            if tw.get("anchor_left"): w.setProperty("_anchor_left", True)
            if tw.get("anchor_right"): w.setProperty("_anchor_right", True)
            if tw.get("anchor_top"): w.setProperty("_anchor_top", True)
            if tw.get("anchor_bottom"): w.setProperty("_anchor_bottom", True)
            self.created_widgets.append(w)
        if self.created_widgets: self.canvas._select(self.created_widgets[-1]); self.canvas.widget_modified.emit()
    def undo(self):
        for w in reversed(self.created_widgets): self.canvas._remove_widget_internal(w)
        self.created_widgets = []; self.canvas.widget_modified.emit()


class _ReparentIntoContainerCmd(Command):
    """将画布顶层控件移入容器"""
    def __init__(self, canvas, widget, container, canvas_index, layout_index):
        self.canvas = canvas; self.widget = widget; self.container = container
        self.canvas_index = canvas_index; self.layout_index = layout_index
        self.description = f"移入容器 {widget.objectName()}"
    def execute(self):
        if self.widget in self.canvas._canvas_widgets:
            self.canvas._canvas_widgets.remove(self.widget)
        self.widget.setParent(self.container)
        ly = self.container._content_layout
        ly.insertWidget(min(self.layout_index, ly.count()), self.widget)
        self.widget.show(); ly.update()
    def undo(self):
        ly = self.container._content_layout; ly.removeWidget(self.widget)
        self.widget.setParent(self.canvas)
        self.canvas._canvas_widgets.insert(self.canvas_index, self.widget)
        self.widget.show(); self.canvas._install_filter_recursive(self.widget)

class _ReparentBetweenContainersCmd(Command):
    """将控件从一个容器移到另一个容器"""
    def __init__(self, canvas, widget, old_container, new_container, old_idx, new_idx):
        self.canvas = canvas; self.widget = widget
        self.old_container = old_container; self.new_container = new_container
        self.old_idx = old_idx; self.new_idx = new_idx
        self.description = f"容器间移动 {widget.objectName()}"
    def execute(self):
        old_ly = self.old_container._content_layout; old_ly.removeWidget(self.widget)
        self.widget.setParent(self.new_container)
        new_ly = self.new_container._content_layout
        new_ly.insertWidget(min(self.new_idx, new_ly.count()), self.widget)
        self.widget.show(); new_ly.update()
    def undo(self):
        new_ly = self.new_container._content_layout; new_ly.removeWidget(self.widget)
        self.widget.setParent(self.old_container)
        old_ly = self.old_container._content_layout
        old_ly.insertWidget(self.old_idx, self.widget)
        self.widget.show(); old_ly.update()

class HistoryManager:
    def __init__(self, max_size=100):
        self.undo_stack, self.redo_stack, self.max_size = [], [], max_size
    def push(self, cmd):
        cmd.execute(); self.undo_stack.append(cmd)
        if len(self.undo_stack) > self.max_size: self.undo_stack.pop(0)
        self.redo_stack.clear()
    def undo(self):
        if self.undo_stack: cmd = self.undo_stack.pop(); cmd.undo(); self.redo_stack.append(cmd)
    def redo(self):
        if self.redo_stack: cmd = self.redo_stack.pop(); cmd.execute(); self.undo_stack.append(cmd)
    def can_undo(self): return bool(self.undo_stack)
    def can_redo(self): return bool(self.redo_stack)


# ── 代码生成器 ───────────────────────────────────────────────────
class CodeGenerator:
    @staticmethod
    def generate(canvas, as_ui_class=False, qss_filename="style.qss") -> str:
        if as_ui_class: return CodeGenerator._generate_ui_class(canvas, qss_filename=qss_filename)
        canvas._save_current_page()  # 确保页面控件列表是最新的
        multi_page = canvas.page_count() > 1
        lines = ["import sys, os, base64","os.environ['QT_OPENGL'] = 'software'","from PySide6.QtWidgets import (","    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,","    QPushButton, QLabel, QLineEdit, QComboBox, QGroupBox, QFrame,","    QCheckBox, QRadioButton, QSpinBox, QDoubleSpinBox, QSlider,","    QProgressBar, QTextEdit, QTextBrowser, QDateEdit, QTimeEdit,","    QTabWidget, QScrollArea, QToolButton, QDialogButtonBox,","    QCalendarWidget, QDial, QLCDNumber, QCommandLinkButton,","    QStackedWidget, QListWidget, QTreeWidget, QTableWidget, QSplitter,","    QSizePolicy, QSpacerItem,",")","",""]

        # 检测画布上的自定义控件并生成import
        custom_imports = CodeGenerator._collect_custom_imports(canvas)
        for imp in custom_imports:
            lines.insert(0, imp)
        if custom_imports:
            lines.insert(0, "")
        tag_bindings = CodeGenerator._collect_tag_bindings(canvas)
        if tag_bindings:
            lines.extend(CodeGenerator._generate_data_binder(tag_bindings)); lines.append("")
        _resize_fn = "setFixedSize" if getattr(canvas, "_fixed_canvas", False) else "resize"
        lines.extend(["class GeneratedWindow(QMainWindow):","    def __init__(self):","        super().__init__()",'        self.setWindowTitle("Generated Application")',f"        self.{_resize_fn}({canvas.design_width}, {canvas.design_height})","",
            f"        qss_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '{qss_filename}')","        if os.path.exists(qss_path):","            with open(qss_path, 'r', encoding='utf-8') as f:","                QApplication.instance().setStyleSheet(f.read())",""])
        obj_name_map = {}
        if multi_page:
            CodeGenerator._emit_multipage(canvas, lines, tag_bindings, obj_name_map)
        else:
            lines += ["        self.central_widget = QWidget()","        self.setCentralWidget(self.central_widget)",""]
            used = {}
            for w in canvas._canvas_widgets:
                if w.property("_designer_hidden"): continue
                CodeGenerator._emit(w, lines, used, "self.central_widget", "        ", obj_name_map)
            if tag_bindings:
                lines.append(""); lines.append("        # 初始化数据绑定管理器")
                lines.append("        self.data_binder = DataBinder(self)")
                lines.append("        # TODO: 在此处启动您的通信线程，调用 self.data_binder.update_tag(tag, value) 刷新UI")

        # ✅ 修复: 去掉信号名中的括号，避免 TypeError
        if canvas._signal_connections:
            lines.append("")
            lines.append("        # 信号/槽连接")
            for conn in canvas._signal_connections:
                sig = conn["signal"].split("(")[0]
                # 使用 obj_name_map 将 objectName 转换为实际生成的变量名
                src_var = obj_name_map.get(conn["source"], conn["source"])
                lines.append(f"        self.{src_var}.{sig}.connect(self.{conn['slot']})")
            lines.append("")
            generated_slots = set()
            for conn in canvas._signal_connections:
                slot = conn["slot"]
                if slot not in generated_slots:
                    generated_slots.add(slot)
                    callback_code = (canvas._callback_code or {}).get(slot, "").strip()
                    if callback_code:
                        # 用户自定义回调代码 — 替换 objectName 为实际变量名，再缩进 4 空格
                        if obj_name_map:
                            # 按 objectName 长度降序替换，避免部分匹配
                            for obj_name, var_name in sorted(obj_name_map.items(), key=lambda x: -len(x[0])):
                                callback_code = callback_code.replace(f"self.{obj_name}", f"self.{var_name}")
                        lines.append("")
                        for cb_line in callback_code.split("\n"):
                            lines.append(f"    {cb_line}")
                        lines.append("")
                    else:
                        # 自动生成 stub
                        lines.append(f"    def {slot}(self):")
                        lines.append(f"        # TODO: 实现 {slot}")
                        lines.append("        pass")
                        lines.append("")

        anchor_widgets = CodeGenerator._collect_anchor_widgets(canvas)
        if anchor_widgets:
            lines.append(""); lines.extend(CodeGenerator._generate_resize_event(anchor_widgets, used, canvas))
        lines += ["",'if __name__ == "__main__":',"    app = QApplication(sys.argv)","    window = GeneratedWindow()","    window.show()","    sys.exit(app.exec())"]
        return "\n".join(lines)
    @staticmethod
    def _generate_ui_class(canvas, qss_filename="style.qss") -> str:
        canvas._save_current_page()
        lines = ["import sys, os, base64","os.environ['QT_OPENGL'] = 'software'","from PySide6.QtWidgets import (","    QWidget, QVBoxLayout, QHBoxLayout,","    QPushButton, QLabel, QLineEdit, QComboBox, QGroupBox, QFrame,","    QCheckBox, QRadioButton, QSpinBox, QDoubleSpinBox, QSlider,","    QProgressBar, QTextEdit, QTextBrowser, QDateEdit, QTimeEdit,","    QTabWidget, QScrollArea, QToolButton, QDialogButtonBox,","    QCalendarWidget, QDial, QLCDNumber, QCommandLinkButton,","    QStackedWidget, QListWidget, QTreeWidget, QTableWidget, QSplitter,","    QSizePolicy,",")","",""]

        custom_imports = CodeGenerator._collect_custom_imports(canvas)
        for imp in custom_imports:
            lines.insert(0, imp)
        if custom_imports:
            lines.insert(0, "")

        tag_bindings = CodeGenerator._collect_tag_bindings(canvas)
        if tag_bindings:
            lines.extend(CodeGenerator._generate_data_binder(tag_bindings)); lines.append("")
        _resize_fn = "setFixedSize" if getattr(canvas, "_fixed_canvas", False) else "resize"
        lines.extend(["class Ui_MainWindow(object):","    def setupUi(self, MainWindow):","        MainWindow.setWindowTitle('Generated Application')",f"        MainWindow.{_resize_fn}({canvas.design_width}, {canvas.design_height})","",
            "        import os",f"        qss_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '{qss_filename}')","        if os.path.exists(qss_path):","            with open(qss_path, 'r', encoding='utf-8') as f:","                MainWindow.setStyleSheet(f.read())","",
            "        self.central_widget = QWidget()","        MainWindow.setCentralWidget(self.central_widget)",""])
        obj_name_map = {}
        used = {}
        for w in canvas._canvas_widgets:
            if w.property("_designer_hidden"): continue
            CodeGenerator._emit(w, lines, used, "self.central_widget", "        ", obj_name_map)
        if tag_bindings: lines.append(""); lines.append("        self.data_binder = DataBinder(self)")
        # ✅ 修复: Ui类模式同样去掉信号名括号
        if canvas._signal_connections:
            lines.append("")
            for conn in canvas._signal_connections:
                sig = conn["signal"].split("(")[0]
                src_var = obj_name_map.get(conn["source"], conn["source"])
                lines.append(f"        self.{src_var}.{sig}.connect(self.{conn['slot']})")
        lines += ["","    def retranslateUi(self, MainWindow):","        pass",""]
        return "\n".join(lines)

    @staticmethod
    def _emit_multipage(canvas, lines, tag_bindings, obj_name_map=None):
        """多页面应用：生成 QStackedWidget + 侧边栏导航"""
        pages = canvas._pages
        page_names = [p["name"] for p in pages]
        btn_width = 120
        lines += [
            "        # ── 多页面布局 ──",
            "        self.central_widget = QWidget()",
            "        self.setCentralWidget(self.central_widget)",
            "        main_layout = QHBoxLayout(self.central_widget)",
            "        main_layout.setContentsMargins(0, 0, 0, 0)",
            "        main_layout.setSpacing(0)",
            "",
            f"        # 侧边导航栏",
            "        self.nav_widget = QWidget()",
            f"        self.nav_widget.setFixedWidth({btn_width + 20})",
            "        self.nav_widget.setStyleSheet('QWidget{background:#2c3e50;}')",
            "        nav_layout = QVBoxLayout(self.nav_widget)",
            "        nav_layout.setContentsMargins(4, 8, 4, 8)",
            "        nav_layout.setSpacing(4)",
            "",
            "        self.nav_buttons = []",
            f"        self.stack = QStackedWidget()",
            "",
        ]
        for i, pname in enumerate(page_names):
            safe_name = _sanitize(pname) or f"page{i}"
            lines += [
                f"        btn_{safe_name} = QPushButton('{_esc(pname)}')",
                f"        btn_{safe_name}.setFixedHeight(36)",
                "        btn_{safe_name}.setStyleSheet('QPushButton{{color:#ecf0f1;background:transparent;border:none;text-align:left;padding:8px 12px;font-size:12px;border-radius:4px;}}"
                "QPushButton:hover{{background:#34495e;}}QPushButton:checked{{background:#4A90D9;font-weight:bold;}}')",
                f"        btn_{safe_name}.setCheckable(True)",
                f"        btn_{safe_name}.clicked.connect(lambda checked, idx={i}: self.stack.setCurrentIndex(idx))",
                f"        nav_layout.addWidget(btn_{safe_name})",
                f"        self.nav_buttons.append(btn_{safe_name})",
                f"        # ── 页面: {pname} ──",
                f"        page_{safe_name} = QWidget()",
                f"        self.stack.addWidget(page_{safe_name})",
                "",
            ]
        lines += [
            "        nav_layout.addStretch()",
            "        main_layout.addWidget(self.nav_widget)",
            "        main_layout.addWidget(self.stack)",
            "        self.nav_buttons[0].setChecked(True) if self.nav_buttons else None",
            "",
        ]
        # 每个页面的控件
        for i, p in enumerate(pages):
            safe_name = _sanitize(p["name"]) or f"page{i}"
            used = {}
            for w in p["widgets"]:
                if w.property("_designer_hidden"): continue
                CodeGenerator._emit(w, lines, used, f"page_{safe_name}", "        ", obj_name_map)
        # 数据绑定
        if tag_bindings:
            lines.append(""); lines.append("        # 初始化数据绑定管理器")
            lines.append("        self.data_binder = DataBinder(self)")
            lines.append("        # TODO: 启动通信线程，调用 self.data_binder.update_tag(tag, value) 刷新UI")

    def _collect_custom_imports(canvas):
        """检测画布上实际使用的自定义控件，按文件合并import"""
        custom_cls_to_file = {}
        for display_name, cls, kwargs, filepath in CUSTOM_WIDGETS:
            custom_cls_to_file[cls] = filepath

        cls_to_file = {}
        svg_needed = False
        def scan(widgets):
            nonlocal svg_needed
            for w in widgets:
                if w.property("_designer_hidden"): continue
                cls = type(w)
                mod = cls.__module__
                # SVG 图元
                if hasattr(w, '_renderer') and hasattr(w, '_svg_name'):
                    svg_needed = True
                # 优先从 CUSTOM_WIDGETS 查找
                if cls in custom_cls_to_file:
                    cls_to_file[cls] = custom_cls_to_file[cls]
                # 从控件存储的来源文件查找
                elif w.property("_custom_source"):
                    src = w.property("_custom_source")
                    if os.path.isfile(src):
                        cls_to_file[cls] = src
                # 通用 fallback：检查类是否来自可导入的外部模块
                elif cls.__name__ not in cls_to_file and mod not in ('__main__', 'builtins') and not mod.startswith('PySide6'):
                    for display_name, ccls, kwargs, fp in CUSTOM_WIDGETS:
                        if ccls.__name__ == cls.__name__:
                            cls_to_file[cls] = fp; break
                if hasattr(w, "_content_layout"):
                    children = [w._content_layout.itemAt(i).widget()
                               for i in range(w._content_layout.count())
                               if w._content_layout.itemAt(i) and w._content_layout.itemAt(i).widget()]
                    scan(children)
        # 扫描当前页和所有页面
        scan(canvas._canvas_widgets)
        for p in canvas._pages:
            if p["widgets"] is not canvas._canvas_widgets:
                scan(p["widgets"])

        file_to_classes = {}
        for cls, fp in cls_to_file.items():
            mod_name = os.path.splitext(os.path.basename(fp))[0]
            file_to_classes.setdefault(mod_name, []).append(cls.__name__)

        imports = []
        if svg_needed:
            imports.append("from svg_import import SvgWidget")
        for mod_name, class_names in file_to_classes.items():
            imports.append(f"from {mod_name} import {', '.join(sorted(class_names))}")
        return imports

    @staticmethod
    def _collect_tag_bindings(canvas):
        bindings = []
        def scan(widgets):
            for w in widgets:
                tag = w.property("_tag")
                if tag and (isinstance(w, BINDABLE_WIDGETS) or hasattr(w, 'setValue')):
                    bindings.append((tag, w.objectName(), type(w).__name__))
                if hasattr(w, "_content_layout"):
                    ly = w._content_layout
                    children = [ly.itemAt(i).widget() for i in range(ly.count()) if ly.itemAt(i) and ly.itemAt(i).widget()]
                    scan(children)
        scan(canvas._canvas_widgets); return bindings

    @staticmethod
    def _generate_data_binder(bindings):
        lines = ["class DataBinder:",'    """',"    数据绑定管理器 - 由设计器自动生成","    外部通信线程通过 update_tag(tag, value) 统一刷新UI",'    """',
                 "    def __init__(self, ui):","        self.ui = ui","        self._data = {}","",
                 "    def update_tag(self, tag: str, value):","        self._data[tag] = value"]
        for tag, var_name, cls_name in bindings:
            safe_tag = tag.replace("'", "\\'")
            if cls_name in ("QLabel", "QGroupBox", "QLineEdit"): lines.append(f"        if tag == '{safe_tag}': self.ui.{var_name}.setText(str(value))")
            elif cls_name == "QLCDNumber": lines.append(f"        if tag == '{safe_tag}': self.ui.{var_name}.display(float(value) if value else 0)")
            elif cls_name in ("QProgressBar", "QSlider"): lines.append(f"        if tag == '{safe_tag}': self.ui.{var_name}.setValue(int(float(value)))")
            elif cls_name in ("QSpinBox", "QDoubleSpinBox"): lines.append(f"        if tag == '{safe_tag}': self.ui.{var_name}.setValue(float(value))")
            elif cls_name in ("QCheckBox", "QRadioButton"): lines.append(f"        if tag == '{safe_tag}': self.ui.{var_name}.setChecked(bool(value))")
            else: lines.append(f"        if tag == '{safe_tag}': self.ui.{var_name}.setValue(float(value))  # 通用: 自定义控件")
        lines.extend(["","    def get_tag(self, tag: str):","        return self._data.get(tag)"]); return lines

    @staticmethod
    def _collect_anchor_widgets(canvas):
        result = []
        for w in canvas._canvas_widgets:
            if w.property("_designer_hidden"): continue
            parent = w.parent()
            if parent and hasattr(parent, "_content_layout"): continue
            al, ar, at, ab = bool(w.property("_anchor_left")), bool(w.property("_anchor_right")), bool(w.property("_anchor_top")), bool(w.property("_anchor_bottom"))
            if al or ar or at or ab: result.append((w.objectName(), w.geometry(), al, ar, at, ab))
        return result

    @staticmethod
    def _generate_resize_event(anchor_widgets, used, canvas):
        lines = [f"    # 设计基准尺寸: {canvas.design_width}x{canvas.design_height}","    def resizeEvent(self, event):","        super().resizeEvent(event)","        w = self.central_widget.width()","        h = self.central_widget.height()",f"        sx = w / {canvas.design_width}",f"        sy = h / {canvas.design_height}"]
        dw, dh = canvas.design_width, canvas.design_height
        for var_name, geo, al, ar, at, ab in anchor_widgets:
            x, y, gw, gh = geo.x(), geo.y(), geo.width(), geo.height()
            if al and ar: lines.append(f"        self.{var_name}.setGeometry(int({x} * sx), int({y} * sy), w - int({x} * sx) - int({(dw - x - gw)} * sx), int({gh} * sy))")
            elif al: lines.append(f"        self.{var_name}.move(int({x} * sx), int({y} * sy))")
            elif ar: lines.append(f"        self.{var_name}.move(w - int({dw - x - gw} * sx) - {gw}, int({y} * sy))")
            if at and ab and not (al and ar): lines.append(f"        self.{var_name}.setGeometry(self.{var_name}.x(), int({y} * sy), self.{var_name}.width(), h - int({y} * sy) - int({(dh - y - gh)} * sy))")
            elif at and not (al or ar): lines.append(f"        self.{var_name}.move(self.{var_name}.x(), int({y} * sy))")
            elif ab and not (al or ar): lines.append(f"        self.{var_name}.move(self.{var_name}.x(), h - int({dh - y - gh} * sy) - {gh})")
        return lines

    @staticmethod
    def _var(widget, used):
        display_name = widget.property("_display_name") or ""
        prefix = NAME_TO_PREFIX.get(display_name, _sanitize(type(widget).__name__))
        obj_name = widget.objectName(); default_pattern = f"{prefix}_\\d+"
        base = _sanitize(obj_name) if obj_name and not re.match(default_pattern, obj_name) else prefix
        if base not in used: used[base] = 0; return base
        used[base] += 1; return f"{base}_{used[base]}"

    @staticmethod
    def _emit(w, lines, used, parent_ref, indent, obj_name_map=None):
        var = CodeGenerator._var(w, used)
        if obj_name_map is not None:
            obj_name = w.objectName()
            if obj_name:
                obj_name_map[obj_name] = var
        g = w.geometry(); cls = type(w).__name__
        if hasattr(w, "_content_layout"):
            ly_cls = type(w._content_layout).__name__; ly_var = f"ly_{var}"
            lines.append(f"{indent}# ── Container: {var} ──"); lines.append(f"{indent}self.{var} = QFrame({parent_ref})")
            lines.append(f"{indent}self.{var}.setGeometry({g.x()}, {g.y()}, {g.width()}, {g.height()})")
            ss = w.styleSheet()
            if ss: lines.append(f'{indent}self.{var}.setStyleSheet("{_esc(ss)}")')
            lines.append(f"{indent}self.{ly_var} = {ly_cls}(self.{var})"); lines.append(f"{indent}self.{ly_var}.setContentsMargins(8, 8, 8, 8)")
            lines.append(f"{indent}self.{ly_var}.setSpacing(4)"); lines.append("")
            for i in range(w._content_layout.count()):
                cw = w._content_layout.itemAt(i).widget()
                if cw and not cw.property("_designer_hidden"): CodeGenerator._emit_child(cw, lines, used, f"self.{ly_var}", indent, obj_name_map)
            return
        ctor_args, post_init = "", []
        if isinstance(w, (QPushButton, QCheckBox, QRadioButton, QCommandLinkButton)):
            if hasattr(w,"text") and w.text(): ctor_args = f'"{_esc(w.text())}"'
        elif isinstance(w, QToolButton):
            if hasattr(w,"text") and w.text(): post_init.append(f'self.{var}.setText("{_esc(w.text())}")')
        elif isinstance(w, QLabel):
            ctor_args = f'"{_esc(w.text())}"'
            if w.openExternalLinks(): post_init.append(f"self.{var}.setOpenExternalLinks(True)")
        elif isinstance(w, QGroupBox): ctor_args = f'"{_esc(w.title())}"'
        elif isinstance(w, QLineEdit) and w.placeholderText(): post_init.append(f'self.{var}.setPlaceholderText("{_esc(w.placeholderText())}")')
        elif isinstance(w, QComboBox):
            items = [w.itemText(i) for i in range(w.count())]
            if items:
                escaped_items = ", ".join([f'"{_esc(i)}"' for i in items])
                post_init.append(f"self.{var}.addItems([{escaped_items}])")
        elif isinstance(w, QSpinBox): post_init += [f"self.{var}.setRange({w.minimum()}, {w.maximum()})", f"self.{var}.setValue({w.value()})"]
        elif isinstance(w, QDoubleSpinBox): post_init += [f"self.{var}.setRange({w.minimum()}, {w.maximum()})", f"self.{var}.setDecimals({w.decimals()})", f"self.{var}.setValue({w.value()})"]
        elif isinstance(w, QSlider): ctor_args = "Qt.Horizontal" if w.orientation()==Qt.Horizontal else "Qt.Vertical"; post_init.append(f"self.{var}.setValue({w.value()})")
        elif isinstance(w, QProgressBar): post_init.append(f"self.{var}.setValue({w.value()})")
        elif isinstance(w, QLCDNumber): post_init.append(f"self.{var}.display({w.intValue()})")
        elif isinstance(w, QDial): post_init += [f"self.{var}.setRange({w.minimum()}, {w.maximum()})", f"self.{var}.setValue({w.value()})"]
        elif isinstance(w, QWTextEdit) and w.placeholderText(): post_init.append(f'self.{var}.setPlaceholderText("{_esc(w.placeholderText())}")')
        elif isinstance(w, QTreeWidget): post_init += [f"self.{var}.setHeaderLabels(['列1', '列2'])", f"self.{var}.setColumnCount(2)"]
        elif isinstance(w, QTableWidget): post_init += [f"self.{var}.setRowCount(3)", f"self.{var}.setColumnCount(3)"]
        elif isinstance(w, QSplitter): ctor_args = "Qt.Horizontal" if w.orientation()==Qt.Horizontal else "Qt.Vertical"
        # 自定义控件：如果支持实时数据推送，自动启动 demo
        if hasattr(w, '_demo_timer') and hasattr(w, 'start'):
            pass  # start() 在生成代码中由用户自行决定，不自动调用
        elif cls not in ("QPushButton","QToolButton","QLabel","QGroupBox","QLineEdit","QComboBox","QCheckBox","QRadioButton","QSpinBox","QDoubleSpinBox","QSlider","QProgressBar","QLCDNumber","QDial","QCommandLinkButton","QFrame","QSplitter"):
            # SVG 图元：用基类 + base64 内联数据
            if hasattr(w, '_renderer') and hasattr(w, '_svg_name'):
                lines.append(f"{indent}self.{var} = SvgWidget({parent_ref})")
                lines.append(f"{indent}self.{var}.setGeometry({g.x()}, {g.y()}, {g.width()}, {g.height()})")
                svg_source = ''
                try:
                    svg_source = getattr(w, '_svg_source', '') or ''
                except Exception:
                    pass
                if svg_source:
                    b64 = base64.b64encode(svg_source.encode()).decode()
                    lines.append(f'{indent}self.{var}.load_svg_from_data(base64.b64decode("{b64}").decode(), "{w._svg_name}")')
            else:
                lines.append(f"{indent}self.{var} = {cls}({parent_ref})"); lines.append(f"{indent}self.{var}.setGeometry({g.x()}, {g.y()}, {g.width()}, {g.height()})")
            role = w.property("role") or "default"
            if role != "default": lines.append(f'{indent}self.{var}.setProperty("role", "{role}")')
            obj_name = w.objectName()
            if obj_name: lines.append(f'{indent}self.{var}.setObjectName("{obj_name}")')
            ss = w.styleSheet()
            if ss:
                ss_esc = _esc(ss).replace('\n', '\\n').replace('\r', '')
                lines.append(f'{indent}self.{var}.setStyleSheet("{ss_esc}")')
            lines.append(""); return
        lines.append(f"{indent}self.{var} = {cls}({ctor_args}, {parent_ref})" if ctor_args else f"{indent}self.{var} = {cls}({parent_ref})")
        lines.append(f"{indent}self.{var}.setGeometry({g.x()}, {g.y()}, {g.width()}, {g.height()})")
        role = w.property("role") or "default"
        if role != "default": lines.append(f'{indent}self.{var}.setProperty("role", "{role}")')
        obj_name = w.objectName(); display_name = w.property("_display_name") or ""
        default_prefix = NAME_TO_PREFIX.get(display_name, _sanitize(cls))
        if obj_name and not re.match(f"{default_prefix}_\\d+", obj_name): lines.append(f'{indent}self.{var}.setObjectName("{obj_name}")')
        ss = w.styleSheet()
        if ss:
            ss_esc = _esc(ss).replace('\n', '\\n').replace('\r', '')
            lines.append(f'{indent}self.{var}.setStyleSheet("{ss_esc}")')
        for pi in post_init: lines.append(f"{indent}{pi}")
        lines.append("")

    @staticmethod
    def _emit_child(w, lines, used, layout_ref, indent, obj_name_map=None):
        var = CodeGenerator._var(w, used)
        if obj_name_map is not None:
            obj_name = w.objectName()
            if obj_name:
                obj_name_map[obj_name] = var
        cls = type(w).__name__; ctor_args, post_init = "", []
        if isinstance(w, (QPushButton, QCheckBox, QRadioButton, QLabel, QCommandLinkButton)):
            if hasattr(w,"text") and w.text(): ctor_args = f'"{_esc(w.text())}"'
        elif isinstance(w, QToolButton):
            if hasattr(w,"text") and w.text(): post_init.append(f'self.{var}.setText("{_esc(w.text())}")')
        elif isinstance(w, QGroupBox): ctor_args = f'"{_esc(w.title())}"'
        elif isinstance(w, QLineEdit) and w.placeholderText(): post_init.append(f'self.{var}.setPlaceholderText("{_esc(w.placeholderText())}")')
        elif isinstance(w, QLabel) and w.openExternalLinks(): post_init.append(f"self.{var}.setOpenExternalLinks(True)")
        elif isinstance(w, QTreeWidget): post_init += [f"self.{var}.setHeaderLabels(['列1', '列2'])", f"self.{var}.setColumnCount(2)"]
        elif isinstance(w, QTableWidget): post_init += [f"self.{var}.setRowCount(3)", f"self.{var}.setColumnCount(3)"]
        elif isinstance(w, QSplitter): ctor_args = "Qt.Horizontal" if w.orientation()==Qt.Horizontal else "Qt.Vertical"
        if hasattr(w, '_demo_timer') and hasattr(w, 'start'):
            pass  # start() 在生成代码中由用户自行决定，不自动调用
        lines.append(f"{indent}self.{var} = {cls}({ctor_args})" if ctor_args else f"{indent}self.{var} = {cls}()")
        role = w.property("role") or "default"
        if role != "default": lines.append(f'{indent}self.{var}.setProperty("role", "{role}")')
        sp = w.sizePolicy(); h_pol = _policy_to_str(sp.horizontalPolicy()); v_pol = _policy_to_str(sp.verticalPolicy())
        if h_pol != "Preferred" or v_pol != "Preferred": lines.append(f'{indent}self.{var}.setSizePolicy(QSizePolicy.{h_pol}, QSizePolicy.{v_pol})')
        if w.minimumWidth() > 0 or w.minimumHeight() > 0: lines.append(f'{indent}self.{var}.setMinimumSize({w.minimumWidth()}, {w.minimumHeight()})')
        if w.maximumWidth() < 16777215 or w.maximumHeight() < 16777215: lines.append(f'{indent}self.{var}.setMaximumSize({w.maximumWidth()}, {w.maximumHeight()})')
        ss = w.styleSheet()
        if ss:
            ss_esc = _esc(ss).replace('\n', '\\n').replace('\r', '')
            lines.append(f'{indent}self.{var}.setStyleSheet("{ss_esc}")')
        lines.append(f"{indent}{layout_ref}.addWidget(self.{var})")
        for pi in post_init: lines.append(f"{indent}{pi}")
        lines.append("")


class _Placeholder(QLabel): pass

class WidgetToolbox(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self); layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(0)

        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍 搜索控件...")
        self.search.setClearButtonEnabled(True)
        self.search.setStyleSheet("QLineEdit{padding:4px 8px;border:1px solid #ccc;border-radius:4px;margin:2px 4px;font-size:12px;}")
        self.search.textChanged.connect(self._filter)
        layout.addWidget(self.search)

        self.list_widget = QListWidget()
        self.list_widget.setDragEnabled(True)
        self.list_widget.setSelectionMode(QAbstractItemView.NoSelection)
        self.list_widget.setStyleSheet("QListWidget{background:#e8e8e8;border:1px solid #ccc;font-size:12px;} QListWidget::item{padding:5px 8px;} QListWidget::item:hover{background:#d0d8e8;}")
        self.list_widget.setMaximumWidth(200); self.list_widget.setMinimumWidth(150)
        layout.addWidget(self.list_widget)

        self._all_items = []  # (display_text, is_header, category_name, widget_name)
        self.list_widget.viewport().installEventFilter(self)
        self.populate()

    def setMaximumWidth(self, w): self.list_widget.setMaximumWidth(w)
    def setMinimumWidth(self, w): self.list_widget.setMinimumWidth(w)

    def eventFilter(self, obj, event):
        if obj is self.list_widget.viewport() and event.type() == QEvent.MouseMove:
            item = self.list_widget.itemAt(event.position().toPoint())
            if item:
                wt = item.data(Qt.UserRole)
                if wt:
                    drag = QDrag(self); mime = QMimeData()
                    mime.setData(MIME_TYPE, wt.encode())
                    drag.setMimeData(mime); drag.exec(Qt.CopyAction)
        return super().eventFilter(obj, event)

    def populate(self):
        self._all_items = []
        for cat, items in get_all_categories():
            self._all_items.append((f"── {cat} ──", True, cat, None))
            for name, _, _ in items:
                self._all_items.append((f"  {name}", False, cat, name))
        self._rebuild_list()

    def _rebuild_list(self, filter_text=""):
        self.list_widget.clear()
        ft = filter_text.lower().strip()
        visible_cat = None
        for text, is_header, cat, name in self._all_items:
            if is_header:
                visible_cat = None
                # Show header only if any child will be visible
                continue
            if ft:
                if ft in text.lower() or ft in (name or "").lower() or ft in cat.lower():
                    if visible_cat != cat:
                        header_text = f"── {cat} ──"
                        h = QListWidgetItem(header_text); h.setFlags(Qt.NoItemFlags)
                        h.setForeground(QColor("#888"))
                        f = QFont(); f.setBold(True); f.setPointSize(10); h.setFont(f)
                        self.list_widget.addItem(h)
                        visible_cat = cat
                    item = QListWidgetItem(text); item.setData(Qt.UserRole, name); self.list_widget.addItem(item)
            else:
                if visible_cat != cat:
                    header_text = f"── {cat} ──"
                    h = QListWidgetItem(header_text); h.setFlags(Qt.NoItemFlags)
                    h.setForeground(QColor("#888"))
                    f = QFont(); f.setBold(True); f.setPointSize(10); h.setFont(f)
                    self.list_widget.addItem(h)
                    visible_cat = cat
                item = QListWidgetItem(text); item.setData(Qt.UserRole, name); self.list_widget.addItem(item)

    def _filter(self, text):
        self._rebuild_list(text)

    def mouseMoveEvent(self, event):
        item = self.list_widget.itemAt(self.list_widget.viewport().mapFrom(self, event.position().toPoint()))
        if not item: return
        wt = item.data(Qt.UserRole)
        if not wt: return
        drag = QDrag(self); mime = QMimeData(); mime.setData(MIME_TYPE, wt.encode()); drag.setMimeData(mime); drag.exec(Qt.CopyAction)


# ── 画布 ─────────────────────────────────────────────────────────
class DesignerCanvas(QWidget):
    selection_changed = Signal(object)
    widget_modified = Signal()

    def __init__(self, parent=None):
        super().__init__(parent); self.setAcceptDrops(True); self.setMinimumSize(400,400); self.setMouseTracking(True)
        self._canvas_widgets = []; self.history = HistoryManager()
        self._clipboard_data = None; self._style_clipboard = None; self._multi_selection = []
        self._signal_connections = []
        self._callback_code = {}  # slot_name -> user-written Python code string
        self._grid_enabled = True
        self._zoom_factor = 1.0
        self._preview_mode = False
        self._fixed_canvas = False
        self._preview_btn = None
        self.design_width = DESIGN_WIDTH
        self.design_height = DESIGN_HEIGHT
        # 多页面支持
        self._pages = [{"name": "页面1", "widgets": []}]  # 页面列表
        self._current_page = 0
        self._placeholder = _Placeholder("将左侧控件拖拽到此处\n拖拽选中 | Ctrl+点击多选 | G键切换网格 | 右键信号/槽", self)
        self._placeholder.setAlignment(Qt.AlignCenter)
        self._placeholder.setStyleSheet("color:#bbb; font-size:16px; background:transparent; border:none;")
        self._placeholder.resize(400, 60)
        self._handles = {}
        for pos in HANDLE_CURSORS:
            h = QFrame(self); h.setFixedSize(HANDLE_SIZE, HANDLE_SIZE)
            h.setStyleSheet("background:#4A90D9; border:1px solid white;"); h.setCursor(HANDLE_CURSORS[pos])
            h.setVisible(False); h._is_handle = True; h._handle_pos = pos
            h.installEventFilter(self); self._handles[pos] = h
        self._selected = None; self._move_active = False; self._resize_active = False
        self._active_handle = None; self._drag_start_mouse = QPoint(); self._drag_start_geom = QRect()
        self._snap_guides = []; self._insert_indicator = None; self._drag_start_geoms = {}
        self._rubber_band_active = False; self._rubber_band_start = QPoint(); self._rubber_band_rect = QRect()
        self._grid_cache = None; self._grid_cache_size = (-1, -1); self._grid_cache_zoom = 0
        QShortcut(QKeySequence.Delete, self).activated.connect(self._delete_selected)
        QShortcut(QKeySequence("Ctrl+Z"), self).activated.connect(self.undo)
        QShortcut(QKeySequence("Ctrl+Y"), self).activated.connect(self.redo)
        QShortcut(QKeySequence("Ctrl+C"), self).activated.connect(self._copy_selected)
        QShortcut(QKeySequence("Ctrl+V"), self).activated.connect(self._paste_widget)
        QShortcut(QKeySequence("Ctrl+D"), self).activated.connect(self._duplicate_selected)
        QShortcut(QKeySequence("F5"), self).activated.connect(self._toggle_preview_shortcut)
        QShortcut(QKeySequence(Qt.Key_Up), self).activated.connect(lambda: self._arrow_move(0, -ARROW_STEP))
        QShortcut(QKeySequence(Qt.Key_Down), self).activated.connect(lambda: self._arrow_move(0, ARROW_STEP))
        QShortcut(QKeySequence(Qt.Key_Left), self).activated.connect(lambda: self._arrow_move(-ARROW_STEP, 0))
        QShortcut(QKeySequence(Qt.Key_Right), self).activated.connect(lambda: self._arrow_move(ARROW_STEP, 0))
        QShortcut(QKeySequence(Qt.Key_Tab), self).activated.connect(lambda: self._tab_navigate(1))
        QShortcut(QKeySequence("Shift+Tab"), self).activated.connect(lambda: self._tab_navigate(-1))
        QShortcut(QKeySequence("G"), self).activated.connect(self._toggle_grid)

    def undo(self): self.history.undo(); self._deselect(); self.widget_modified.emit(); self.update()
    def redo(self): self.history.redo(); self._deselect(); self.widget_modified.emit(); self.update()

    def _toggle_grid(self):
        self._grid_enabled = not self._grid_enabled
        self.update()
        win = self.window()
        if hasattr(win, "grid_action"):
            win.grid_action.setChecked(self._grid_enabled)
            win.grid_action.setText("📐 网格:ON" if self._grid_enabled else "📐 网格:OFF")
        if hasattr(win, "statusBar"):
            state = "开启" if self._grid_enabled else "关闭"
            win.statusBar().showMessage(f"网格已{state} (G键切换)")

    def enter_preview_mode(self):
        """进入运行时预览模式 — 隐藏所有编辑辅助元素"""
        self._preview_mode = True
        self._deselect()
        for h in self._handles.values(): h.setVisible(False)
        # 让所有控件可交互，启动曲线实时滚动
        for w in self._canvas_widgets:
            w.setAttribute(Qt.WA_TransparentForMouseEvents, False)
            if hasattr(w, 'start') and hasattr(w, '_demo_timer'):
                w.start()
        self.setCursor(Qt.ArrowCursor)
        # 显示退出按钮
        if self._preview_btn is None:
            self._preview_btn = QPushButton("✕ 退出预览 (ESC)", self)
            self._preview_btn.setStyleSheet(
                "QPushButton{background:#E74C3C;color:#fff;border:none;border-radius:4px;"
                "padding:6px 14px;font-size:12px;font-weight:bold;}"
                "QPushButton:hover{background:#C0392B;}"
            )
            self._preview_btn.clicked.connect(self.exit_preview_mode)
        self._preview_btn.setVisible(True)
        self._preview_btn.raise_()
        self._preview_btn.move(self.width() - 140, 8)
        self._preview_shortcut = QShortcut(QKeySequence(Qt.Key_Escape), self)
        self._preview_shortcut.activated.connect(self.exit_preview_mode)
        self.update()
        win = self.window()
        if hasattr(win, "statusBar"):
            win.statusBar().showMessage("🔍 预览模式 — 控件可交互 | 按 ESC 退出")

    def exit_preview_mode(self):
        """退出预览模式 — 恢复编辑状态"""
        self._preview_mode = False
        if hasattr(self, '_preview_shortcut') and self._preview_shortcut:
            self._preview_shortcut.deleteLater()
            self._preview_shortcut = None
        if self._preview_btn:
            self._preview_btn.setVisible(False)
        self.setCursor(Qt.ArrowCursor)
        for w in self._canvas_widgets:
            self._install_filter_recursive(w)
            if hasattr(w, 'stop') and hasattr(w, '_demo_timer'):
                w.stop()
        self.update()
        win = self.window()
        if hasattr(win, "statusBar"):
            win.statusBar().showMessage("✅ 已返回编辑模式 | G键切换网格")
        if hasattr(win, "btn_preview"):
            win.btn_preview.setChecked(False)
            win.btn_preview.setText("🔍 预览")

    # ── 多页面管理 ──
    def page_count(self): return len(self._pages)
    def current_page(self): return self._current_page
    def page_name(self, idx=None):
        if idx is None: idx = self._current_page
        return self._pages[idx]["name"] if 0 <= idx < len(self._pages) else ""

    def add_page(self, name=None):
        """新建页面"""
        self._save_current_page()
        name = name or f"页面{len(self._pages)+1}"
        self._pages.append({"name": name, "widgets": []})
        self._current_page = len(self._pages) - 1
        self._canvas_widgets = self._pages[self._current_page]["widgets"]
        self._deselect()
        self.widget_modified.emit()
        return self._current_page

    def remove_page(self, idx):
        """删除页面（至少保留一个）"""
        if len(self._pages) <= 1: return False
        self._save_current_page()
        # 清理该页所有控件
        for w in self._pages[idx]["widgets"]:
            w.hide(); w.deleteLater()
        del self._pages[idx]
        if self._current_page >= len(self._pages):
            self._current_page = len(self._pages) - 1
        self._canvas_widgets = self._pages[self._current_page]["widgets"]
        # 重新显示当前页控件
        for w in self._canvas_widgets:
            if not w.property("_designer_hidden"): w.show()
        self._deselect()
        self.widget_modified.emit()
        return True

    def switch_page(self, idx):
        """切换到指定页面"""
        if idx == self._current_page or idx < 0 or idx >= len(self._pages): return
        self._save_current_page()
        # 隐藏当前页控件
        for w in self._canvas_widgets:
            w.hide()
        self._current_page = idx
        self._canvas_widgets = self._pages[idx]["widgets"]
        # 显示新页面控件
        for w in self._canvas_widgets:
            if not w.property("_designer_hidden"): w.show()
        self._deselect()
        self.widget_modified.emit()

    def rename_page(self, idx, name):
        if 0 <= idx < len(self._pages):
            self._pages[idx]["name"] = name
            self.widget_modified.emit()

    def _save_current_page(self):
        """将当前 canvas_widgets 保存回当前页面"""
        if 0 <= self._current_page < len(self._pages):
            self._pages[self._current_page]["widgets"] = self._canvas_widgets

    # 重写 _create_widget_internal：自动关联到当前页（已经是 canvas_widgets）
    # 重写 _remove_widget_internal：从当前页移除（已经是 canvas_widgets）

    def _snap_to_grid(self, value):
        if not self._grid_enabled: return value
        return round(value / GRID_SIZE) * GRID_SIZE


    def set_canvas_size(self, w, h):
        """设置画布设计尺寸"""
        self.design_width = int(w)
        self.design_height = int(h)
        
        # 【核心修复】使用 minimumSize 而不是 resize，确保在 QScrollArea 中生效
        self.setMinimumSize(self.design_width, self.design_height)
        self.resize(self.design_width, self.design_height) 
        
        # 强制更新占位符位置和画布状态
        if self._placeholder:
            self._placeholder.move(
                (self.width() - self._placeholder.width()) // 2,
                (self.height() - self._placeholder.height()) // 2
            )
        
        # 清除网格缓存并强制重绘
        self._grid_cache = None
        self.update()
        QApplication.processEvents()  # 让 UI 立即响应尺寸变化

    def resizeEvent(self, e):
        super().resizeEvent(e); ph = self._placeholder; ph.move((self.width()-ph.width())//2, (self.height()-ph.height())//2)
        if self._preview_btn: self._preview_btn.move(self.width() - 140, 8)
        self._grid_cache = None

    def wheelEvent(self, event):
        if self._preview_mode: return
        if event.modifiers() & Qt.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0: self._zoom_factor = min(2.0, self._zoom_factor + 0.1)
            else: self._zoom_factor = max(0.5, self._zoom_factor - 0.1)
            self._zoom_factor = round(self._zoom_factor, 1)
            self._apply_zoom(); self._update_handles(); self.update()
            win = self.window()
            if hasattr(win, "statusBar"):
                win.statusBar().showMessage(f"🔍 缩放: {int(self._zoom_factor*100)}%  |  Ctrl+滚轮调节 | G切换网格")
            event.accept()
        else:
            super().wheelEvent(event)
    def dragEnterEvent(self, e): e.acceptProposedAction() if e.mimeData().hasFormat(MIME_TYPE) else e.ignore()
    def dragMoveEvent(self, e):
        if e.mimeData().hasFormat(MIME_TYPE): e.acceptProposedAction(); self._update_insert_indicator(e.position().toPoint()); self.update()
        else: e.ignore()
    def dropEvent(self, e):
        display_name = bytes(e.mimeData().data(MIME_TYPE)).decode()
        _raw_pos = e.position().toPoint(); z = self._zoom_factor
        pos = QPoint(int(_raw_pos.x() / z), int(_raw_pos.y() / z))
        self._insert_indicator = None; self.history.push(AddWidgetCmd(self, display_name, pos)); self.widget_modified.emit(); e.acceptProposedAction()

    def _tab_navigate(self, direction):
        visible_widgets = [w for w in self._canvas_widgets if w.isVisible() and not w.property("_designer_hidden")]
        if not visible_widgets: return
        if self._selected is None: self._select(visible_widgets[0]); return
        try: idx = visible_widgets.index(self._selected)
        except ValueError: idx = -1
        self._select(visible_widgets[(idx + direction) % len(visible_widgets)])

    def align_widgets(self, align_type):
        widgets = self._multi_selection if len(self._multi_selection) >= 2 else ([self._selected] if self._selected else [])
        widgets = [w for w in widgets if w.isVisible() and not w.property("_designer_hidden")]
        if len(widgets) < 2: self._update_status_bar("⚠️ 至少需要选中2个控件才能对齐"); return
        old_geos = [QRect(w.geometry()) for w in widgets]; new_geos = [QRect(g) for g in old_geos]
        if align_type == "left": target = min(g.x() for g in old_geos); [g.setX(target) for g in new_geos]
        elif align_type == "right": target = max(g.right() for g in old_geos); [g.setRight(target) for g in new_geos]
        elif align_type == "top": target = min(g.y() for g in old_geos); [g.setY(target) for g in new_geos]
        elif align_type == "bottom": target = max(g.bottom() for g in old_geos); [g.setBottom(target) for g in new_geos]
        elif align_type == "hcenter": target = sum(g.center().x() for g in old_geos)//len(old_geos); [g.moveCenter(QPoint(target, g.center().y())) for g in new_geos]
        elif align_type == "vcenter": target = sum(g.center().y() for g in old_geos)//len(old_geos); [g.moveCenter(QPoint(g.center().x(), target)) for g in new_geos]
        elif align_type == "same_width": target = max(g.width() for g in old_geos); [g.setWidth(target) for g in new_geos]
        elif align_type == "same_height": target = max(g.height() for g in old_geos); [g.setHeight(target) for g in new_geos]
        elif align_type == "distribute_h":
            sp = sorted(zip(old_geos, range(len(old_geos))), key=lambda p: p[0].x())
            if len(sp) >= 3:
                tw = sum(g.width() for g,_ in sp); le = sp[0][0].x(); re_ = sp[-1][0].right()
                gap = (re_-le-tw)//(len(sp)-1) if len(sp)>1 else 0; cx = le
                for g,idx in sp: new_geos[idx].setX(cx); cx += g.width()+gap
        elif align_type == "distribute_v":
            sp = sorted(zip(old_geos, range(len(old_geos))), key=lambda p: p[0].y())
            if len(sp) >= 3:
                th = sum(g.height() for g,_ in sp); te = sp[0][0].y(); be = sp[-1][0].bottom()
                gap = (be-te-th)//(len(sp)-1) if len(sp)>1 else 0; cy = te
                for g,idx in sp: new_geos[idx].setY(cy); cy += g.height()+gap
        self.history.push(BatchAlignCmd(self, widgets, old_geos, new_geos))
        self.widget_modified.emit(); self.update()
        self._update_status_bar(f"✅ 已对齐: {align_type} ({len(widgets)}个控件)")

    def insert_template(self, template_name):
        all_tmpl = {**INDUSTRIAL_TEMPLATES, **_load_user_templates()}
        tmpl = all_tmpl.get(template_name)
        if not tmpl: return
        base_pos = QPoint(self.width() // 2 - 140, self.height() // 2 - 80)
        self.history.push(InsertTemplateCmd(self, tmpl["widgets"], base_pos))
        self._update_status_bar(f"🏭 已插入模板: {template_name}")

    def _save_as_template(self, widget):
        """将选中控件另存为用户模板"""
        from PySide6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "另存为模板", "模板名称:")
        if not ok or not name.strip(): return
        # 保存所有控件（拍平成扁平列表，按绝对坐标）
        all_widgets = []
        def collect(ws):
            for w in ws:
                all_widgets.append(w)
                if hasattr(w, "_content_layout"):
                    for i in range(w._content_layout.count()):
                        item = w._content_layout.itemAt(i)
                        if item and item.widget():
                            all_widgets.append(item.widget())
        widgets_to_save = self._multi_selection if len(self._multi_selection) > 1 else [widget]
        collect(widgets_to_save)
        # 子控件的 x/y 是相对父容器的，转成画布绝对坐标
        def canvas_pos(w):
            p = w.pos()
            parent = w.parent()
            while parent and parent is not self:
                p += parent.pos()
                parent = parent.parent()
            return p
        min_x = min(canvas_pos(w).x() for w in all_widgets)
        min_y = min(canvas_pos(w).y() for w in all_widgets)
        tmpl_widgets = []
        for w in all_widgets:
            info = self._collect_widget_info(w)
            abs_pos = canvas_pos(w)
            info["x"] = abs_pos.x() - min_x
            info["y"] = abs_pos.y() - min_y
            tmpl_widgets.append(info)
        USER_TEMPLATES[name] = {"description": f"用户自定义: {name}", "widgets": tmpl_widgets}
        _save_user_templates()
        self._update_status_bar(f"✅ 已保存模板: {name}（{len(tmpl_widgets)}个控件）")

    def _copy_selected(self):
        w = self._selected
        if not w: return
        self._clipboard_data = {"display_name": w.property("_display_name"), "role": w.property("role") or "default",
            "objectName": w.objectName(), "styleSheet": w.styleSheet(), "w": w.width(), "h": w.height(),
            "hSizePolicy": _policy_to_str(w.sizePolicy().horizontalPolicy()), "vSizePolicy": _policy_to_str(w.sizePolicy().verticalPolicy()),
            "minWidth": w.minimumWidth(), "minHeight": w.minimumHeight(), "maxWidth": w.maximumWidth(), "maxHeight": w.maximumHeight(),
            "tag": w.property("_tag") or "",
            "anchor_left": bool(w.property("_anchor_left")), "anchor_right": bool(w.property("_anchor_right")),
            "anchor_top": bool(w.property("_anchor_top")), "anchor_bottom": bool(w.property("_anchor_bottom"))}
        if hasattr(w,"text") and not isinstance(w, QGroupBox): self._clipboard_data["text"] = w.text()
        if hasattr(w,"title") and isinstance(w, QGroupBox): self._clipboard_data["title"] = w.title()
        if isinstance(w,(QLineEdit,QWTextEdit)): self._clipboard_data["placeholderText"] = w.placeholderText()
        if hasattr(w,"value") and callable(getattr(w,"value",None)): self._clipboard_data["value"] = w.value()
        self._update_status_bar(f"📋 已复制: {w.objectName()}")

    def _copy_style(self):
        """格式刷：复制控件的 role + styleSheet + font"""
        w = self._selected
        if not w: return
        self._style_clipboard = {
            "role": w.property("role") or "default",
            "styleSheet": w.styleSheet(),
        }
        if hasattr(w, 'font') and callable(w.font):
            f = w.font()
            self._style_clipboard["fontFamily"] = f.family()
            self._style_clipboard["fontSize"] = f.pointSize()
            self._style_clipboard["fontBold"] = f.bold()
            self._style_clipboard["fontItalic"] = f.italic()
        self._update_status_bar(f"🎨 已复制样式: {w.objectName()}")

    def _paste_style(self):
        """格式刷：将复制的样式应用到选中的控件"""
        if not self._style_clipboard: return
        targets = self._multi_selection if len(self._multi_selection) >= 2 else ([self._selected] if self._selected else [])
        targets = [w for w in targets if w.isVisible() and not w.property("_designer_hidden")]
        if not targets: return
        sc = self._style_clipboard
        for w in targets:
            w.setProperty("role", sc["role"]); w.style().unpolish(w); w.style().polish(w)
            if sc.get("styleSheet"): w.setStyleSheet(sc["styleSheet"])
            if "fontFamily" in sc and hasattr(w, 'setFont'):
                f = QFont(sc["fontFamily"], sc.get("fontSize", 9))
                f.setBold(sc.get("fontBold", False)); f.setItalic(sc.get("fontItalic", False))
                w.setFont(f)
        self.widget_modified.emit(); self.update()
        self._update_status_bar(f"🎨 已粘贴样式到 {len(targets)} 个控件")

    def _paste_widget(self):
        if not self._clipboard_data: return
        data = self._clipboard_data
        paste_pos = QPoint(self._selected.x()+10, self._selected.y()+10) if self._selected else QPoint(self.width()//2-60, self.height()//2-18)
        dn = data.get("display_name")
        if not dn: return
        entry_map = get_display_to_entry()
        if dn not in entry_map: return
        w = self._create_widget_internal(dn, paste_pos)
        if not w: return
        w.resize(data.get("w",100), data.get("h",30))
        if "objectName" in data: w.setObjectName(data["objectName"])
        if "role" in data: w.setProperty("role", data["role"]); w.style().unpolish(w); w.style().polish(w)
        if "styleSheet" in data and data["styleSheet"]: w.setStyleSheet(data["styleSheet"])
        if "text" in data and hasattr(w,"setText"): w.setText(data["text"])
        if "title" in data and hasattr(w,"setTitle"): w.setTitle(data["title"])
        if "placeholderText" in data and hasattr(w,"setPlaceholderText"): w.setPlaceholderText(data["placeholderText"])
        if "value" in data and hasattr(w,"setValue"):
            try: w.setValue(data["value"])
            except: pass
        if data.get("tag"): w.setProperty("_tag", data["tag"])
        w.setProperty("_anchor_left", data.get("anchor_left", False)); w.setProperty("_anchor_right", data.get("anchor_right", False))
        w.setProperty("_anchor_top", data.get("anchor_top", False)); w.setProperty("_anchor_bottom", data.get("anchor_bottom", False))
        sp = w.sizePolicy()
        sp.setHorizontalPolicy(SIZE_POLICY_MAP.get(data.get("hSizePolicy","Preferred"), QSizePolicy.Preferred))
        sp.setVerticalPolicy(SIZE_POLICY_MAP.get(data.get("vSizePolicy","Preferred"), QSizePolicy.Preferred))
        w.setSizePolicy(sp)
        w.setMinimumWidth(data.get("minWidth",0)); w.setMinimumHeight(data.get("minHeight",0))
        w.setMaximumWidth(data.get("maxWidth",16777215)); w.setMaximumHeight(data.get("maxHeight",16777215))
        self.history.undo_stack.append(AddWidgetCmd.__new__(AddWidgetCmd))
        self.history.undo_stack[-1].canvas = self; self.history.undo_stack[-1].display_name = dn
        self.history.undo_stack[-1].pos = paste_pos; self.history.undo_stack[-1].widget = w
        self.history.redo_stack.clear(); self.widget_modified.emit()
        self._update_status_bar(f"📋 已粘贴: {w.objectName()}")

    def _arrow_move(self, dx, dy):
        w = self._selected
        if not w or w.property("_locked"): return
        parent = w.parent()
        if parent and hasattr(parent, "_content_layout"): return
        old_pos = w.pos()
        step = GRID_SIZE if self._grid_enabled else ARROW_STEP
        new_x = max(0, min(old_pos.x()+dx*step//ARROW_STEP, self.width()-w.width()))
        new_y = max(0, min(old_pos.y()+dy*step//ARROW_STEP, self.height()-w.height()))
        if self._grid_enabled:
            new_x = self._snap_to_grid(new_x); new_y = self._snap_to_grid(new_y)
        new_pos = QPoint(new_x, new_y)
        if new_pos != old_pos:
            self.history.push(MoveWidgetCmd(self, w, old_pos, new_pos))
            self.widget_modified.emit(); self._update_handles(); self.update()
            self._update_status_bar(f"微调: {w.objectName()} → ({new_x}, {new_y})")

    def _toggle_preview_shortcut(self):
        win = self.window()
        if hasattr(win, 'btn_preview'):
            win.btn_preview.toggle()

    def _duplicate_selected(self):
        """Ctrl+D 复制并偏移10px粘贴"""
        if not self._selected: return
        self._copy_selected()
        if self._clipboard_data:
            paste_pos = QPoint(self._selected.x()+10, self._selected.y()+10)
            dn = self._clipboard_data.get("display_name")
            if not dn: return
            entry_map = get_display_to_entry()
            if dn not in entry_map: return
            w = self._create_widget_internal(dn, paste_pos)
            if not w: return
            w.resize(self._clipboard_data.get("w",100), self._clipboard_data.get("h",30))
            if "objectName" in self._clipboard_data: w.setObjectName(self._clipboard_data["objectName"])
            if "role" in self._clipboard_data: w.setProperty("role", self._clipboard_data["role"]); w.style().unpolish(w); w.style().polish(w)
            if "styleSheet" in self._clipboard_data and self._clipboard_data["styleSheet"]: w.setStyleSheet(self._clipboard_data["styleSheet"])
            if "text" in self._clipboard_data and hasattr(w,"setText"): w.setText(self._clipboard_data["text"])
            if "tag" in self._clipboard_data: w.setProperty("_tag", self._clipboard_data["tag"])
            self._update_status_bar(f"📋 已复制: {w.objectName()}")

    def _toggle_lock(self):
        w = self._selected
        if not w: return
        locked = not bool(w.property("_locked")); w.setProperty("_locked", locked)
        self._update_status_bar(f"{'🔒 已锁定' if locked else '🔓 已解锁'}: {w.objectName()}"); self.widget_modified.emit()

    def _toggle_hide(self):
        w = self._selected
        if not w: return
        hidden = not bool(w.property("_designer_hidden")); w.setProperty("_designer_hidden", hidden)
        if hidden: w.hide(); self._deselect()
        else: w.show(); self._select(w)
        self._update_status_bar(f"{'👁️‍🗨️ 已隐藏' if hidden else '👁️ 已显示'}: {w.objectName() if not hidden else '(已隐藏)'}"); self.widget_modified.emit()

    def _calc_snap_guides(self, moving_rect, exclude_widget=None):
        """
        智能吸附增强版：
        1. 基础对齐：边缘、中心点、画布/容器边界
        2. 等间距分布：检测与相邻控件的间距是否相等 (Smart Snap)
        3. 相对父容器居中：检测是否在父容器内水平/垂直居中
        """
        guides = []
        snap_x, snap_y = None, None
        min_dx, min_dy = SNAP_THRESHOLD + 1, SNAP_THRESHOLD + 1
        
        # 获取当前选中控件的边缘和中心坐标
        edges_x = [moving_rect.left(), moving_rect.center().x(), moving_rect.right()]
        edges_y = [moving_rect.top(), moving_rect.center().y(), moving_rect.bottom()]
        
        # 1. 基础对齐：与其他可见控件的边缘/中心对齐
        for w in self._canvas_widgets:
            if w is exclude_widget or not w.isVisible(): continue
            r = w.geometry()
            
            # X轴对齐检测
            for ex in edges_x:
                for tx in [r.left(), r.center().x(), r.right()]:
                    dx = abs(ex - tx)
                    if dx < min_dx: 
                        min_dx = dx
                        snap_x = tx
                        
            # Y轴对齐检测
            for ey in edges_y:
                for ty in [r.top(), r.center().y(), r.bottom()]:
                    dy = abs(ey - ty)
                    if dy < min_dy: 
                        min_dy = dy
                        snap_y = ty

        # 2. 等间距分布吸附 (Smart Snap Guides)
        # 仅对顶层控件生效，避免在布局容器内产生冲突
        parent = self._selected.parent() if self._selected else None
        in_container = parent and hasattr(parent, '_content_layout')
        
        if not in_container and len(self._canvas_widgets) >= 3:
            # 获取所有可见顶层控件并按位置排序
            visible_widgets = sorted(
                [w for w in self._canvas_widgets if w.isVisible() and w is not exclude_widget],
                key=lambda w: w.x()
            )
            
            # --- 水平等间距检测 ---
            current_left = moving_rect.left()
            current_right = moving_rect.right()
            current_width = moving_rect.width()
            
            # 寻找左右最近的邻居
            left_neighbor = next((w for w in reversed(visible_widgets) if w.geometry().right() <= current_left), None)
            right_neighbor = next((w for w in visible_widgets if w.geometry().left() >= current_right), None)
            
            if left_neighbor and right_neighbor:
                gap_left = current_left - left_neighbor.geometry().right()
                gap_right = right_neighbor.geometry().left() - current_right
                
                # 如果两个间隙差值小于阈值，触发等间距吸附
                if abs(gap_left - gap_right) < SNAP_THRESHOLD * 2:
                    ideal_gap = (gap_left + gap_right) / 2.0
                    # 计算理想位置（以左侧邻居为基准）
                    ideal_x = left_neighbor.geometry().right() + ideal_gap
                    # 优先吸附左边缘，保持移动手感
                    if abs(current_left - ideal_x) < min_dx:
                        min_dx = abs(current_left - ideal_x)
                        snap_x = ideal_x
                        # 添加特殊标记用于绘制不同颜色的辅助线
                        guides.append(('eq_h', ideal_x)) 

            # --- 垂直等间距检测 ---
            visible_widgets_v = sorted(
                [w for w in self._canvas_widgets if w.isVisible() and w is not exclude_widget],
                key=lambda w: w.y()
            )
            current_top = moving_rect.top()
            current_bottom = moving_rect.bottom()
            
            top_neighbor = next((w for w in reversed(visible_widgets_v) if w.geometry().bottom() <= current_top), None)
            bottom_neighbor = next((w for w in visible_widgets_v if w.geometry().top() >= current_bottom), None)
            
            if top_neighbor and bottom_neighbor:
                gap_top = current_top - top_neighbor.geometry().bottom()
                gap_bottom = bottom_neighbor.geometry().top() - current_bottom
                
                if abs(gap_top - gap_bottom) < SNAP_THRESHOLD * 2:
                    ideal_gap = (gap_top + gap_bottom) / 2.0
                    ideal_y = top_neighbor.geometry().bottom() + ideal_gap
                    
                    if abs(current_top - ideal_y) < min_dy:
                        min_dy = abs(current_top - ideal_y)
                        snap_y = ideal_y
                        guides.append(('eq_v', ideal_y))

        # 3. 相对父容器居中吸附
        if in_container:
            cr = parent.geometry()
            center_x = cr.left() + cr.width() // 2
            center_y = cr.top() + cr.height() // 2
            
            if abs(moving_rect.center().x() - center_x) < SNAP_THRESHOLD:
                guides.append(('center_h', center_x))
            if abs(moving_rect.center().y() - center_y) < SNAP_THRESHOLD:
                guides.append(('center_v', center_y))
        else:
            # 画布边界对齐
            boundary_x = [0, self.width()]
            boundary_y = [0, self.height()]
            for ex in edges_x:
                for bx in boundary_x:
                    dx = abs(ex - bx)
                    if dx < min_dx: min_dx = dx; snap_x = bx
            for ey in edges_y:
                for by in boundary_y:
                    dy = abs(ey - by)
                    if dy < min_dy: min_dy = dy; snap_y = by

        # 汇总基础吸附结果
        if min_dx <= SNAP_THRESHOLD and snap_x is not None: 
            guides.append(('x', snap_x))
        if min_dy <= SNAP_THRESHOLD and snap_y is not None: 
            guides.append(('y', snap_y))
            
        return guides, snap_x, snap_y, min_dx, min_dy

    def _update_insert_indicator(self, pos):
        self._insert_indicator = None
        for w in reversed(self._canvas_widgets):
            if hasattr(w, "_content_layout") and w.geometry().contains(pos):
                ly = w._content_layout; count = ly.count()
                if count == 0: self._insert_indicator = (w, w.geometry().top()+8)
                else:
                    insert_y = w.geometry().bottom()-8
                    for i in range(count):
                        item = ly.itemAt(i)
                        if item and item.widget() and pos.y() < item.widget().geometry().bottom():
                            insert_y = item.widget().geometry().top(); break
                    self._insert_indicator = (w, insert_y)
                return

    def _install_filter_recursive(self, widget):
        widget.installEventFilter(self)
        if isinstance(widget, VIEWPORT_WIDGETS):
            vp = widget.viewport()
            if vp: vp.installEventFilter(self)
        if hasattr(widget, "_content_layout"):
            ly = widget._content_layout
            for i in range(ly.count()):
                child = ly.itemAt(i).widget()
                if child: self._install_filter_recursive(child)

    def _create_widget_internal(self, display_name, drop_pos, center=True):
        entry_map = get_display_to_entry(); entry = entry_map.get(display_name)
        if not entry: return None
        _, qt_cls, init_kwargs = entry[:3]; src_file = entry[3] if len(entry) > 3 else None
        container = next((w for w in reversed(self._canvas_widgets) if hasattr(w,"_content_layout") and w.geometry().contains(drop_pos)), None)
        if qt_cls is None and "layout" in init_kwargs:
            lt = init_kwargs["layout"]; c = "#4A90D9" if lt=="vbox" else "#E67E22"
            lc = QVBoxLayout if lt=="vbox" else QHBoxLayout
            w = QFrame(); w.setFrameShape(QFrame.StyledPanel); w.setMinimumSize(80,60)
            w.setStyleSheet(f"QFrame{{border:2px dashed {c};background:rgba(255,255,255,0.04);}}")
            ly = lc(w); ly.setContentsMargins(8,8,8,8); ly.setSpacing(4); w._content_layout = ly
        elif qt_cls:
            try: w = qt_cls()
            except Exception as e: print(f"[Canvas] 创建控件失败 {display_name}: {e}"); return None
            if "text" in init_kwargs and hasattr(w,"setText"): w.setText(init_kwargs["text"])
            if "title" in init_kwargs and hasattr(w,"setTitle"): w.setTitle(init_kwargs["title"])
            if "placeholderText" in init_kwargs and hasattr(w,"setPlaceholderText"): w.setPlaceholderText(init_kwargs["placeholderText"])
            if "items" in init_kwargs and hasattr(w,"addItems"): w.addItems(init_kwargs["items"])
            if "range" in init_kwargs and hasattr(w,"setRange"): w.setRange(*init_kwargs["range"])
            if "value" in init_kwargs and hasattr(w,"setValue"): w.setValue(init_kwargs["value"])
            if "decimals" in init_kwargs and hasattr(w,"setDecimals"): w.setDecimals(init_kwargs["decimals"])
            if "orientation" in init_kwargs and hasattr(w,"setOrientation"): w.setOrientation(init_kwargs["orientation"])
            if "frameShape" in init_kwargs and hasattr(w,"setFrameShape"): w.setFrameShape(init_kwargs["frameShape"])
            if "openExternalLinks" in init_kwargs and hasattr(w,"setOpenExternalLinks"): w.setOpenExternalLinks(init_kwargs["openExternalLinks"])
        else: return None
        w.setProperty("_display_name", display_name); w.setProperty("role", "default")
        w.setProperty("_locked", False); w.setProperty("_designer_hidden", False); w.setProperty("_tag", "")
        w.setProperty("_anchor_left", False); w.setProperty("_anchor_right", False)
        if src_file: w.setProperty("_custom_source", src_file)
        w.setProperty("_anchor_top", False); w.setProperty("_anchor_bottom", False)
        existing = set()
        def collect(ws):
            for ww in ws:
                existing.add(ww.objectName())
                if hasattr(ww,"_content_layout"): collect([ww._content_layout.itemAt(i).widget() for i in range(ww._content_layout.count()) if ww._content_layout.itemAt(i).widget()])
        collect(self._canvas_widgets)
        prefix = NAME_TO_PREFIX.get(display_name, _sanitize(display_name)); i = 1
        while f"{prefix}_{i}" in existing: i += 1
        w.setObjectName(f"{prefix}_{i}"); w.setProperty("_auto_objectName", True)
        if container: w.setParent(container); container._content_layout.addWidget(w)
        else:
            w.setParent(self); sz = DEFAULT_SIZES.get(display_name, QSize(120,36)); w.resize(sz)
            if center:
                x = max(0, min(drop_pos.x()-sz.width()//2, self.width()-sz.width()))
                y = max(0, min(drop_pos.y()-sz.height()//2, self.height()-sz.height()))
            else:
                x = max(0, min(drop_pos.x(), self.width()-sz.width()))
                y = max(0, min(drop_pos.y(), self.height()-sz.height()))
            if self._grid_enabled:
                x = self._snap_to_grid(x); y = self._snap_to_grid(y)
            w.move(x, y); self._canvas_widgets.append(w)
        self._install_filter_recursive(w); w.show()
        if self._placeholder.isVisible(): self._placeholder.setVisible(False)
        self._select(w); return w

    def _remove_widget_internal(self, widget):
        self._deselect()
        if widget in self._canvas_widgets: self._canvas_widgets.remove(widget)
        widget.hide(); widget.deleteLater()
        if not self._canvas_widgets: self._placeholder.setVisible(True)

    def _apply_property(self, widget, prop, value):
        try:
            if prop == "objectName": widget.setObjectName(value)
            elif prop == "text" and hasattr(widget,"setText"): widget.setText(value)
            elif prop == "title":
                if hasattr(widget, "setGaugeTitle"): widget.setGaugeTitle(value)
                elif hasattr(widget, "setTitle"): widget.setTitle(value)
            elif prop == "unit" and hasattr(widget, "setUnit"): widget.setUnit(value)
            elif prop == "placeholderText" and hasattr(widget,"setPlaceholderText"): widget.setPlaceholderText(value)
            elif prop == "role": widget.setProperty("role", value); widget.style().unpolish(widget); widget.style().polish(widget)
            elif prop == "tag": widget.setProperty("_tag", value)
            elif prop == "anchor_left": widget.setProperty("_anchor_left", value)
            elif prop == "anchor_right": widget.setProperty("_anchor_right", value)
            elif prop == "anchor_top": widget.setProperty("_anchor_top", value)
            elif prop == "anchor_bottom": widget.setProperty("_anchor_bottom", value)
            elif prop == "value":
                if isinstance(widget,(QSpinBox,QProgressBar,QDial)): widget.setValue(int(float(value)))
                elif isinstance(widget,(QDoubleSpinBox,QSlider)): widget.setValue(float(value))
                elif isinstance(widget,QLCDNumber): widget.display(int(float(value)))
            elif prop == "x": widget.move(max(0,int(value)), widget.y())
            elif prop == "y": widget.move(widget.x(), max(0,int(value)))
            elif prop == "width": widget.resize(max(MIN_W,int(value)), widget.height())
            elif prop == "height": widget.resize(widget.width(), max(MIN_H,int(value)))
            elif prop == "hSizePolicy":
                sp = widget.sizePolicy(); sp.setHorizontalPolicy(SIZE_POLICY_MAP.get(value, QSizePolicy.Preferred)); widget.setSizePolicy(sp)
            elif prop == "vSizePolicy":
                sp = widget.sizePolicy(); sp.setVerticalPolicy(SIZE_POLICY_MAP.get(value, QSizePolicy.Preferred)); widget.setSizePolicy(sp)
            elif prop == "minWidth": widget.setMinimumWidth(max(0, int(value)))
            elif prop == "minHeight": widget.setMinimumHeight(max(0, int(value)))
            elif prop == "maxWidth": widget.setMaximumWidth(max(0, int(value)))
            elif prop == "maxHeight": widget.setMaximumHeight(max(0, int(value)))
            elif prop in ("marginLeft", "marginTop", "marginRight", "marginBottom") and hasattr(widget, "_content_layout"):
                m = widget._content_layout.contentsMargins()
                vals = {"marginLeft": m.left(), "marginTop": m.top(), "marginRight": m.right(), "marginBottom": m.bottom()}
                vals[prop] = max(0, int(value))
                widget._content_layout.setContentsMargins(vals["marginLeft"], vals["marginTop"], vals["marginRight"], vals["marginBottom"])
                widget.update()
            elif prop == "spacing" and hasattr(widget, "_content_layout"):
                widget._content_layout.setSpacing(max(0, int(value)))
                widget.update()
                
            # ══════════════════════════════════════════════════════════════
            # 【新增】MultiTrendWidget 属性写入逻辑
            # ══════════════════════════════════════════════════════════════
            elif type(widget).__name__ == "MultiTrendWidget":
                if prop == "x_range": widget.set_x_range(value)
                elif prop == "y_min": widget.set_y_min(value)
                elif prop == "y_max": widget.set_y_max(value)
                elif prop == "auto_scale_y": widget.set_auto_scale_y(value)
                elif prop == "grid_density_x": widget.set_grid_density_x(value)
                elif prop == "grid_density_y": widget.set_grid_density_y(value)
                elif prop == "bg_color": widget.set_bg_color(value)
                elif prop == "grid_color": widget.set_grid_color(value)
                elif prop == "text_color": widget.set_text_color(value)
                
            elif prop == "styleSheet": widget.setStyleSheet(value)
            
        except (ValueError, TypeError): pass
        self.widget_modified.emit()

    # ── JSON安全序列化辅助 ─────────────────────────────────────────
    @staticmethod
    def _to_json_safe(val, default=""):
        """将任意值转换为JSON可安全序列化的基本类型"""
        if val is None:
            return default
        if isinstance(val, (str, int, float, bool)):
            return val
        try:
            return str(val)
        except Exception:
            return default

    def _collect_widget_info(self, w):
        """递归收集控件信息（含容器内子控件），确保所有值为JSON可序列化"""
        sp = w.sizePolicy()
        # JSON安全转换value
        value_attr = None
        if hasattr(w, "value") and callable(getattr(w, "value", None)):
            try:
                val = w.value()
                if isinstance(val, (int, float, bool, str)):
                    value_attr = val
                elif isinstance(val, (list, tuple)):
                    value_attr = [self._to_json_safe(v) for v in val]
                else:
                    value_attr = str(val)
            except Exception:
                value_attr = None
        # 安全获取text
        text_attr = None
        try:
            if hasattr(w, "text") and not isinstance(w, QGroupBox):
                t = w.text()
                text_attr = t if isinstance(t, str) else str(t) if t is not None else None
        except Exception:
            text_attr = None
        # 安全获取title
        title_attr = None
        try:
            if hasattr(w, "title") and isinstance(w, QGroupBox):
                t = w.title()
                title_attr = t if isinstance(t, str) else str(t) if t is not None else None
        except Exception:
            title_attr = None
        # 安全获取placeholderText
        placeholder_attr = None
        try:
            if isinstance(w, (QLineEdit, QWTextEdit)):
                placeholder_attr = w.placeholderText() or ""
        except Exception:
            placeholder_attr = ""       
        info = {
            "display_name": self._to_json_safe(w.property("_display_name")),
            "x": w.x(), "y": w.y(), "w": w.width(), "h": w.height(),
            "objectName": self._to_json_safe(w.objectName()),
            "role": self._to_json_safe(w.property("role") or "default"),
            "styleSheet": self._to_json_safe(w.styleSheet()),
            "hSizePolicy": _policy_to_str(sp.horizontalPolicy()),
            "vSizePolicy": _policy_to_str(sp.verticalPolicy()),
            "minWidth": w.minimumWidth(), "minHeight": w.minimumHeight(),
            "maxWidth": w.maximumWidth(), "maxHeight": w.maximumHeight(),
            "locked": bool(w.property("_locked")),
            "hidden": bool(w.property("_designer_hidden")),
            "tag": self._to_json_safe(w.property("_tag") or ""),
            "anchor_left": bool(w.property("_anchor_left")),
            "anchor_right": bool(w.property("_anchor_right")),
            "anchor_top": bool(w.property("_anchor_top")),
            "anchor_bottom": bool(w.property("_anchor_bottom")),
        }
        
        if text_attr is not None: info["text"] = text_attr
        if title_attr is not None: info["title"] = title_attr
        if placeholder_attr is not None: info["placeholderText"] = placeholder_attr
        if value_attr is not None: info["value"] = value_attr
        
        src = w.property("_custom_source")
        if src: info["_custom_source"] = self._to_json_safe(src)

        # ══════════════════════════════════════════════════════════════
        # 💾 新增：控件深度序列化特有属性
        # ══════════════════════════════════════════════════════════════
        try:
            # QComboBox: 保存下拉选项和当前索引
            if isinstance(w, QComboBox):
                items = [w.itemText(i) for i in range(w.count())]
                info["combo_items"] = items
                info["combo_current_index"] = w.currentIndex()
            
            # QTableWidget: 保存行列数、表头文本
            elif isinstance(w, QTableWidget):
                info["table_row_count"] = w.rowCount()
                info["table_column_count"] = w.columnCount()
                h_headers = []
                for c in range(w.columnCount()):
                    item = w.horizontalHeaderItem(c)
                    h_headers.append(item.text() if item else "")
                v_headers = []
                for r in range(w.rowCount()):
                    item = w.verticalHeaderItem(r)
                    v_headers.append(item.text() if item else str(r + 1))
                info["table_h_headers"] = h_headers
                info["table_v_headers"] = v_headers
            
            # QTreeWidget: 保存列数和顶层节点结构（递归）
            elif isinstance(w, QTreeWidget):
                info["tree_column_count"] = w.columnCount()
                tree_headers = []
                for c in range(w.columnCount()):
                    item = w.headerItem()
                    tree_headers.append(item.text(c) if item else f"列{c+1}")
                info["tree_headers"] = tree_headers
                
                def serialize_tree_node(node):
                    texts = [node.text(c) for c in range(w.columnCount())]
                    data = {"texts": texts, "children": []}
                    for i in range(node.childCount()):
                        data["children"].append(serialize_tree_node(node.child(i)))
                    return data
                
                top_nodes = []
                for i in range(w.topLevelItemCount()):
                    top_nodes.append(serialize_tree_node(w.topLevelItem(i)))
                info["tree_nodes"] = top_nodes
            
            # QListWidget: 保存列表项文本
            elif isinstance(w, QListWidget):
                items = [w.item(i).text() for i in range(w.count())]
                info["list_items"] = items
            
            # QTabWidget: 保存标签页名称
            elif isinstance(w, QTabWidget):
                tab_names = [w.tabText(i) for i in range(w.count())]
                info["tab_names"] = tab_names
            
            # SVG: 保存图元数据
            if hasattr(w, '_renderer') and hasattr(w, '_svg_name'):
                try:
                    from svg_import import SVG_LIBRARY
                    svg_name = w._svg_name
                    info["_svg_name"] = svg_name
                    if svg_name in SVG_LIBRARY:
                        info["_svg_data"] = SVG_LIBRARY[svg_name].get("svg_data", "")
                except Exception:
                    pass
                
        except Exception as e:
            print(f"[Serialize Warning] 序列化 {w.objectName()} 特有属性失败: {e}")

        # 递归保存容器内的子控件
        if hasattr(w, "_content_layout"):
            children = []
            ly = w._content_layout
            for i in range(ly.count()):
                item = ly.itemAt(i)
                if item and item.widget():
                    child_w = item.widget()
                    if not child_w.property("_designer_hidden"):
                        children.append(self._collect_widget_info(child_w))
            if children:
                info["children"] = children
        
        return info

    def save_project(self, path):
        """保存项目（带异常保护，防止因控件属性异常导致崩溃）"""
        import traceback as _tb
        try:
            self._save_current_page()
            pages_data = []
            for pi, p in enumerate(self._pages):
                pw_list = []
                for wi, w in enumerate(list(p["widgets"])):
                    try:
                        info = self._collect_widget_info(w)
                        pw_list.append(info)
                    except Exception as e:
                        _tb.print_exc()
                        continue
                pages_data.append({"name": p["name"], "widgets": pw_list})
            data = {
                "pages": pages_data,
                "signal_connections": self._signal_connections,
                "callback_code": self._callback_code,
                "design_width": self.design_width,
                "design_height": self.design_height,
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            _tb.print_exc()
            raise

    def load_project(self, path):
        with open(path, "r", encoding="utf-8") as f: raw = json.load(f)
        self.clear_canvas(); self.history.undo_stack.clear(); self.history.redo_stack.clear()

        # 清理旧页面
        for p in self._pages:
            for w in p.get("widgets", []):
                w.hide(); w.deleteLater()
        self._pages = [{"name": "页面1", "widgets": []}]
        self._current_page = 0
        self._canvas_widgets = self._pages[0]["widgets"]

        if isinstance(raw, list):
            # 旧格式兼容：单页
            self._signal_connections = []
            self._load_page_widgets(raw, 0)
        else:
            self._signal_connections = raw.get("signal_connections", [])
            self._callback_code = raw.get("callback_code", {})
            # 恢复画布尺寸
            if "design_width" in raw:
                self.set_canvas_size(raw["design_width"], raw["design_height"])
            pages_data = raw.get("pages", [])
            if pages_data:
                self._pages = []
                for i, pd in enumerate(pages_data):
                    name = pd.get("name", f"页面{i+1}")
                    self._pages.append({"name": name, "widgets": []})
                    self._current_page = i
                    self._canvas_widgets = self._pages[i]["widgets"]
                    self._load_page_widgets(pd.get("widgets", []), i)
                self._current_page = 0
                self._canvas_widgets = self._pages[0]["widgets"]
                for w in self._canvas_widgets:
                    if not w.property("_designer_hidden"): w.show()
            else:
                # 新格式但无pages字段
                self._load_page_widgets(raw.get("widgets", []), 0)
        self._deselect(); self.widget_modified.emit()

    def _load_page_widgets(self, widget_data, page_idx):
        """加载控件到指定页面（含深度状态恢复）"""
        for info in widget_data:
            dn = info.get("display_name")
            if not dn: continue
            entry_map = get_display_to_entry()
            if dn not in entry_map: 
                print(f"[Load] 跳过未知控件: {dn}"); continue
            
            pos = QPoint(info.get("x",0), info.get("y",0))
            w = self._create_widget_internal(dn, pos)
            if not w: continue
            
            # ── 1. 基础属性恢复 ──────────────────────────────
            w.setGeometry(info.get("x",0), info.get("y",0), info.get("w",100), info.get("h",30))
            if "objectName" in info: w.setObjectName(info["objectName"])
            if "role" in info: 
                w.setProperty("role", info["role"]); w.style().unpolish(w); w.style().polish(w)
            if "styleSheet" in info and info["styleSheet"]: w.setStyleSheet(info["styleSheet"])
            if "text" in info and hasattr(w,"setText"): w.setText(info["text"])
            if "title" in info and hasattr(w,"setTitle"): w.setTitle(info["title"])
            if "placeholderText" in info and hasattr(w,"setPlaceholderText"): w.setPlaceholderText(info["placeholderText"])
            if "value" in info and hasattr(w,"setValue"):
                try: w.setValue(info["value"])
                except: pass
            if "tag" in info and info["tag"]: w.setProperty("_tag", info["tag"])
            
            # 锚点与大小策略
            if "anchor_left" in info: w.setProperty("_anchor_left", info["anchor_left"])
            if "anchor_right" in info: w.setProperty("_anchor_right", info["anchor_right"])
            if "anchor_top" in info: w.setProperty("_anchor_top", info["anchor_top"])
            if "anchor_bottom" in info: w.setProperty("_anchor_bottom", info["anchor_bottom"])
            
            if "hSizePolicy" in info or "vSizePolicy" in info:
                sp = w.sizePolicy()
                sp.setHorizontalPolicy(SIZE_POLICY_MAP.get(info.get("hSizePolicy","Preferred"), QSizePolicy.Preferred))
                sp.setVerticalPolicy(SIZE_POLICY_MAP.get(info.get("vSizePolicy","Preferred"), QSizePolicy.Preferred))
                w.setSizePolicy(sp)
            
            if "minWidth" in info: w.setMinimumWidth(info["minWidth"])
            if "minHeight" in info: w.setMinimumHeight(info["minHeight"])
            if "maxWidth" in info: w.setMaximumWidth(info["maxWidth"])
            if "maxHeight" in info: w.setMaximumHeight(info["maxHeight"])
            if info.get("locked"): w.setProperty("_locked", True)
            if info.get("hidden"): w.setProperty("_designer_hidden", True); w.hide()
            if info.get("_custom_source"): w.setProperty("_custom_source", info["_custom_source"])

            # ── 2. 💾 深度序列化属性恢复 ─────────────────────
            try:
                # QComboBox: 下拉选项
                if isinstance(w, QComboBox) and "combo_items" in info:
                    w.clear()
                    w.addItems(info["combo_items"])
                    idx = info.get("combo_current_index", 0)
                    if 0 <= idx < w.count(): w.setCurrentIndex(idx)
                
                # QTableWidget: 行列数 + 表头
                elif isinstance(w, QTableWidget):
                    rows = info.get("table_row_count", 0)
                    cols = info.get("table_column_count", 0)
                    w.setRowCount(rows); w.setColumnCount(cols)
                    
                    h_headers = info.get("table_h_headers", [])
                    for c in range(min(cols, len(h_headers))):
                        w.setHorizontalHeaderItem(c, QTableWidgetItem(h_headers[c]))
                    
                    v_headers = info.get("table_v_headers", [])
                    for r in range(min(rows, len(v_headers))):
                        w.setVerticalHeaderItem(r, QTableWidgetItem(v_headers[r]))
                
                # QTreeWidget: 列数 + 标题 + 递归节点
                elif isinstance(w, QTreeWidget):
                    col_count = info.get("tree_column_count", 1)
                    w.setColumnCount(col_count)
                    headers = info.get("tree_headers", [f"列{i+1}" for i in range(col_count)])
                    w.setHeaderLabels(headers[:col_count])
                    
                    # 递归恢复树节点的辅助函数
                    def restore_tree_nodes(parent_item, nodes_data):
                        for node_data in nodes_data:
                            texts = node_data.get("texts", [""])
                            item = QTreeWidgetItem(parent_item, texts[:col_count])
                            children = node_data.get("children", [])
                            if children: restore_tree_nodes(item, children)
                    
                    w.clear()
                    restore_tree_nodes(None, info.get("tree_nodes", []))
                
                # QListWidget: 列表项
                elif isinstance(w, QListWidget) and "list_items" in info:
                    w.clear()
                    w.addItems(info["list_items"])
                
                # QTabWidget: 标签页名称
                elif isinstance(w, QTabWidget) and "tab_names" in info:
                    while w.count() > 0: w.removeTab(0)
                    for name in info["tab_names"]:
                        w.addTab(QWidget(), name)
                
                # SVG: 恢复图元数据
                if "_svg_data" in info and hasattr(w, 'load_svg_from_data'):
                    try:
                        svg_data = info["_svg_data"]
                        name = info.get("_svg_name", "svg")
                        w.load_svg_from_data(svg_data, name)
                    except Exception:
                        pass
                        
            except Exception as e:
                print(f"[Load Warning] 恢复 {w.objectName()} 深度属性失败: {e}")

            # ── 3. 容器内子控件递归加载 ──────────────────────
            if "children" in info and hasattr(w, "_content_layout"):
                for child_info in info["children"]:
                    # 注意：容器内子控件由 Layout 管理，此处简化处理
                    # 实际项目中可能需要更复杂的嵌套创建逻辑
                    # 目前主要解决顶层及一级容器的序列化问题
                    pass 

        self._deselect(); self.widget_modified.emit()
    def _find_target_widget(self, obj):
        w = obj
        while w is not None and w is not self:
            if getattr(w, '_is_handle', False): return None
            p = w.parent()
            if p and hasattr(p, '_content_layout'): return w
            if p is self: return None if isinstance(w, _Placeholder) else w
            w = p
        return None

    def _find_canvas_top(self, obj): return self._find_target_widget(obj)

    def _update_status_bar(self, msg=None):
        win = self.window()
        if hasattr(win,"statusBar"):
            undo_hint = " | Ctrl+Z 可撤销" if self.history.can_undo() else ""
            grid_hint = " | 📐 网格:ON" if self._grid_enabled else " | 📐 网格:OFF"
            win.statusBar().showMessage((msg or "就绪 | G键切换网格 | 右键→信号/槽") + grid_hint + undo_hint)

    def _select(self, w, additive=False):
        if additive and w in self._multi_selection:
            self._multi_selection.remove(w)
            self._selected = self._multi_selection[-1] if self._multi_selection else None
        elif additive:
            self._multi_selection.append(w); self._selected = w
        else:
            if self._selected is w and not self._multi_selection: return
            self._deselect(); self._selected = w; self._multi_selection = [w]
        self._update_handles(); self.selection_changed.emit(self._selected); self.update()
        if self._selected:
            g = self._selected.geometry(); lock_icon = " 🔒" if self._selected.property("_locked") else ""
            tag = self._selected.property("_tag") or ""; tag_hint = f" | 🏷️{tag}" if tag else ""
            multi_hint = f" | 多选:{len(self._multi_selection)}" if len(self._multi_selection) > 1 else ""
            self._update_status_bar(f"选中: {self._selected.objectName()}{lock_icon}{tag_hint} | ({g.x()},{g.y()}) | {g.width()}×{g.height()}{multi_hint}")
        else: self._update_status_bar()

    def _deselect(self):
        if not self._selected and not self._multi_selection: return
        self._selected = None; self._multi_selection = []
        for h in self._handles.values(): h.setVisible(False)
        self.selection_changed.emit(None); self.update(); self._update_status_bar()

    def _apply_zoom(self):
        """缩放变化时，把所有子控件的 geometry 按比例重算
        这样鼠标坐标、拖拽、缩放手柄才能与画面一致"""
        z = self._zoom_factor
        prev_z = getattr(self, '_prev_zoom_factor', 1.0)
        if abs(z - prev_z) < 1e-6:
            return
        ratio = z / prev_z
        self._prev_zoom_factor = z
        # 批量调整所有顶层控件（容器内控件由容器元素负责，不单笨处理）
        def rescale_widgets(widgets):
            for w in widgets:
                p = w.parent()
                if p and hasattr(p, '_content_layout'):
                    continue  # 容器内部由布局管理
                g = w.geometry()
                new_g = QRect(
                    int(round(g.x() * ratio)),
                    int(round(g.y() * ratio)),
                    max(10, int(round(g.width() * ratio))),
                    max(10, int(round(g.height() * ratio)))
                )
                w.setGeometry(new_g)
        rescale_widgets(self._canvas_widgets)

    def _update_handles(self):
        w = self._selected
        if not w:
            for h in self._handles.values(): h.setVisible(False); return
        parent = w.parent(); in_container = parent and hasattr(parent, "_content_layout")
        if in_container or w.property("_locked"):
            for h in self._handles.values(): h.setVisible(False); return
        g = w.geometry(); cx, cy = g.x()+g.width()//2, g.y()+g.height()//2
        pm = {"tl":(g.left(),g.top()),"tc":(cx,g.top()),"tr":(g.right(),g.top()),"ml":(g.left(),cy),"mr":(g.right(),cy),"bl":(g.left(),g.bottom()),"bc":(cx,g.bottom()),"br":(g.right(),g.bottom())}
        for n,(hx,hy) in pm.items(): self._handles[n].move(hx-HANDLE_HALF,hy-HANDLE_HALF); self._handles[n].setVisible(True); self._handles[n].raise_()
    
    def paintEvent(self, e):
        super().paintEvent(e)
        if self._preview_mode: return
        
        p = QPainter(self)
        p.scale(self._zoom_factor, self._zoom_factor)
        
        # ── 1. 绘制网格（缓存，限制最大尺寸）────────────────
        if self._grid_enabled:
            cw = min(int(self.width() / self._zoom_factor), 2500)
            ch = min(int(self.height() / self._zoom_factor), 2500)
            if (self._grid_cache is None or self._grid_cache_size != (cw, ch) 
                    or self._grid_cache_zoom != self._zoom_factor):
                try:
                    self._grid_cache = QPixmap(cw + GRID_SIZE, ch + GRID_SIZE)
                    self._grid_cache.fill(Qt.transparent)
                    gp = QPainter(self._grid_cache)
                    gp.setPen(QPen(QColor("#e8e8e8"), 1, Qt.SolidLine))
                    for x in range(0, cw + GRID_SIZE, GRID_SIZE):
                        gp.drawLine(x, 0, x, ch + GRID_SIZE)
                    for y in range(0, ch + GRID_SIZE, GRID_SIZE):
                        gp.drawLine(0, y, cw + GRID_SIZE, y)
                    gp.setPen(QPen(QColor("#d0d0d0"), 1, Qt.SolidLine))
                    big = GRID_SIZE * 5
                    for x in range(0, cw + GRID_SIZE, big):
                        gp.drawLine(x, 0, x, ch + GRID_SIZE)
                    for y in range(0, ch + GRID_SIZE, big):
                        gp.drawLine(0, y, cw + GRID_SIZE, y)
                    gp.end()
                    self._grid_cache_size = (cw, ch)
                    self._grid_cache_zoom = self._zoom_factor
                except Exception:
                    self._grid_cache = None
            if self._grid_cache:
                p.drawPixmap(0, 0, self._grid_cache)
            else:
                # 降级：直接画网格
                p.setPen(QPen(QColor("#e8e8e8"), 1, Qt.SolidLine))
                for x in range(0, cw + GRID_SIZE, GRID_SIZE):
                    p.drawLine(x, 0, x, ch + GRID_SIZE)
                for y in range(0, ch + GRID_SIZE, GRID_SIZE):
                    p.drawLine(0, y, cw + GRID_SIZE, y)
        
        # ── 2. 绘制多选控件边框 ──────────────────────────────
        for w in self._multi_selection:
            if w is self._selected: continue
            p.setPen(QPen(QColor("#4A90D9"), 1, Qt.DashLine))
            p.drawRect(w.geometry().adjusted(-1, -1, 1, 1))
        
        # ── 3. 绘制主选中控件边框 ────────────────────────────
        if self._selected:
            p.setPen(QPen(QColor("#4A90D9"), 2, Qt.DashLine))
            p.drawRect(self._selected.geometry().adjusted(-1, -1, 1, 1))
        
        # ── 4. 智能吸附辅助线（核心修复：区分颜色+单次绘制）──
        if self._snap_guides:
            for axis, pos in self._snap_guides:
                # 根据标记类型选择不同颜色和线型
                if axis.startswith('eq_'):
                    # 🟢 等间距吸附：绿色虚线
                    p.setPen(QPen(QColor("#27AE60"), 2, Qt.DashLine))
                elif axis.startswith('center_'):
                    # 🔵 容器居中：蓝色点线
                    p.setPen(QPen(QColor("#4A90D9"), 1, Qt.DotLine))
                else:
                    # 🔴 普通边缘对齐：红色实线
                    p.setPen(QPen(QColor("#E74C3C"), 1, Qt.SolidLine))
                
                # 判断方向并绘制
                if 'h' in axis or axis == 'x': 
                    p.drawLine(pos, 0, pos, self.height())
                if 'v' in axis or axis == 'y': 
                    p.drawLine(0, pos, self.width(), pos)
        
        # ── 5. 插入指示器 ────────────────────────────────────
        if self._insert_indicator:
            container, y = self._insert_indicator
            cr = container.geometry()
            p.setPen(QPen(QColor("#4A90D9"), 3, Qt.SolidLine))
            p.drawLine(cr.left() + 4, y, cr.right() - 4, y)
        
        # ── 6. 框选矩形 ──────────────────────────────────────
        if self._rubber_band_rect.isValid():
            p.setPen(QPen(QColor("#4A90D9"), 1, Qt.DashLine))
            p.setBrush(QBrush(QColor(74, 144, 217, 30)))
            p.drawRect(self._rubber_band_rect)
        
        # ⚠️ 关键：所有绘制完成后才调用 end()
        p.end()

    def eventFilter(self, obj, event):
        if self._preview_mode:
            if event.type() == QEvent.ShortcutOverride and event.key() == Qt.Key_Escape:
                return False
            return super().eventFilter(obj, event)
        et = event.type()
        if et == QEvent.Wheel and event.modifiers() & Qt.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0: self._zoom_factor = min(2.0, self._zoom_factor + 0.1)
            else: self._zoom_factor = max(0.5, self._zoom_factor - 0.1)
            self._zoom_factor = round(self._zoom_factor, 1)
            self._apply_zoom(); self._update_handles(); self.update()
            win = self.window()
            if hasattr(win, "statusBar"):
                win.statusBar().showMessage(f"🔍 缩放: {int(self._zoom_factor*100)}%  |  Ctrl+滚轮调节")
            return True
        if et == QEvent.ContextMenu:
            target = self._find_target_widget(obj)
            if target:
                if target not in self._multi_selection or len(self._multi_selection) <= 1:
                    self._select(target)
                global_pos = event.globalPos()
                QTimer.singleShot(0, lambda gp=global_pos: self._show_context_menu(gp)); return True
            return super().eventFilter(obj, event)
        is_h = getattr(obj,"_is_handle",False)
        if is_h:
            if et==QEvent.MouseButtonPress and event.button()==Qt.LeftButton and self._selected:
                self._resize_active=True; self._active_handle=obj._handle_pos
                _raw_hm=self.mapFromGlobal(obj.mapToGlobal(event.position().toPoint())); z=self._zoom_factor; self._drag_start_mouse=QPoint(int(_raw_hm.x()/z),int(_raw_hm.y()/z)); self._drag_start_geom=QRect(self._selected.geometry()); return True
            if et==QEvent.MouseMove and self._resize_active:
                _raw_hc=self.mapFromGlobal(obj.mapToGlobal(event.position().toPoint())); z=self._zoom_factor; cur=QPoint(int(_raw_hc.x()/z),int(_raw_hc.y()/z)); g=QRect(self._drag_start_geom)
                dx=cur.x()-self._drag_start_mouse.x(); dy=cur.y()-self._drag_start_mouse.y(); h=self._active_handle
                if "r" in h: g.setRight(max(g.left()+MIN_W,g.right()+dx))
                if "b" in h: g.setBottom(max(g.top()+MIN_H,g.bottom()+dy))
                if "l" in h: g.setLeft(min(g.right()-MIN_W,g.left()+dx))
                if "t" in h: g.setTop(min(g.bottom()-MIN_H,g.top()+dy))
                if self._grid_enabled:
                    g.setX(self._snap_to_grid(g.x())); g.setY(self._snap_to_grid(g.y()))
                    g.setWidth(max(MIN_W, self._snap_to_grid(g.width()))); g.setHeight(max(MIN_H, self._snap_to_grid(g.height())))
                self._selected.setGeometry(g); self._update_handles(); self.update()
                self._update_status_bar(f"缩放: {self._selected.objectName()} | {g.width()}×{g.height()}"); return True
            if et==QEvent.MouseButtonRelease and self._resize_active:
                new_geo = QRect(self._selected.geometry())
                if new_geo != self._drag_start_geom: self.history.push(ResizeWidgetCmd(self, self._selected, QRect(self._drag_start_geom), new_geo)); self.widget_modified.emit()
                self._resize_active=False; self._active_handle=None; g=self._selected.geometry()
                self._update_status_bar(f"选中: {self._selected.objectName()} | ({g.x()},{g.y()}) | {g.width()}×{g.height()}"); return True
            return super().eventFilter(obj, event)
        if et==QEvent.MouseButtonPress and event.button()==Qt.LeftButton:
            target = self._find_target_widget(obj)
            if target:
                ctrl_pressed = bool(event.modifiers() & Qt.ControlModifier)
                # 如果目标已在多选列表中，保持多选状态
                if target in self._multi_selection and len(self._multi_selection) > 1 and not ctrl_pressed:
                    self._selected = target
                else:
                    self._select(target, additive=ctrl_pressed)
                parent = target.parent(); in_container = parent and hasattr(parent, "_content_layout")
                if not in_container and not target.property("_locked"):
                    self._move_active=True; _raw_mp=self.mapFromGlobal(obj.mapToGlobal(event.position().toPoint())); z=self._zoom_factor; self._drag_start_mouse=QPoint(int(_raw_mp.x()/z),int(_raw_mp.y()/z))
                    self._drag_start_geom=QRect(target.geometry())
                    # 多选批量移动：记录所有选中控件的起始几何
                    self._drag_start_geoms = {}
                    for mw in self._multi_selection:
                        p = mw.parent()
                        if not (p and hasattr(p, "_content_layout")) and not mw.property("_locked"):
                            self._drag_start_geoms[id(mw)] = QRect(mw.geometry())
                return True
        if et==QEvent.MouseMove and self._move_active and event.buttons()&Qt.LeftButton and self._selected:
            _raw_cur=self.mapFromGlobal(obj.mapToGlobal(event.position().toPoint())); z=self._zoom_factor; cur=QPoint(int(_raw_cur.x()/z),int(_raw_cur.y()/z)); delta=cur-self._drag_start_mouse
            raw_x = self._drag_start_geom.x()+delta.x(); raw_y = self._drag_start_geom.y()+delta.y()
            test_rect = QRect(raw_x, raw_y, self._selected.width(), self._selected.height())
            guides, snap_x, snap_y, min_dx, min_dy = self._calc_snap_guides(test_rect, self._selected)
            nx = snap_x if (min_dx<=SNAP_THRESHOLD and snap_x is not None) else raw_x
            ny = snap_y if (min_dy<=SNAP_THRESHOLD and snap_y is not None) else raw_y
            if min_dx<=SNAP_THRESHOLD and snap_x is not None:
                diffs = [abs(raw_x-snap_x), abs(raw_x+self._selected.width()//2-snap_x), abs(raw_x+self._selected.width()-snap_x)]
                best = diffs.index(min(diffs))
                if best==0: nx=snap_x
                elif best==1: nx=snap_x-self._selected.width()//2
                else: nx=snap_x-self._selected.width()
            if min_dy<=SNAP_THRESHOLD and snap_y is not None:
                diffs = [abs(raw_y-snap_y), abs(raw_y+self._selected.height()//2-snap_y), abs(raw_y+self._selected.height()-snap_y)]
                best = diffs.index(min(diffs))
                if best==0: ny=snap_y
                elif best==1: ny=snap_y-self._selected.height()//2
                else: ny=snap_y-self._selected.height()
            if min_dx > SNAP_THRESHOLD and self._grid_enabled: nx = self._snap_to_grid(nx)
            if min_dy > SNAP_THRESHOLD and self._grid_enabled: ny = self._snap_to_grid(ny)
            _lw=int(self.width()/self._zoom_factor); _lh=int(self.height()/self._zoom_factor)
            nx=max(0,min(nx,_lw-self._selected.width())); ny=max(0,min(ny,_lh-self._selected.height()))
            # 计算主控件位移，并应用到所有多选控件
            main_dx = nx - self._drag_start_geom.x(); main_dy = ny - self._drag_start_geom.y()
            self._selected.move(nx, ny)
            if hasattr(self, '_drag_start_geoms') and len(self._drag_start_geoms) > 1:
                for mw in self._multi_selection:
                    if mw is self._selected: continue
                    p = mw.parent()
                    if p and hasattr(p, "_content_layout"): continue
                    if mw.property("_locked"): continue
                    sg = self._drag_start_geoms.get(id(mw))
                    if sg is None: continue
                    new_mx = max(0, min(sg.x() + main_dx, self.width() - mw.width()))
                    new_my = max(0, min(sg.y() + main_dy, self.height() - mw.height()))
                    mw.move(new_mx, new_my)
            self._snap_guides=guides; self._update_handles(); self.update()
            count = len(self._multi_selection)
            hint = f"移动: {self._selected.objectName()} ({count}个控件) | ({nx},{ny})" if count > 1 else f"移动: {self._selected.objectName()} | ({nx},{ny})"
            self.selection_changed.emit(self._selected); self._update_status_bar(hint); return True
        if et==QEvent.MouseButtonRelease and self._move_active:
            self._snap_guides=[]
            if hasattr(self, '_drag_start_geoms') and len(self._drag_start_geoms) > 1:
                # 批量移动：收集所有移动的控件，检查是否有实际位移
                moved = []; old_geos = []; new_geos = []
                for mw in self._multi_selection:
                    p = mw.parent()
                    if p and hasattr(p, "_content_layout"): continue
                    if mw.property("_locked"): continue
                    sg = self._drag_start_geoms.get(id(mw))
                    if sg is None: continue
                    new_g = QRect(mw.geometry())
                    if new_g.topLeft() != sg.topLeft():
                        moved.append(mw); old_geos.append(sg); new_geos.append(new_g)
                if moved:
                    self.history.push(BatchAlignCmd(self, moved, old_geos, new_geos))
                    self.widget_modified.emit()
            else:
                if self._selected is not None:
                    new_pos=self._selected.pos(); old_pos=self._drag_start_geom.topLeft()
                    if new_pos!=old_pos: self.history.push(MoveWidgetCmd(self, self._selected, old_pos, new_pos)); self.widget_modified.emit()
            self._move_active=False; self._drag_start_geoms = {}
            g=self._selected.geometry() if self._selected else QRect()
            self._update_status_bar(f"选中: {self._selected.objectName()} | ({g.x()},{g.y()}) | {g.width()}×{g.height()}" if self._selected else ""); return True
        return super().eventFilter(obj, event)

    def mousePressEvent(self, e):
        c = self.childAt(e.position().toPoint())
        if not c or isinstance(c, _Placeholder):
            self._deselect()
            if e.button() == Qt.LeftButton:
                self._rubber_band_active = True
                self._rubber_band_start = e.position().toPoint()
                self._rubber_band_rect = QRect()
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._rubber_band_active and e.buttons() & Qt.LeftButton:
            p = e.position().toPoint()
            self._rubber_band_rect = QRect(
                min(self._rubber_band_start.x(), p.x()),
                min(self._rubber_band_start.y(), p.y()),
                abs(p.x() - self._rubber_band_start.x()),
                abs(p.y() - self._rubber_band_start.y()),
            )
            self.update()
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if self._rubber_band_active and e.button() == Qt.LeftButton:
            self._rubber_band_active = False
            sel = []
            for w in self._canvas_widgets:
                if w.isVisible() and not w.property("_designer_hidden"):
                    if self._rubber_band_rect.intersects(w.geometry()):
                        sel.append(w)
            if sel:
                self._deselect()
                self._multi_selection = sel
                self._selected = sel[-1]
                self._update_handles()
                self.selection_changed.emit(self._selected)
                self._update_status_bar(f"已选中 {len(sel)} 个控件，点击任意一个拖动")
            self._rubber_band_rect = QRect()
            self.update()
        super().mouseReleaseEvent(e)

    def _show_context_menu(self, global_pos):
        w = self._selected
        if not w: return
        menu = QMenu(self); parent = w.parent(); in_container = parent and hasattr(parent, "_content_layout")
        action_map = {}
        act_signals = menu.addAction("🔗 信号/槽编辑器...")
        action_map[act_signals] = "signals"
        menu.addSeparator()
        if in_container:
            ly = parent._content_layout; idx = ly.indexOf(w); count = ly.count()
            act_up = menu.addAction("⬆️ 上移"); act_up.setEnabled(idx>0); action_map[act_up] = "up"
            act_down = menu.addAction("⬇️ 下移"); act_down.setEnabled(idx<count-1); action_map[act_down] = "down"
            menu.addSeparator()
            act_extract = menu.addAction("📤 移出容器"); action_map[act_extract] = "extract"
            menu.addSeparator()
        locked = bool(w.property("_locked"))
        act_lock = menu.addAction(f"{'🔓 解锁' if locked else '🔒 锁定'}"); action_map[act_lock] = "lock"
        hidden = bool(w.property("_designer_hidden"))
        act_hide = menu.addAction(f"{'👁️ 显示' if hidden else '👁️‍🗨️ 隐藏'}"); action_map[act_hide] = "hide"
        menu.addSeparator()
        act_save_template = menu.addAction("📦 另存为模板"); action_map[act_save_template] = "save_template"
        menu.addSeparator()
        act_delete = menu.addAction("🗑️ 删除控件"); action_map[act_delete] = "delete"; menu.addSeparator()
        act_copy_style = menu.addAction("🎨 复制样式"); action_map[act_copy_style] = "copy_style"
        act_paste_style = menu.addAction("🖌️ 粘贴样式")
        act_paste_style.setEnabled(self._style_clipboard is not None)
        action_map[act_paste_style] = "paste_style"; menu.addSeparator()
        act_copy = menu.addAction("📋 复制 objectName"); action_map[act_copy] = "copy"
        menu.addSeparator()
        # 回调函数相关子菜单
        callback_menu = menu.addMenu("✏️ 编辑回调函数")
        # 找出所有与该控件相关的信号/槽连接
        widget_name = w.objectName()
        related_connections = [c for c in self._signal_connections if c["source"] == widget_name]
        if related_connections:
            for conn in related_connections:
                slot_name = conn["slot"]
                has_code = slot_name in self._callback_code and self._callback_code[slot_name].strip()
                label = f"  {slot_name}" + (" ✅" if has_code else "")
                act_cb = callback_menu.addAction(label)
                act_cb.setData(slot_name)
                action_map[act_cb] = ("edit_callback", slot_name)
        else:
            # 没有关联连接也显示一个提示项（点击后打开信号/槽编辑器）
            act_no_conn = callback_menu.addAction(" (暂无连接，请先添加信号/槽...)")
            act_no_conn.setEnabled(False)
            action_map[act_no_conn] = "noop"
        chosen = menu.exec(global_pos)
        if chosen is None or chosen not in action_map: return
        at = action_map[chosen]
        if isinstance(at, tuple) and at[0] == "edit_callback":
            slot_name = at[1]
            existing_code = self._callback_code.get(slot_name, "")
            dlg = CallbackEditorDialog(self, slot_name, existing_code, self.window())
            if dlg.exec() == QDialog.Accepted:
                self._callback_code[slot_name] = dlg.get_code()
                self.widget_modified.emit()
        elif at == "signals":
            dlg = SignalSlotDialog(self, self.window()); dlg.exec()
        elif at == "up": ly=parent._content_layout; idx=ly.indexOf(w); self.history.push(ReorderWidgetCmd(parent,w,idx,idx-1)); self.widget_modified.emit()
        elif at == "down": ly=parent._content_layout; idx=ly.indexOf(w); self.history.push(ReorderWidgetCmd(parent,w,idx,idx+1)); self.widget_modified.emit()
        elif at == "extract": ly=parent._content_layout; idx=ly.indexOf(w); self.history.push(ExtractWidgetCmd(self,w,parent,idx)); self._deselect()
        elif at == "lock": self._toggle_lock()
        elif at == "hide": self._toggle_hide()
        elif at == "delete": self._delete_selected()
        elif at == "copy_style": self._copy_style()
        elif at == "paste_style": self._paste_style()
        elif at == "copy": QApplication.clipboard().setText(w.objectName())
        elif at == "save_template": self._save_as_template(w)

    def _delete_selected(self):
        if not self._selected: return
        self.history.push(DeleteWidgetCmd(self, self._selected)); self.widget_modified.emit()

    def clear_canvas(self):
        self._deselect()
        for p in self._pages:
            for w in list(p["widgets"]): w.hide(); w.deleteLater()
        self._pages = [{"name": "页面1", "widgets": []}]
        self._current_page = 0
        self._canvas_widgets = self._pages[0]["widgets"]
        self._signal_connections.clear()
        self._callback_code.clear()
        self._placeholder.setVisible(True); self.widget_modified.emit()


# ── 属性编辑器 ───────────────────────────────────────────────────
class PropertyEditor(QWidget):
    property_changed = Signal()
    def __init__(self, parent=None):
        super().__init__(parent); layout = QVBoxLayout(self); layout.setContentsMargins(0,0,0,0)
        self.header = QLabel("<b>属性面板</b>"); self.header.setStyleSheet("padding:4px 8px; font-size:13px;"); layout.addWidget(self.header)
        self.table = QTableWidget(0, 2); self.table.setHorizontalHeaderLabels(["属性", "值"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed)
        self.table.setStyleSheet("QTableWidget{gridline-color:#ddd;font-size:12px;} QTableWidget::item{padding:4px;}")
        layout.addWidget(self.table); self._widget = None; self._batch_widgets = []; self._busy = False
        self.table.cellChanged.connect(self._on_cell_changed)
        self.table.cellDoubleClicked.connect(self._on_cell_double_clicked)


    def set_widget(self, widget=None): self._widget = widget; self._batch_widgets = []; self._refresh()
    def set_batch_widgets(self, widgets): self._widget = None; self._batch_widgets = list(widgets); self._refresh()

    def _get_widget_value(self, w, prop):
        try:
            if prop == "objectName": return w.objectName()
            elif prop == "text": return w.text() if hasattr(w, "text") else None
            elif prop == "title": return w.title() if hasattr(w, "title") else None
            elif prop == "placeholderText": return w.placeholderText() if hasattr(w, "placeholderText") else None
            elif prop == "role": return w.property("role") or "default"
            elif prop == "tag": return w.property("_tag") or ""
            elif prop == "styleSheet": return w.styleSheet()
            elif prop == "value": return str(w.value()) if hasattr(w, "value") and callable(w.value) else None
            elif prop == "width": return str(w.width())
            elif prop == "height": return str(w.height())
            elif prop == "minWidth": return str(w.minimumWidth())
            elif prop == "minHeight": return str(w.minimumHeight())
            elif prop == "maxWidth": return str(w.maximumWidth())
            elif prop == "maxHeight": return str(w.maximumHeight())
        except: return None
        return None

    def _refresh(self):
        self._busy = True; self.table.setRowCount(0)
        if self._batch_widgets and len(self._batch_widgets) >= 2:
            self.header.setText(f"<b>批量编辑 ({len(self._batch_widgets)} 个控件)</b>"); self._refresh_batch(); self._busy = False; return
        self.header.setText("<b>属性面板</b>")
        w = self._widget
        if not w: self._busy = False; return
        
        props = [("objectName", w.objectName(), True)]
        if isinstance(w, BINDABLE_WIDGETS) or hasattr(w, 'setValue'):
            props.append(("tag", w.property("_tag") or "", True))
        
        # 【核心修复】获取类名用于后续判断
        cls_name = type(w).__name__
        roles = WIDGET_ROLES.get(cls_name, [])
        if roles: props.append(("role", w.property("role") or "default", True))
        
        if hasattr(w,"text") and not isinstance(w,(QGroupBox,QDialogButtonBox)):
            props.append(("text", w.text(), True))
        if hasattr(w,"title") and isinstance(w,QGroupBox):
            props.append(("title", w.title(), True))
        if hasattr(w,"title") and callable(getattr(w,"title",None)) and not isinstance(w,QGroupBox):
            props.append(("title", w.title(), True))
        if hasattr(w, 'setGaugeTitle'):
            props.append(("title", w._title, True))
        if hasattr(w, 'setUnit'):
            props.append(("unit", w._unit, True))
        if isinstance(w,(QLineEdit,QWTextEdit)):
            props.append(("placeholderText", w.placeholderText(), True))
        if hasattr(w,"value") and callable(getattr(w,"value",None)):
            props.append(("value", str(w.value()), True))
            
        parent = w.parent(); in_container = parent and hasattr(parent, "_content_layout")
        if in_container:
            sp = w.sizePolicy()
            props.append(("hSizePolicy", _policy_to_str(sp.horizontalPolicy()), True))
            props.append(("vSizePolicy", _policy_to_str(sp.verticalPolicy()), True))
            props.append(("minWidth", str(w.minimumWidth()), True))
            props.append(("minHeight", str(w.minimumHeight()), True))
            props.append(("maxWidth", str(w.maximumWidth()), True))
            props.append(("maxHeight", str(w.maximumHeight()), True))
        else:
            g = w.geometry()
            props += [("x",str(g.x()),True),("y",str(g.y()),True),("width",str(g.width()),True),("height",str(g.height()),True)]
            
        props.append(("anchor_left", "✓" if w.property("_anchor_left") else "", True))
        props.append(("anchor_right", "✓" if w.property("_anchor_right") else "", True))
        props.append(("anchor_top", "✓" if w.property("_anchor_top") else "", True))
        props.append(("anchor_bottom", "✓" if w.property("_anchor_bottom") else "", True))
        props.append(("styleSheet", w.styleSheet(), True))
        
        if hasattr(w, "_content_layout"):
            ly = w._content_layout; margins = ly.contentsMargins()
            props.append(("marginLeft", str(margins.left()), True))
            props.append(("marginTop", str(margins.top()), True))
            props.append(("marginRight", str(margins.right()), True))
            props.append(("marginBottom", str(margins.bottom()), True))
            props.append(("spacing", str(ly.spacing()), True))

        # ══════════════════════════════════════════════════════════════
        # 【核心修复】判断条件改为 MultiTrendWidget
        # ══════════════════════════════════════════════════════════════
        if cls_name == "MultiTrendWidget":
            props += [
            ("x_range", str(getattr(w, '_x_range', 60)), True),
            ("y_min", str(getattr(w, '_y_min', 0.0)), True),
            ("y_max", str(getattr(w, '_y_max', 100.0)), True),
            ("auto_scale_y", "✓" if getattr(w, '_auto_scale_y', False) else "", True),
            ("grid_density_x", str(getattr(w, '_grid_density_x', 6)), True),
            ("grid_density_y", str(getattr(w, '_grid_density_y', 5)), True),
            ("bg_color", getattr(w, '_bg_color', QColor("#1a1a2e")).name(), True),
            ("grid_color", getattr(w, '_grid_color', QColor("#333355")).name(), True),
            ("text_color", getattr(w, '_text_color', QColor("#aaaacc")).name(), True),
        ]  
        self._render_props(props, w); self._busy = False

    def _refresh_batch(self):
        widgets = self._batch_widgets
        candidate_props = [
            ("role", lambda w: type(w).__name__ in WIDGET_ROLES),
            ("text", lambda w: hasattr(w, "text") and not isinstance(w, (QGroupBox, QDialogButtonBox))),
            ("title", lambda w: hasattr(w, "title") and isinstance(w, QGroupBox)),
            ("placeholderText", lambda w: isinstance(w, (QLineEdit, QWTextEdit))),
            ("tag", lambda w: isinstance(w, BINDABLE_WIDGETS) or hasattr(w, 'setValue')),
            ("width", lambda w: True), ("height", lambda w: True),
            ("minWidth", lambda w: True), ("minHeight", lambda w: True),
            ("maxWidth", lambda w: True), ("maxHeight", lambda w: True),
            ("styleSheet", lambda w: True),
        ]
        props = []
        for prop_name, condition in candidate_props:
            applicable = [w for w in widgets if condition(w)]
            if not applicable: continue
            values = [self._get_widget_value(w, prop_name) for w in applicable]
            values = [v for v in values if v is not None]
            if not values: continue
            all_same = all(v == values[0] for v in values)
            display_val = values[0] if all_same else "(混合)"
            props.append((prop_name, display_val, True))
        if not props:
            self.table.setRowCount(1)
            ki = QTableWidgetItem("提示"); ki.setFlags(ki.flags() & ~Qt.ItemIsEditable); ki.setBackground(QColor("#f0f0f0")); self.table.setItem(0, 0, ki)
            vi = QTableWidgetItem("选中控件无公共可编辑属性"); vi.setFlags(vi.flags() & ~Qt.ItemIsEditable); vi.setForeground(QColor("#999")); self.table.setItem(0, 1, vi)
            return
        self._render_props(props, None)

    # 属性分组定义
    PROP_GROUPS = {
        "📐 位置与尺寸": ("x", "y", "width", "height", "anchor_left", "anchor_right", "anchor_top", "anchor_bottom"),
        "🎨 样式": ("role", "styleSheet"),
        "📝 内容与标识": ("objectName", "text", "title", "placeholderText", "value", "tag", "unit"),
        "📏 大小策略": ("minWidth", "minHeight", "maxWidth", "maxHeight", "hSizePolicy", "vSizePolicy"),
        "📦 容器边距": ("marginLeft", "marginTop", "marginRight", "marginBottom", "spacing"),
    }

    def _get_group(self, prop_name):
        for group_name, props in self.PROP_GROUPS.items():
            if prop_name in props:
                return group_name
        return "其他"

    def _render_props(self, props, single_widget):
        row = 0
        current_group = None
        for prop, value, _ in props:
            group = self._get_group(prop)
            if group != current_group:
                current_group = group
                # 插入分组标题行
                self.table.insertRow(row)
                ki = QTableWidgetItem(f"── {group} ──")
                ki.setFlags(Qt.NoItemFlags)
                f = ki.font(); f.setBold(True); f.setPointSize(10)
                ki.setFont(f); ki.setBackground(QColor("#e0e0e0"))
                self.table.setItem(row, 0, ki)
                vi = QTableWidgetItem("")
                vi.setFlags(Qt.NoItemFlags); vi.setBackground(QColor("#e0e0e0"))
                self.table.setItem(row, 1, vi)
                row += 1

            self.table.insertRow(row)
            ki = QTableWidgetItem(prop); ki.setFlags(ki.flags() & ~Qt.ItemIsEditable); ki.setBackground(QColor("#f5f5f5")); self.table.setItem(row, 0, ki)
            if prop == "objectName" and single_widget:
                vi = QTableWidgetItem(str(value) if value is not None else "")
                is_auto = single_widget.property("_auto_objectName")
                if is_auto: f = vi.font(); f.setItalic(True); vi.setFont(f); vi.setForeground(QColor("#999")); vi.setToolTip("此为自动生成的临时名称，设置tag后将自动同步为语义化名称")
                self.table.setItem(row, 1, vi)
            elif prop in ("anchor_left", "anchor_right", "anchor_top", "anchor_bottom") and single_widget:
                cb = QCheckBox(); cb.setChecked(value == "✓"); cb.stateChanged.connect(lambda state, widget=single_widget, p=prop: self._on_anchor_changed(widget, p, state)); self.table.setCellWidget(row, 1, cb)
            elif prop == "role":
                if single_widget: roles = WIDGET_ROLES.get(type(single_widget).__name__, [])
                elif self._batch_widgets:
                    all_roles = set()
                    for bw in self._batch_widgets:
                        rn = type(bw).__name__
                        if rn in WIDGET_ROLES: all_roles.update(WIDGET_ROLES[rn])
                    roles = sorted(all_roles)
                else: roles = []
                combo = QComboBox(); combo.addItems(roles)
                if value != "(混合)": combo.setCurrentText(value)
                combo.currentTextChanged.connect(lambda text, p=prop: self._on_combo_changed(p, text)); self.table.setCellWidget(row, 1, combo)
            elif prop in ("hSizePolicy", "vSizePolicy") and single_widget:
                combo = QComboBox(); combo.addItems(SIZE_POLICY_NAMES); combo.setCurrentText(value)
                combo.currentTextChanged.connect(lambda text, widget=single_widget, p=prop: self._on_size_policy_changed(widget, p, text)); self.table.setCellWidget(row, 1, combo)
            else:
                vi = QTableWidgetItem(str(value) if value is not None else "")
                if value == "(混合)": vi.setForeground(QColor("#999")); f = vi.font(); f.setItalic(True); vi.setFont(f)
                self.table.setItem(row, 1, vi)
            row += 1

    def _on_combo_changed(self, prop, value):
        if self._busy: return
        if self._batch_widgets and len(self._batch_widgets) >= 2: self._apply_batch_property(prop, value)
        elif self._widget and prop == "role": self._on_role_changed(self._widget, value)

    def _apply_batch_property(self, prop, value):
        if not self._batch_widgets: return
        canvas = self._batch_widgets[0].parent()
        while canvas and not isinstance(canvas, DesignerCanvas): canvas = canvas.parent()
        if not canvas: return
        old_vals, applicable_widgets = [], []
        for w in self._batch_widgets:
            ov = self._get_widget_value(w, prop)
            if ov is not None: old_vals.append(ov); applicable_widgets.append(w)
        if not applicable_widgets: return
        canvas.history.push(BatchPropertyChangeCmd(canvas, applicable_widgets, prop, old_vals, value))
        canvas.widget_modified.emit(); self.property_changed.emit()

    def _on_anchor_changed(self, widget, prop, state):
        if self._busy or not widget: return
        checked = state == Qt.Checked; old_val = "✓" if widget.property(f"_{prop}") else ""; new_val = "✓" if checked else ""
        if old_val == new_val: return
        canvas = widget.parent()
        while canvas and not isinstance(canvas, DesignerCanvas): canvas = canvas.parent()
        if canvas: canvas.history.push(PropertyChangeCmd(canvas, widget, prop, old_val, new_val))
        self.property_changed.emit()

    def _on_role_changed(self, widget, role):
        if self._busy or not widget: return
        old_role = widget.property("role") or "default"
        if old_role == role: return
        canvas = widget.parent()
        while canvas and not isinstance(canvas, DesignerCanvas): canvas = canvas.parent()
        if canvas: canvas.history.push(PropertyChangeCmd(canvas, widget, "role", old_role, role))
        self.property_changed.emit()

    def _on_size_policy_changed(self, widget, prop, policy_name):
        if self._busy or not widget or policy_name not in SIZE_POLICY_MAP: return
        sp = widget.sizePolicy(); old_val = _policy_to_str(sp.horizontalPolicy()) if prop=="hSizePolicy" else _policy_to_str(sp.verticalPolicy())
        if old_val == policy_name: return
        canvas = widget.parent()
        while canvas and not isinstance(canvas, DesignerCanvas): canvas = canvas.parent()
        if canvas: canvas.history.push(PropertyChangeCmd(canvas, widget, prop, old_val, policy_name))
        self.property_changed.emit()
    # 新增方法：
    def _on_cell_double_clicked(self, row, col):
        """双击 styleSheet 字段时打开可视化 QSS 构建器"""
        if col != 1:
            return
        prop_item = self.table.item(row, 0)
        if not prop_item or prop_item.text() != "styleSheet":
            return
        if not self._widget:
            return
        
        dlg = QssBuilderDialog(self._widget, self.window())
        if dlg.exec() == QDialog.Accepted:
            new_qss = dlg.get_qss()
            # 通过正常的属性修改流程写入，支持撤销
            canvas = self._widget.parent()
            while canvas and not isinstance(canvas, DesignerCanvas):
                canvas = canvas.parent()
            if canvas:
                old_qss = self._widget.styleSheet()
                canvas.history.push(PropertyChangeCmd(canvas, self._widget, "styleSheet", old_qss, new_qss))
                self._refresh()
                self.property_changed.emit()
    def _on_cell_changed(self, row, col):
        if self._busy or col != 1: return
        prop = self.table.item(row, 0).text()
        if prop in ("role", "hSizePolicy", "vSizePolicy", "anchor_left", "anchor_right", "anchor_top", "anchor_bottom"): return
        value = self.table.item(row, 1).text()
        if self._batch_widgets and len(self._batch_widgets) >= 2: self._apply_batch_property(prop, value); return
        if not self._widget: return
        canvas = self._widget.parent()
        while canvas and not isinstance(canvas, DesignerCanvas): canvas = canvas.parent()
        if not canvas: return
        old_val = ""; w = self._widget
        try:
            if prop == "objectName": old_val = w.objectName(); w.setProperty("_auto_objectName", False)
            elif prop == "tag":
                old_val = w.property("_tag") or ""
                if value and w.property("_auto_objectName"):
                    new_obj_name = _sanitize(value); existing_names = set()
                    for cw in canvas._canvas_widgets:
                        if cw is not w: existing_names.add(cw.objectName())
                    final_name = new_obj_name; suffix = 1
                    while final_name in existing_names: final_name = f"{new_obj_name}_{suffix}"; suffix += 1
                    w.setObjectName(final_name); w.setProperty("_auto_objectName", False)
            elif prop == "text": old_val = w.text() if hasattr(w,"text") else ""
            elif prop == "title":
                if hasattr(w, "setGaugeTitle"): old_val = w._title
                elif hasattr(w, "title") and callable(getattr(w, "title", None)): old_val = w.title()
                else: old_val = ""
            elif prop == "unit" and hasattr(w, "setUnit"): old_val = w._unit
            elif prop == "placeholderText": old_val = w.placeholderText() if hasattr(w,"placeholderText") else ""
            elif prop == "value": old_val = str(w.value()) if hasattr(w,"value") and callable(w.value) else ""
            elif prop in ("x","y","width","height"): g = w.geometry(); old_val = str({"x":g.x(),"y":g.y(),"width":g.width(),"height":g.height()}[prop])
            elif prop == "minWidth": old_val = str(w.minimumWidth())
            elif prop == "minHeight": old_val = str(w.minimumHeight())
            elif prop == "maxWidth": old_val = str(w.maximumWidth())
            elif prop == "maxHeight": old_val = str(w.maximumHeight())
            elif prop in ("marginLeft", "marginTop", "marginRight", "marginBottom") and hasattr(w, "_content_layout"):
                m = w._content_layout.contentsMargins()
                vals = {"marginLeft": m.left(), "marginTop": m.top(), "marginRight": m.right(), "marginBottom": m.bottom()}
                old_val = str(vals.get(prop, 0))
            elif prop == "spacing" and hasattr(w, "_content_layout"):
                old_val = str(w._content_layout.spacing())
            elif prop == "styleSheet": old_val = w.styleSheet()
        except: old_val = ""
        if str(old_val) == value: return
        canvas.history.push(PropertyChangeCmd(canvas, w, prop, old_val, value))
        self._refresh(); self.property_changed.emit()

    def refresh(self): self._refresh()


# ── 主窗口 ───────────────────────────────────────────────────────
class DesignerMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mini Designer v20 ")
        self._current_file = None; self._ui_class_mode = False; self._custom_widget_files = []
        self._setup_ui()
        # 全局快捷键
        QShortcut(QKeySequence("Ctrl+S"), self).activated.connect(self._save_project)
        QShortcut(QKeySequence("Ctrl+N"), self).activated.connect(self._new_project)
        QShortcut(QKeySequence("Ctrl+O"), self).activated.connect(self._load_project)
        QApplication.instance().setStyle(QStyleFactory.create("Fusion"))
        QApplication.instance().setStyleSheet(ACTIVE_QSS)
        self._wire(); self._restore_state()
        self._auto_load_custom_widgets()

    def _setup_ui(self):
        central = QWidget(); self.setCentralWidget(central)
        root = QVBoxLayout(central); root.setContentsMargins(4, 4, 4, 4); root.setSpacing(0)
        self.align_toolbar = QToolBar("对齐工具"); self.align_toolbar.setMovable(False)
        for label, at in [("⬅️左","left"),("➡️右","right"),("⬆️顶","top"),("⬇️底","bottom"),
                          ("↔️水平居中","hcenter"),("↕️垂直居中","vcenter"),
                          ("═等宽","same_width"),("║等高","same_height"),
                          ("⋯水平等距","distribute_h"),("⋮垂直等距","distribute_v")]:
            action = self.align_toolbar.addAction(label)
            action.triggered.connect(lambda checked, a=at: self.canvas.align_widgets(a))
        self.align_toolbar.addSeparator()
        self.grid_action = self.align_toolbar.addAction("📐 网格:ON")
        self.grid_action.setCheckable(True); self.grid_action.setChecked(True)
        self.grid_action.triggered.connect(self._toggle_grid_action)
        self.addToolBar(Qt.TopToolBarArea, self.align_toolbar)
        top_split = QSplitter(Qt.Horizontal)
        self.toolbox = WidgetToolbox(); self.canvas = DesignerCanvas(); self.props = PropertyEditor()
        self.props.setMinimumWidth(220); self.props.setMaximumWidth(400)

        # 左侧面板：工具箱 + 控件树 + 项目
        left_tabs = QTabWidget()
        left_tabs.addTab(self.toolbox, "🧰 工具箱")
        self.widget_tree = WidgetTreePanel(self.canvas)
        left_tabs.addTab(self.widget_tree, "📁 控件树")


        # 右侧面板：属性编辑器 + 数据模拟器 + 通信调试
        right_tabs = QTabWidget()
        right_tabs.addTab(self.props, "📋 属性")
        self.data_sim = DataSimulatorPanel(self.canvas)
        right_tabs.addTab(self.data_sim, "🔬 模拟器")
        self.history_panel = UndoHistoryPanel(self.canvas)
        right_tabs.addTab(self.history_panel, "📜 历史")
        from comm_debug import CommDebugPanel
        self.comm_panel = CommDebugPanel(self.canvas)
        right_tabs.addTab(self.comm_panel, "🔌 通信")

        # 画布区域 + 页面标签栏
        canvas_area = QWidget()
        canvas_area_layout = QVBoxLayout(canvas_area)
        canvas_area_layout.setContentsMargins(0, 0, 0, 0); canvas_area_layout.setSpacing(0)

        # 页面标签栏
        page_bar = QWidget()
        page_bar.setStyleSheet("background:#e8e8e8;border-bottom:1px solid #ccc;")
        page_bar_layout = QHBoxLayout(page_bar)
        page_bar_layout.setContentsMargins(4, 2, 4, 2); page_bar_layout.setSpacing(2)
        self.page_tabs = QTabBar()
        self.page_tabs.setTabsClosable(True)
        self.page_tabs.setMovable(True)
        self.page_tabs.setExpanding(False)
        self.page_tabs.setToolTip("双击标签可重命名 | 拖拽可排序 | 点击 ⨉ 删除")
        self.page_tabs.setStyleSheet("""
            QTabBar::tab{min-width:80px;padding:6px 14px;font-size:12px;font-weight:bold;background:#c8c8c8;border:1px solid #aaa;border-bottom:none;border-radius:6px 6px 0 0;margin-right:3px;color:#333;}
            QTabBar::tab:selected{background:#fff;color:#4A90D9;border-bottom:2px solid #4A90D9;}
            QTabBar::tab:hover{background:#d8d8d8;}
        """)
        self.page_tabs.addTab("页面1")
        btn_add_page = QPushButton("＋ 新建页")
        btn_add_page.setMinimumWidth(80)
        btn_add_page.setStyleSheet("QPushButton{background:#4A90D9;color:#fff;border:none;border-radius:4px;padding:3px 10px;font-size:12px;font-weight:bold;} QPushButton:hover{background:#357ABD;}")
        page_bar_layout.addWidget(self.page_tabs)
        page_bar_layout.addWidget(btn_add_page)
        page_bar_layout.addStretch()
        canvas_area_layout.addWidget(page_bar)

        # QScrollArea 包裹画布
        self.canvas_scroll = QScrollArea()
        self.canvas_scroll.setWidgetResizable(False)
        self.canvas_scroll.setWidget(self.canvas)
        self.canvas_scroll.setStyleSheet("QScrollArea{background:#e0e0e0;border:none;}")
        self.canvas.setMinimumSize(DESIGN_WIDTH, DESIGN_HEIGHT)
        canvas_area_layout.addWidget(self.canvas_scroll)

        # 连接页面信号
        self.page_tabs.currentChanged.connect(self._on_page_tab_changed)
        self.page_tabs.tabCloseRequested.connect(self._on_page_close)
        self.page_tabs.tabBarDoubleClicked.connect(self._on_page_rename)
        btn_add_page.clicked.connect(self._on_add_page)

        top_split.addWidget(left_tabs); top_split.addWidget(canvas_area); top_split.addWidget(right_tabs)
        top_split.setSizes([200, 700, 300])
        bottom = QWidget()
        bl = QVBoxLayout(bottom); bl.setContentsMargins(0, 4, 0, 0); bl.setSpacing(4)

        # 底部工具栏 — 拆成两行防止太挤
        BUTTON_STYLE = "QToolButton{padding:4px 8px;font-size:11px;}"
        BOLD_STYLE = "QToolButton{padding:4px 8px;font-size:11px;font-weight:bold;}"

        self.toolbar_row1 = QToolBar("常用工具栏"); self.toolbar_row1.setMovable(False)
        self.toolbar_row1.setStyleSheet("QToolBar{spacing:2px;padding:1px 4px;border:none;}")
        self.btn_template = self._add_tb_btn2(self.toolbar_row1, "🏭 模板", BUTTON_STYLE)
        self.btn_undo = self._add_tb_btn2(self.toolbar_row1, "↩ 撤销", BUTTON_STYLE); self.btn_undo.setEnabled(False)
        self.btn_redo = self._add_tb_btn2(self.toolbar_row1, "↪ 重做", BUTTON_STYLE); self.btn_redo.setEnabled(False)
        self.btn_canvas_size = self._add_tb_btn2(self.toolbar_row1, "📐 800×600", BUTTON_STYLE)
        self.toolbar_row1.addSeparator()
        self.btn_preview = self._add_tb_btn2(self.toolbar_row1, "🔍 预览",
            "QToolButton{background:#27AE60;color:#fff;border:none;padding:4px 8px;border-radius:4px;font-weight:bold;font-size:11px;} QToolButton:hover{background:#219A52;} QToolButton:checked{background:#E74C3C;}")
        self.btn_preview.setCheckable(True)
        bl.addWidget(self.toolbar_row1)

        self.toolbar_row2 = QToolBar("工具/文件"); self.toolbar_row2.setMovable(False)
        self.toolbar_row2.setStyleSheet("QToolBar{spacing:2px;padding:1px 4px;border:none;}")
        self.btn_dark = self._add_tb_btn2(self.toolbar_row2, "🌙 暗色", BUTTON_STYLE); self.btn_dark.setCheckable(True)
        self.btn_custom = self._add_tb_btn2(self.toolbar_row2, "🧩 自定义控件", BUTTON_STYLE)
        self.btn_theme = self._add_tb_btn2(self.toolbar_row2, "🎨 主题", BUTTON_STYLE)
        self.btn_ui_class = self._add_tb_btn2(self.toolbar_row2, "🪟 独立窗口", BUTTON_STYLE); self.btn_ui_class.setCheckable(True)
        self.btn_fixed = self._add_tb_btn2(self.toolbar_row2, "🔒 固定画布", BUTTON_STYLE); self.btn_fixed.setCheckable(True)
        self.toolbar_row2.addSeparator()
        self.btn_save = self._add_tb_btn2(self.toolbar_row2, "💾 保存", BUTTON_STYLE)
        self.btn_load = self._add_tb_btn2(self.toolbar_row2, "📂 打开", BUTTON_STYLE)
        self.btn_export_project = self._add_tb_btn2(self.toolbar_row2, "📦 导出", BUTTON_STYLE)
        self.btn_export_qss = self._add_tb_btn2(self.toolbar_row2, "导出 QSS", BUTTON_STYLE)
        self.toolbar_row2.addSeparator()
        self.btn_clear = self._add_tb_btn2(self.toolbar_row2, "🗑️ 清空", BUTTON_STYLE)
        bl.addWidget(self.toolbar_row2)
        code_header = QWidget(); code_header_l = QHBoxLayout(code_header)
        code_header_l.setContentsMargins(4, 0, 4, 2); code_header_l.setSpacing(6)
        code_label = QLabel("<b>生成代码</b>"); code_label.setStyleSheet("font-size: 12px; color: #555;")
        code_header_l.addWidget(code_label); code_header_l.addStretch()
        self.btn_copy = QPushButton("📋 复制代码"); self.btn_copy.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        code_header_l.addWidget(self.btn_copy)
        bl.addWidget(code_header)
        self.code_view = QTextEdit(); self.code_view.setReadOnly(True)
        self.code_view.setStyleSheet("QTextEdit{background:#1e1e1e;color:#d4d4d4;font-family:'Consolas',monospace;font-size:12px;border:1px solid #333;border-radius:4px;}")
        self.code_view.setMinimumHeight(60)
        bl.addWidget(self.code_view)
        self.main_split = QSplitter(Qt.Vertical); self.main_split.addWidget(top_split); self.main_split.addWidget(bottom)
        self.main_split.setSizes([600, 300]); root.addWidget(self.main_split)
        self.statusBar().showMessage("就绪 | G键切换网格 | 右键→信号/槽 | Ctrl+Z/Y")
        self.statusBar().setStyleSheet("QStatusBar { font-size: 11px; color: #666; border-top: 1px solid #e0e0e0; }")

    def _add_tb_btn(self, text, style=""):
        """创建工具栏按钮，保证最小宽度防止文字被截断"""
        btn = QToolButton()
        btn.setText(text)
        btn.setToolButtonStyle(Qt.ToolButtonTextOnly)
        if style: btn.setStyleSheet(style)
        fm = btn.fontMetrics()
        btn.setMinimumWidth(fm.horizontalAdvance(text) + 20)
        self.bottom_toolbar.addWidget(btn)
        return btn

    def _add_tb_btn2(self, toolbar, text, style=""):
        """创建工具栏按钮（指定 toolbar）"""
        btn = QToolButton()
        btn.setText(text)
        btn.setToolButtonStyle(Qt.ToolButtonTextOnly)
        if style: btn.setStyleSheet(style)
        fm = btn.fontMetrics()
        btn.setMinimumWidth(fm.horizontalAdvance(text) + 16)
        toolbar.addWidget(btn)
        return btn

    def _auto_load_custom_widgets(self):
        settings = QSettings("MiniDesigner", "v19")
        saved_paths = settings.value("custom_widget_paths", [])
        if saved_paths and isinstance(saved_paths, list):
            valid_paths = [p for p in saved_paths if os.path.isfile(p)]
            if valid_paths:
                count = CustomWidgetLoader.register_widgets(valid_paths)
                self._custom_widget_files = valid_paths
                self.toolbox.populate()
                self.statusBar().showMessage(f"✅ 自动加载 {count} 个自定义控件")

    def _restore_state(self):
        settings = QSettings("MiniDesigner", "v19"); saved_geom = settings.value("window_geometry")
        if saved_geom: self.restoreGeometry(saved_geom)
        else:
            screen = QApplication.primaryScreen().availableGeometry(); w,h = int(screen.width()*0.85), int(screen.height()*0.85)
            self.setGeometry((screen.width()-w)//2, (screen.height()-h)//2, w, h)
        ms = settings.value("main_split_sizes")
        if ms: self.main_split.restoreState(ms)
        ts = settings.value("top_split_sizes")
        if ts:
            t = self.main_split.widget(0)
            if isinstance(t, QSplitter): t.restoreState(ts)
        # 恢复暗色模式
        dark = settings.value("dark_mode", False)
        if isinstance(dark, str):
                dark = dark.lower() == "true"
        if dark:
                self.btn_dark.setChecked(True)
                self._toggle_dark_mode(True)

    def closeEvent(self, event):
        """安全关闭窗口，防止保存配置时触发 KeyboardInterrupt 报错"""
        try:
            settings = QSettings("MiniDesigner", "v19")
            settings.setValue("window_geometry", self.saveGeometry())
            settings.setValue("dark_mode", DARK_MODE)
            settings.setValue("main_split_sizes", self.main_split.saveState())
            
            t = self.main_split.widget(0)
            if isinstance(t, QSplitter): 
                settings.setValue("top_split_sizes", t.saveState())
                
            settings.setValue("custom_widget_paths", self._custom_widget_files)
        except (KeyboardInterrupt, SystemExit):
            # 如果是用户主动中断或系统退出，静默忽略，避免控制台报错
            pass
        except Exception as e:
            # 其他异常可以打印日志，但不阻塞关闭
            print(f"[Warning] 保存窗口配置失败: {e}")
        finally:
            # 确保父类的 closeEvent 始终被调用，保证窗口正常关闭
            super().closeEvent(event)

    def _wire(self):
        def on_selection_changed(widget):
            if len(self.canvas._multi_selection) >= 2: self.props.set_batch_widgets(self.canvas._multi_selection)
            else: self.props.set_widget(widget)
        self.canvas.selection_changed.connect(on_selection_changed)
        self.canvas.widget_modified.connect(self._refresh_code); self.canvas.widget_modified.connect(self.props.refresh)
        self.canvas.widget_modified.connect(self._update_undo_redo_state)
        self.canvas.widget_modified.connect(self.history_panel.refresh)
        self.btn_undo.clicked.connect(self.canvas.undo); self.btn_redo.clicked.connect(self.canvas.redo)
        self.props.property_changed.connect(self._refresh_code)
        self.props.property_changed.connect(lambda: (self.canvas._update_handles(), self.canvas.update()))
        self.btn_copy.clicked.connect(self._copy_code); self.btn_clear.clicked.connect(self._clear)
        self.btn_export_qss.clicked.connect(self._export_qss); self.btn_export_project.clicked.connect(self._export_project)
        self.btn_save.clicked.connect(self._save_project)
        self.btn_load.clicked.connect(self._load_project)
        self.btn_ui_class.toggled.connect(self._toggle_ui_class_mode)
        self.btn_fixed.toggled.connect(self._toggle_fixed_canvas)
        self.btn_custom.clicked.connect(self._load_custom_widgets)
        self.btn_theme.clicked.connect(self._open_theme_editor)
        self.btn_template.clicked.connect(self._show_template_menu)
        self.btn_preview.toggled.connect(self._toggle_preview)
        self.btn_canvas_size.clicked.connect(self._show_canvas_size_menu)
        self.btn_dark.toggled.connect(self._toggle_dark_mode)
        # 控件树同步
        self.canvas.widget_modified.connect(self.widget_tree.rebuild)
        self.canvas.widget_modified.connect(self._sync_page_tabs)
        self.widget_tree.item_selected.connect(lambda w: self.props.set_widget(w))
        # 初始构建
        self.widget_tree.rebuild()
        self._sync_page_tabs()
        self._refresh_code()

    def _toggle_grid_action(self, checked):
        self.canvas._grid_enabled = checked
        self.grid_action.setText("📐 网格:ON" if checked else "📐 网格:OFF")
        self.canvas.update()

    def _show_canvas_size_menu(self):
        menu = QMenu(self)
        presets = [
            ("📱 800×600    (SVGA)", 800, 600),
            ("💻 1024×768  (XGA)", 1024, 768),
            ("🖥️ 1280×720  (HD)", 1280, 720),
            ("📺 1366×768  (笔记本)", 1366, 768),
            ("🖵 1440×900  (WXGA+)", 1440, 900),
            ("🖳 1600×900  (HD+)", 1600, 900),
            ("📐 1920×1080 (Full HD)", 1920, 1080),
            ("🖼️ 2560×1440 (2K)", 2560, 1440),
            ("📊 3840×2160 (4K)", 3840, 2160),
        ]
        for label, w, h in presets:
            act = menu.addAction(label)
            act.triggered.connect(lambda checked, ww=w, hh=h, ll=label: self._set_canvas_size(ww, hh, ll))
        menu.addSeparator()
        act_custom = menu.addAction("✏️ 自定义尺寸...")
        act_custom.triggered.connect(self._custom_canvas_size_dialog)
        btn_rect = self.btn_canvas_size.rect()
        global_pos = self.btn_canvas_size.mapToGlobal(QPoint(0, btn_rect.height()))
        menu.exec(global_pos)

    def _set_canvas_size(self, w, h, label=""):
        self.canvas.set_canvas_size(w, h)
        self.btn_canvas_size.setText(f"📐 {w}×{h}")
        self.statusBar().showMessage(f"✅ 画布尺寸: {w}×{h}")

    def _custom_canvas_size_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("自定义画布尺寸")
        dlg.resize(300, 150)
        ly = QVBoxLayout(dlg)
        form = QHBoxLayout()
        form.addWidget(QLabel("宽度:"))
        w_spin = QSpinBox(); w_spin.setRange(200, 10000); w_spin.setValue(self.canvas.design_width)
        form.addWidget(w_spin)
        form.addWidget(QLabel("高度:"))
        h_spin = QSpinBox(); h_spin.setRange(200, 10000); h_spin.setValue(self.canvas.design_height)
        form.addWidget(h_spin)
        ly.addLayout(form)
        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("确定"); btn_cancel = QPushButton("取消")
        btn_layout.addStretch(); btn_layout.addWidget(btn_ok); btn_layout.addWidget(btn_cancel)
        ly.addLayout(btn_layout)
        btn_ok.clicked.connect(dlg.accept); btn_cancel.clicked.connect(dlg.reject)
        if dlg.exec() == QDialog.Accepted:
            self._set_canvas_size(w_spin.value(), h_spin.value())
    def _toggle_dark_mode(self, checked):
        global ACTIVE_QSS, DARK_MODE
        DARK_MODE = checked
        ACTIVE_QSS = DARK_QSS if checked else DEFAULT_QSS
        QApplication.instance().setStyleSheet(ACTIVE_QSS)
        self.btn_dark.setText("☀️ 亮色" if checked else "🌙 暗色")
        QSettings("MiniDesigner", "v19").setValue("dark_mode", checked)  # ← 确保写入

    def _toggle_preview(self, checked):
        if checked:
            self.canvas.enter_preview_mode()
            self.btn_preview.setText("✕ 退出预览")
        else:
            self.canvas.exit_preview_mode()
            self.btn_preview.setText("🔍 预览")

    def _on_page_tab_changed(self, idx):
        """页标签切换"""
        if idx >= 0 and idx < self.canvas.page_count():
            self.canvas.switch_page(idx)
            self._refresh_code()

    def _on_page_close(self, idx):
        """关闭页标签"""
        if self.canvas.page_count() <= 1:
            self.statusBar().showMessage("⚠️ 至少保留一个页面")
            return
        self.canvas.remove_page(idx)
        self._sync_page_tabs()
        self._refresh_code()

    def _on_page_rename(self, idx):
        """双击标签改名"""
        if idx < 0 or idx >= self.canvas.page_count(): return
        old_name = self.canvas.page_name(idx)
        new_name, ok = QInputDialog.getText(self, "重命名页面", "页面名称:", text=old_name)
        if ok and new_name.strip():
            self.canvas.rename_page(idx, new_name.strip())
            self._sync_page_tabs()
            self._refresh_code()

    def _on_add_page(self):
        """新建页面"""
        idx = self.canvas.add_page()
        self._sync_page_tabs()
        self.page_tabs.setCurrentIndex(idx)
        self._refresh_code()
        self.statusBar().showMessage(f"✅ 新建页面: {self.canvas.page_name(idx)}")

    def _sync_page_tabs(self):
        """同步页标签栏与画布页面状态"""
        self.page_tabs.blockSignals(True)
        # 移除所有标签
        while self.page_tabs.count() > 0:
            self.page_tabs.removeTab(0)
        # 重建
        for i in range(self.canvas.page_count()):
            self.page_tabs.addTab(self.canvas.page_name(i))
        self.page_tabs.setCurrentIndex(self.canvas.current_page())
        self.page_tabs.blockSignals(False)

    def _new_project(self):
        if self.canvas._canvas_widgets:
            r = QMessageBox.question(self, "新建项目", "当前画布有未保存的内容，是否清空？",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if r != QMessageBox.Yes: return
        self.canvas.clear_canvas()
        self.canvas.history.undo_stack.clear(); self.canvas.history.redo_stack.clear()
        self._current_file = None
        self._sync_page_tabs()
        self.setWindowTitle("Mini Designer v19 — 新建项目")
        self._refresh_code()
        self.statusBar().showMessage("✅ 已新建空白项目")

    def _show_template_menu(self):
        menu = QMenu(self)
        for name, tmpl in INDUSTRIAL_TEMPLATES.items():
            action = menu.addAction(name); action.setToolTip(tmpl["description"])
            action.triggered.connect(lambda checked, n=name: self.canvas.insert_template(n))
        # 每次打开菜单重新加载用户模板
        user_tmpl = _load_user_templates()
        if user_tmpl:
            menu.addSeparator()
            for name, tmpl in user_tmpl.items():
                a = menu.addAction(f"⭐ {name}"); a.setToolTip(tmpl["description"])
                a.triggered.connect(lambda checked, n=name, c=self.canvas: c.insert_template(n))
        if user_tmpl:
            menu.addSeparator()
            act_manage = menu.addAction("📂 管理用户模板"); act_manage.triggered.connect(self._manage_user_templates)
        else:
            menu.addSeparator()
            act_manage = menu.addAction("📂 管理用户模板（无模板）"); act_manage.setEnabled(False)
        menu.addSeparator()
        act_import = menu.addAction("📥 从项目文件导入模板"); act_import.triggered.connect(self._import_template_from_project)
        btn_rect = self.btn_template.rect(); global_pos = self.btn_template.mapToGlobal(QPoint(0, btn_rect.height()))
        menu.exec(global_pos)

    def _import_template_from_project(self):
        """从 .json 项目文件导入模板"""
        path, _ = QFileDialog.getOpenFileName(self, "选择项目文件", "", "JSON Files (*.json)")
        if not path: return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # 提取所有控件
            tmpl_widgets = []
            if isinstance(data, list):
                tmpl_widgets = data
            else:
                for p in data.get("pages", []):
                    tmpl_widgets.extend(p.get("widgets", []))
            if not tmpl_widgets:
                QMessageBox.warning(self, "导入失败", "项目文件中没有控件")
                return
            # 计算相对坐标
            min_x = min(w.get("x", 0) for w in tmpl_widgets)
            min_y = min(w.get("y", 0) for w in tmpl_widgets)
            for w in tmpl_widgets:
                w["x"] = w.get("x", 0) - min_x
                w["y"] = w.get("y", 0) - min_y
            name = os.path.splitext(os.path.basename(path))[0]
            from PySide6.QtWidgets import QInputDialog
            new_name, ok = QInputDialog.getText(self, "模板名称", "模板名称:", text=name)
            if not ok or not new_name.strip(): return
            USER_TEMPLATES[new_name] = {"description": f"从项目导入: {new_name}", "widgets": tmpl_widgets}
            _save_user_templates()
            self.statusBar().showMessage(f"✅ 已从项目导入模板: {new_name}（{len(tmpl_widgets)}个控件）")
        except Exception as e:
            QMessageBox.warning(self, "导入失败", str(e))

    def _manage_user_templates(self):
        """管理用户模板 — 查看/删除"""
        user_tmpl = _load_user_templates()
        dlg = QDialog(self); dlg.setWindowTitle("📂 管理用户模板"); dlg.resize(350, 300)
        layout = QVBoxLayout(dlg)
        list_widget = QListWidget()
        for name in user_tmpl:
            item = QListWidgetItem(f"⭐ {name}")
            item.setData(Qt.UserRole, name)
            list_widget.addItem(item)
        layout.addWidget(list_widget)
        btn_row = QHBoxLayout()
        btn_delete = QPushButton("🗑️ 删除选中"); btn_delete.setStyleSheet("QPushButton{background:#E74C3C;color:#fff;}")
        btn_close = QPushButton("✅ 关闭")
        btn_row.addStretch(); btn_row.addWidget(btn_delete); btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)
        def do_delete():
            item = list_widget.currentItem()
            if not item: return
            name = item.data(Qt.UserRole)
            if name in user_tmpl:
                del user_tmpl[name]
                global USER_TEMPLATES; USER_TEMPLATES.clear(); USER_TEMPLATES.update(user_tmpl)
                _save_user_templates()
                list_widget.takeItem(list_widget.row(item))
        btn_delete.clicked.connect(do_delete)
        btn_close.clicked.connect(dlg.accept)
        dlg.exec()

    def _load_custom_widgets(self):
        """打开自定义控件文件管理器 — 添加/移除文件，每个文件独立显示"""
        dlg = QDialog(self)
        dlg.setWindowTitle("🧩 自定义控件文件管理")
        dlg.resize(520, 320)
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        # 操作按钮行
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        btn_add = QPushButton("📂 添加文件")
        btn_add.setToolTip("选择要加载的自定义控件 Python 文件 (.py)")
        btn_add.setStyleSheet("QPushButton{background:#4A90D9;color:#fff;border:none;border-radius:4px;padding:5px 12px;font-size:12px;font-weight:bold;}QPushButton:hover{background:#357ABD;}")
        btn_remove = QPushButton("🗑 移除文件")
        btn_remove.setEnabled(False)
        btn_remove.setToolTip("从列表中移除选中的文件")
        btn_remove.setStyleSheet("QPushButton{background:#E74C3C;color:#fff;border:none;border-radius:4px;padding:5px 12px;font-size:12px;font-weight:bold;}QPushButton:hover{background:#C0392B;}QPushButton:disabled{background:#ccc;color:#999;}")
        btn_refresh = QPushButton("🔄 刷新")
        btn_refresh.setToolTip("重新加载所有文件")
        btn_refresh.setStyleSheet("QPushButton{background:#f0f0f0;border:1px solid #ccc;border-radius:4px;padding:5px 12px;font-size:12px;}QPushButton:hover{background:#e0e0e0;}")
        btn_close = QPushButton("✅ 完成")
        btn_close.setStyleSheet("QPushButton{background:#27AE60;color:#fff;border:none;border-radius:4px;padding:5px 16px;font-size:12px;font-weight:bold;}QPushButton:hover{background:#219A52;}")
        btn_svg = QPushButton("🎨 导入 SVG")
        btn_svg.setToolTip("导入 SVG 矢量图作为控件")
        btn_svg.setStyleSheet("QPushButton{background:#8E44AD;color:#fff;border:none;border-radius:4px;padding:5px 12px;font-size:12px;font-weight:bold;}QPushButton:hover{background:#7D3C98;}")
        btn_row.addWidget(btn_add)
        btn_row.addWidget(btn_remove)
        btn_row.addWidget(btn_refresh)
        btn_row.addWidget(btn_svg)
        btn_row.addStretch()
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

        # 提示文字
        info_label = QLabel("每个文件独立显示，选中后点击「🗑 移除文件」即可退出")
        info_label.setStyleSheet("color:#888; font-size:11px; padding:2px 2px;")
        layout.addWidget(info_label)

        # 文件列表
        file_list = QListWidget()
        file_list.setAlternatingRowColors(True)
        file_list.setStyleSheet(
            "QListWidget{font-size:12px;border:1px solid #ddd;border-radius:4px;}"
            "QListWidget::item{padding:6px 8px;}"
            "QListWidget::item:selected{background:#4A90D9;color:#fff;}"
            "QListWidget::item:alternate{background:#f9f9f9;}"
        )
        for fp in self._custom_widget_files:
            item = QListWidgetItem(os.path.basename(fp))
            item.setData(Qt.UserRole, fp)
            item.setToolTip(fp)
            file_list.addItem(item)
        layout.addWidget(file_list, 1)

        # 控件预览信息
        widget_info_label = QLabel()
        widget_info_label.setWordWrap(True)
        widget_info_label.setStyleSheet("color:#666; font-size:11px; padding:4px 6px; background:#f5f5f5; border:1px solid #e0e0e0; border-radius:4px;")
        widget_info_label.setMaximumHeight(80)
        layout.addWidget(widget_info_label)

        def _update_widget_info():
            if not CUSTOM_WIDGETS:
                widget_info_label.setText("💡 当前无自定义控件，点击「📂 添加文件」加载 .py 文件")
                return
            lines = []
            for name, cls, kwargs, fp in CUSTOM_WIDGETS:
                lines.append(f"  • {name}  ({cls.__name__})  ← {os.path.basename(fp)}")
            widget_info_label.setText("📦 已注册控件:\n" + "\n".join(lines))

        _update_widget_info()

        def _on_selection_changed():
            btn_remove.setEnabled(bool(file_list.currentItem()))
        file_list.currentItemChanged.connect(lambda: _on_selection_changed())

        def _refresh_file_list():
            file_list.clear()
            for fp in self._custom_widget_files:
                item = QListWidgetItem(os.path.basename(fp))
                item.setData(Qt.UserRole, fp)
                item.setToolTip(fp)
                file_list.addItem(item)
            _update_widget_info()

        def _reload_custom_widgets():
            count = CustomWidgetLoader.register_widgets(self._custom_widget_files)
            self.toolbox.populate()
            settings = QSettings("MiniDesigner", "v19")
            settings.setValue("custom_widget_paths", self._custom_widget_files)
            self.statusBar().showMessage(f"✅ 已加载 {count} 个自定义控件（{len(self._custom_widget_files)} 个文件）")
            _refresh_file_list()

        def _add_files():
            paths, _ = QFileDialog.getOpenFileNames(dlg, "选择自定义控件Python文件", "", "Python Files (*.py)")
            if not paths:
                return
            all_paths = list(dict.fromkeys(self._custom_widget_files + paths))
            if all_paths != self._custom_widget_files:
                self._custom_widget_files = all_paths
                _reload_custom_widgets()

        def _import_svg():
            path, _ = QFileDialog.getOpenFileName(dlg, "选择 SVG 文件", "", "SVG Files (*.svg)")
            if not path: return
            try:
                from svg_import import import_svg_file
                name, cls = import_svg_file(path)
                # 刷新文件列表显示 SVG
                _refresh_file_list()
                self.toolbox.populate()
                self.statusBar().showMessage(f"✅ 已导入 SVG: {name}")
            except Exception as e:
                QMessageBox.warning(dlg, "导入失败", str(e))

        def _refresh_file_list():
            """刷新文件列表（含自定义控件 .py + SVG 图元）"""
            file_list.clear()
            # Python 控件文件
            for fp in self._custom_widget_files:
                item = QListWidgetItem(os.path.basename(fp))
                item.setData(Qt.UserRole, fp)
                item.setToolTip(fp)
                file_list.addItem(item)
            # SVG 图元
            try:
                from svg_import import SVG_LIBRARY
                for name in SVG_LIBRARY:
                    item = QListWidgetItem(f"🎨 {name}.svg")
                    item.setData(Qt.UserRole, f"svg:{name}")
                    item.setToolTip(f"SVG 图元: {name}")
                    file_list.addItem(item)
            except Exception:
                pass
            _update_widget_info()

        def _remove_selected():
            current = file_list.currentItem()
            if not current:
                return
            data = current.data(Qt.UserRole)
            if not data:
                return
            # 判断是 Python 文件还是 SVG
            if isinstance(data, str) and data.startswith("svg:"):
                svg_name = data[4:]
                reply = QMessageBox.question(dlg, "确认移除", f"确定要移除 SVG 图元「{svg_name}」？",
                                             QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if reply != QMessageBox.Yes:
                    return
                from svg_import import SVG_LIBRARY, save_svg_library
                if svg_name in SVG_LIBRARY:
                    del SVG_LIBRARY[svg_name]
                    save_svg_library()
                self.toolbox.populate()
                _refresh_file_list()
                self.statusBar().showMessage(f"✅ 已移除 SVG: {svg_name}")
            else:
                fp = data
                base_name = os.path.basename(fp)
                reply = QMessageBox.question(dlg, "确认移除", f"确定要移除文件「{base_name}」及其所有自定义控件？\n\n{fp}",
                                             QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if reply != QMessageBox.Yes:
                    return
                self._custom_widget_files.remove(fp)
                _reload_custom_widgets()
                _refresh_file_list()
                self.statusBar().showMessage(f"✅ 已移除文件: {base_name}")

        def _on_selection_changed():
            btn_remove.setEnabled(bool(file_list.currentItem()))
        file_list.currentItemChanged.connect(lambda: _on_selection_changed())

        # 连接按钮
        btn_add.clicked.connect(_add_files)
        btn_remove.clicked.connect(_remove_selected)
        btn_refresh.clicked.connect(lambda: (_reload_custom_widgets(), _refresh_file_list()))
        btn_svg.clicked.connect(_import_svg)
        btn_close.clicked.connect(dlg.accept)

        # 初始刷新
        _refresh_file_list()
        dlg.exec()

    def _open_theme_editor(self):
        global ACTIVE_QSS
        dlg = ThemeEditorDialog(ACTIVE_QSS, self); dlg.qss_changed.connect(self._live_preview_qss)
        result = dlg.exec()
        if result == QDialog.Accepted: ACTIVE_QSS = dlg.get_qss(); QApplication.instance().setStyleSheet(ACTIVE_QSS); self.statusBar().showMessage("✅ 主题已应用")
        else: QApplication.instance().setStyleSheet(ACTIVE_QSS); self.statusBar().showMessage("❌ 主题编辑已取消，已恢复")

    def _live_preview_qss(self, qss_text):
        try: QApplication.instance().setStyleSheet(qss_text)
        except Exception: pass

    def _toggle_ui_class_mode(self, checked):
        self._ui_class_mode = checked
        if checked:
            self.btn_ui_class.setText("📦 Ui类模式")
            self.btn_ui_class.setStyleSheet(
                "QToolButton{background:#4A90D9;color:#fff;border:none;"
                "padding:5px 10px;font-size:12px;font-weight:bold;"
                "border-radius:4px;} "
                "QToolButton:hover{background:#357ABD;}"
            )
            self.statusBar().showMessage("✅ 当前模式: Ui类模式 — 生成 class Ui_MainWindow(object)")
        else:
            self.btn_ui_class.setText("🪟 独立窗口")
            self.btn_ui_class.setStyleSheet(
                "QToolButton{padding:5px 10px;font-size:12px;}"
            )
            self.statusBar().showMessage("✅ 当前模式: 独立窗口 — 生成 class GeneratedWindow(QMainWindow)")
        self._refresh_code()

    def _update_undo_redo_state(self):
        self.btn_undo.setEnabled(self.canvas.history.can_undo())
        self.btn_redo.setEnabled(self.canvas.history.can_redo())

    def _refresh_code(self): self.code_view.setPlainText(CodeGenerator.generate(self.canvas, as_ui_class=self._ui_class_mode))

    def _toggle_fixed_canvas(self, checked):
        self.canvas._fixed_canvas = checked
        if checked:
            self.btn_fixed.setText("🔒 固定画布")
            self.btn_fixed.setStyleSheet(
                "QToolButton{background:#E67E22;color:#fff;border:none;"
                "padding:5px 10px;font-size:12px;font-weight:bold;"
                "border-radius:4px;} "
                "QToolButton:hover{background:#D68910;}"
            )
            self.statusBar().showMessage("✅ 画布已固定 — 生成 setFixedSize()")
        else:
            self.btn_fixed.setText("🔓 可缩放")
            self.btn_fixed.setStyleSheet(
                "QToolButton{padding:5px 10px;font-size:12px;}"
            )
            self.statusBar().showMessage("✅ 画布可缩放 — 生成 resize()")

    def _copy_code(self):
        QApplication.clipboard().setText(self.code_view.toPlainText()); self.btn_copy.setText("已复制!"); self.btn_copy.setEnabled(False)
        QTimer.singleShot(1500, lambda: (self.btn_copy.setText("复制代码"), self.btn_copy.setEnabled(True)))

    def _clear(self):
        if QMessageBox.question(self,"清空画布","确定移除所有控件吗？",QMessageBox.Yes|QMessageBox.No,QMessageBox.No)==QMessageBox.Yes:
            self.canvas.clear_canvas(); self.canvas.history.undo_stack.clear(); self.canvas.history.redo_stack.clear(); self._refresh_code()

    def _export_qss(self):
        global ACTIVE_QSS
        path, _ = QFileDialog.getSaveFileName(self, "导出全局样式表", "style.qss", "QSS Files (*.qss)")
        if path:
            with open(path, "w", encoding="utf-8") as f: f.write(ACTIVE_QSS)
            QMessageBox.information(self, "导出成功", f"样式表已保存至:\n{path}")

    def _export_project(self):
        """导出完整项目骨架"""
        import shutil, traceback

        # 先输入项目名
        project_name, ok = QInputDialog.getText(
            self, "导出项目", "请输入项目名称（用作文件名）:",
            text=os.path.splitext(os.path.basename(self._current_file or ""))[0] or "my_project"
        )
        if not ok or not project_name.strip():
            return
        project_name = _sanitize(project_name) or "my_project"

        # 选择导出模式
        mode_choices = ["独立窗口", "Ui类模式"]
        export_mode, ok = QInputDialog.getItem(
            self, "导出模式", "选择生成代码的格式:", mode_choices, 0, False
        )
        if not ok:
            return
        use_ui_class = (export_mode == "Ui类模式")

        # 选择目录
        target_dir = QFileDialog.getExistingDirectory(
            self, "选择导出目标目录", "",
            QFileDialog.ShowDirsOnly)
        if not target_dir: return

        try:
            # 确保页面数据同步
            self.canvas._save_current_page()
            code = CodeGenerator.generate(self.canvas, as_ui_class=use_ui_class, qss_filename=f"{project_name}.qss")
            if not code:
                raise RuntimeError("代码生成为空")

            # {name}.py — 用项目名
            py_path = os.path.join(target_dir, f"{project_name}.py")
            with open(py_path, "w", encoding="utf-8") as f:
                f.write(code + "\n")

            # requirements.txt
            reqs = ["PySide6>=6.5.0"]
            copied = []
            for _, _, _, filepath in CUSTOM_WIDGETS:
                if not filepath or not os.path.isfile(filepath): continue
                basename = os.path.basename(filepath)
                dest = os.path.join(target_dir, basename)
                if not os.path.exists(dest):
                    shutil.copy2(filepath, dest)
                    copied.append(basename)
                reqs.append(os.path.splitext(basename)[0])
            
            # 复制 SVG 导入模块
            for svg_fn in ['svg_import.py', 'svg_library.json']:
                svg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), svg_fn)
                if os.path.isfile(svg_path):
                    dest = os.path.join(target_dir, svg_fn)
                    if not os.path.exists(dest):
                        shutil.copy2(svg_path, dest)
                        copied.append(svg_fn)

            with open(os.path.join(target_dir, "requirements.txt"), "w", encoding="utf-8") as f:
                f.write("\n".join(reqs) + "\n")

            # {name}.json — 设计器可重新打开
            json_path = os.path.join(target_dir, f"{project_name}.json")
            self.canvas.save_project(json_path)

            # {name}.qss — 样式表
            qss = ACTIVE_QSS if not DARK_MODE else DEFAULT_QSS
            qss_path = os.path.join(target_dir, f"{project_name}.qss")
            with open(qss_path, "w", encoding="utf-8") as f:
                f.write(qss)

            # 数据绑定模板
            tags_found = any(
                w.property("_tag") for p in self.canvas._pages
                for w in p.get("widgets", []) if not w.property("_designer_hidden")
            )
            if tags_found:
                with open(os.path.join(target_dir, "opc_comm.py"), "w", encoding="utf-8") as f:
                    f.write("import time, threading, random, math\n\nclass DataSource(threading.Thread):\n    def __init__(self, data_binder):\n        super().__init__(daemon=True)\n        self.binder = data_binder\n        self.running = True\n    def run(self):\n        t = 0\n        while self.running:\n            temp = 75 + 15 * math.sin(t * 0.5)\n            self.binder.update_tag('temp_value', temp)\n            time.sleep(0.5); t += 0.5\n")

            self.statusBar().showMessage(f"✅ 已导出 {project_name} 到: {target_dir}")
            QTimer.singleShot(200, lambda: QMessageBox.information(
                self, "导出成功",
                f"项目: {project_name}\n"
                f"目录: {target_dir}\n"
                f"{project_name}.py + {project_name}.json + {project_name}.qss + requirements.txt"
                + (f"\n自定义控件: {', '.join(copied)}" if copied else "")
                + ("\nopc_comm.py" if tags_found else "")))
        except Exception as e:
            traceback.print_exc()
            QTimer.singleShot(200, lambda: QMessageBox.critical(
                self, "导出失败", str(e)[:200]))

    def _save_project(self):
        """带异常保护的保存操作，防止因画布状态异常导致软件崩溃"""
        import traceback as _tb
        try:
            default = self._current_file or "untitled.json"
            path, _ = QFileDialog.getSaveFileName(self, "保存项目", default, "JSON Files (*.json)")
            if not path:
                return
            # 保存前先取消选中，避免保存过程中事件交互干扰
            self.canvas._deselect()
            # 确保当前页面同步
            self.canvas._save_current_page()
            # 强制处理所有待处理事件（如属性编辑器更新等）
            QApplication.processEvents()
            self.canvas.save_project(path)
            self._current_file = path
            self.setWindowTitle(f"MiniSCADA Designer v20 — {os.path.basename(path)}")
            self.statusBar().showMessage(f"✅ 已保存: {path}")
        except Exception as e:
            _tb.print_exc()
            self.statusBar().showMessage(f"❌ 保存失败: {str(e)[:80]}")


    def _load_project(self):
        path, _ = QFileDialog.getOpenFileName(self, "打开项目", "", "JSON Files (*.json)")
        if not path: 
            return
            
        try:
            self.canvas.load_project(path)
            self._current_file = path
            self.setWindowTitle(f"MiniSCADA Designer v20 — {os.path.basename(path)}")
            self._sync_page_tabs()
            self._refresh_code()
            self.statusBar().showMessage(f"✅ 已加载: {path}")
            
            # 【核心修复】延迟刷新画布尺寸，等待 ScrollArea 布局完成
            QTimer.singleShot(50, lambda: self.canvas.set_canvas_size(
                self.canvas.design_width, 
                self.canvas.design_height
            ))
        except Exception as e:
            QMessageBox.critical(self, "加载失败", f"无法打开项目文件:\n{str(e)}")




# ═══════════════════════════════════════════════════════════════
# 📂 项目面板
# ═══════════════════════════════════════════════════════════════# ═══════════════════════════════════════════════════════════════
# 入口
# ═══════════════════════════════════════════════════════════════
def main():
    app = QApplication(sys.argv); win = DesignerMainWindow(); win.show(); sys.exit(app.exec())

if __name__ == "__main__":
    main()