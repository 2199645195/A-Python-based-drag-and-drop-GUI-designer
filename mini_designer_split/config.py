#!/usr/bin/env python3
"""
mini_designer_split/config.py — 全局配置、QSS、控件映射、工具函数
"""
import re, math, random
from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import (
    QSizePolicy, QPushButton, QToolButton, QCommandLinkButton, QDialogButtonBox,
    QCheckBox, QRadioButton, QLabel, QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox,
    QDateEdit, QTimeEdit, QCalendarWidget, QListWidget, QTreeWidget, QTableWidget,
    QSlider, QProgressBar, QDial, QLCDNumber, QGroupBox, QTabWidget, QStackedWidget,
    QScrollArea, QSplitter, QFrame, QTextEdit, QTextBrowser,
)

# ── 工具函数 ──────────────────────────────────────────────────────
def _esc(s):
    return s.replace("\\", "\\\\").replace('"', '\\"')

def _sanitize(name):
    return re.sub(r"_+", "_", re.sub(r"[^a-zA-Z0-9_]", "_", name)).strip("_").lower() or "widget"

def _policy_to_str(policy):
    for name, val in SIZE_POLICY_MAP.items():
        if policy == val:
            return name
    return "Preferred"

# ── QSS 主题 ─────────────────────────────────────────────────────
DEFAULT_QSS = """
QMainWindow { background: #fafafa; }
QWidget { font-family: "Microsoft YaHei", "Segoe UI", sans-serif; font-size: 13px; color: #333; }
QPushButton, QToolButton, QCommandLinkButton { background: #fff; border: 1px solid #d0d0d0; padding: 6px 16px; border-radius: 6px; }
QPushButton:hover, QToolButton:hover, QCommandLinkButton:hover { background: #e8f0fe; border-color: #4A90D9; }
QPushButton:pressed, QToolButton:pressed { background: #d0e4f7; }
QListWidget, QTableWidget, QTextEdit, QTextBrowser, QTreeWidget { background: #fff; border: 1px solid #e0e0e0; border-radius: 4px; outline: none; }
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

DARK_QSS = """
QMainWindow { background: #1e1e2e; }
QWidget { font-family: "Microsoft YaHei", "Segoe UI", sans-serif; font-size: 13px; color: #cdd6f4; }
QPushButton, QToolButton, QCommandLinkButton { background: #313244; border: 1px solid #45475a; padding: 6px 16px; border-radius: 6px; color: #cdd6f4; }
QPushButton:hover, QToolButton:hover, QCommandLinkButton:hover { background: #45475a; border-color: #89b4fa; }
QPushButton:pressed, QToolButton:pressed { background: #585b70; }
QListWidget, QTableWidget, QTextEdit, QTextBrowser, QTreeWidget { background: #313244; border: 1px solid #45475a; border-radius: 4px; outline: none; color: #cdd6f4; }
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

ACTIVE_QSS = DEFAULT_QSS
DARK_MODE = False

# ── 控件角色映射 ─────────────────────────────────────────────────
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

BINDABLE_WIDGETS = (QLabel, QLineEdit, QLCDNumber, QProgressBar, QSlider, QSpinBox,
                    QDoubleSpinBox, QCheckBox, QRadioButton, QGroupBox)

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

# ── 画布常量 ─────────────────────────────────────────────────────
MIME_TYPE = "application/x-designer-widget-v19"
HANDLE_SIZE = 8
HANDLE_HALF = 4
MIN_W = 30
MIN_H = 24
HANDLE_CURSORS = {
    "tl": Qt.SizeFDiagCursor, "tc": Qt.SizeVerCursor, "tr": Qt.SizeBDiagCursor,
    "ml": Qt.SizeHorCursor, "mr": Qt.SizeHorCursor,
    "bl": Qt.SizeBDiagCursor, "bc": Qt.SizeVerCursor, "br": Qt.SizeFDiagCursor,
}
VIEWPORT_WIDGETS = (QTableWidget, QTreeWidget, QListWidget, QTextEdit, QTextBrowser)
SNAP_THRESHOLD = 5
ARROW_STEP = 1
DESIGN_WIDTH = 800
DESIGN_HEIGHT = 600
GRID_SIZE = 10

# ── SizePolicy ───────────────────────────────────────────────────
SIZE_POLICY_MAP = {
    "Preferred": QSizePolicy.Preferred, "Fixed": QSizePolicy.Fixed,
    "Minimum": QSizePolicy.Minimum, "Maximum": QSizePolicy.Maximum,
    "Expanding": QSizePolicy.Expanding, "MinimumExpanding": QSizePolicy.MinimumExpanding,
    "Ignored": QSizePolicy.Ignored,
}
SIZE_POLICY_NAMES = list(SIZE_POLICY_MAP.keys())

# ── 内置控件分类 ─────────────────────────────────────────────────
BUILTIN_CATEGORIES = [
    ("按钮类", [("按钮",QPushButton,{"text":"按钮"}),("工具按钮",QToolButton,{"text":"工具"}),("命令链接按钮",QCommandLinkButton,{"text":"命令链接"}),("对话框按钮组",QDialogButtonBox,{}),("复选框",QCheckBox,{"text":"复选框"}),("单选按钮",QRadioButton,{"text":"单选按钮"})]),
    ("文本与标签", [("标签",QLabel,{"text":"标签文本"}),("链接标签",QLabel,{"text":"<a href='#'>链接文本</a>","openExternalLinks":True}),("单行输入框",QLineEdit,{"placeholderText":"请输入..."}),("多行文本框",QTextEdit,{"placeholderText":"多行文本..."}),("只读文本浏览器",QTextBrowser,{})]),
    ("选择器", [("下拉框",QComboBox,{"items":["选项1","选项2","选项3"]}),("整数微调框",QSpinBox,{"range":(0,999),"value":0}),("浮点微调框",QDoubleSpinBox,{"range":(0.0,99.9),"decimals":2}),("日期选择器",QDateEdit,{}),("时间选择器",QTimeEdit,{}),("日历控件",QCalendarWidget,{}),("列表控件",QListWidget,{}),("树形控件",QTreeWidget,{}),("表格控件",QTableWidget,{})]),
    ("数值与进度", [("滑块",QSlider,{"orientation":Qt.Horizontal}),("进度条",QProgressBar,{"value":45}),("旋钮",QDial,{}),("液晶数字显示",QLCDNumber,{})]),
    ("容器与布局", [("分组框",QGroupBox,{"title":"分组标题"}),("标签页容器",QTabWidget,{}),("堆叠容器",QStackedWidget,{}),("滚动区域",QScrollArea,{}),("分割面板",QSplitter,{"orientation":Qt.Horizontal}),("垂直布局容器",None,{"layout":"vbox"}),("水平布局容器",None,{"layout":"hbox"})]),
    ("框架与分隔", [("框架",QFrame,{"frameShape":QFrame.StyledPanel}),("水平分隔线",QFrame,{"frameShape":QFrame.HLine}),("垂直分隔线",QFrame,{"frameShape":QFrame.VLine})]),
]

CUSTOM_WIDGETS = []  # [(display_name, cls, kwargs, filepath), ...]

def get_all_categories():
    cats = list(BUILTIN_CATEGORIES)
    if CUSTOM_WIDGETS:
        custom_items = [(name, cls, kwargs) for name, cls, kwargs, _ in CUSTOM_WIDGETS]
        cats.append(("⭐ 自定义控件", custom_items))
    return cats

def get_display_to_entry():
    mapping = {}
    for _, items in BUILTIN_CATEGORIES:
        for item in items:
            mapping[item[0]] = item
    for name, cls, kwargs, filepath in CUSTOM_WIDGETS:
        mapping[name] = (name, cls, kwargs, filepath)
    return mapping

# ── 命名前缀与默认尺寸 ───────────────────────────────────────────
NAME_TO_PREFIX = {
    "按钮":"btn","工具按钮":"tool_btn","命令链接按钮":"cmd_link","对话框按钮组":"btn_box",
    "复选框":"checkbox","单选按钮":"radio","标签":"label","链接标签":"link_label",
    "单行输入框":"line_edit","多行文本框":"text_edit","只读文本浏览器":"text_browser",
    "下拉框":"combo","整数微调框":"spin_box","浮点微调框":"double_spin",
    "日期选择器":"date_edit","时间选择器":"time_edit","日历控件":"calendar",
    "列表控件":"list_widget","树形控件":"tree_widget","表格控件":"table_widget",
    "滑块":"slider","进度条":"progress","旋钮":"dial","液晶数字显示":"lcd",
    "分组框":"group_box","标签页容器":"tab_widget","堆叠容器":"stacked",
    "滚动区域":"scroll_area","分割面板":"splitter",
    "垂直布局容器":"vbox_container","水平布局容器":"hbox_container",
    "框架":"frame","水平分隔线":"h_line","垂直分隔线":"v_line",
}

DEFAULT_SIZES = {
    "按钮":QSize(120,36),"工具按钮":QSize(80,30),"命令链接按钮":QSize(200,48),
    "对话框按钮组":QSize(260,40),"复选框":QSize(100,28),"单选按钮":QSize(100,28),
    "标签":QSize(80,24),"链接标签":QSize(100,24),"单行输入框":QSize(160,28),
    "多行文本框":QSize(200,80),"只读文本浏览器":QSize(200,80),
    "下拉框":QSize(160,28),"整数微调框":QSize(100,28),"浮点微调框":QSize(120,28),
    "日期选择器":QSize(140,28),"时间选择器":QSize(120,28),"日历控件":QSize(240,180),
    "列表控件":QSize(160,100),"树形控件":QSize(200,120),"表格控件":QSize(280,140),
    "滑块":QSize(160,28),"进度条":QSize(200,24),"旋钮":QSize(80,80),
    "液晶数字显示":QSize(120,40),"分组框":QSize(240,100),"标签页容器":QSize(300,180),
    "堆叠容器":QSize(280,160),"滚动区域":QSize(280,160),"分割面板":QSize(280,120),
    "垂直布局容器":QSize(120,80),"水平布局容器":QSize(160,80),
    "框架":QSize(200,100),"水平分隔线":QSize(100,4),"垂直分隔线":QSize(4,100),
}

# ── 工业模板 ─────────────────────────────────────────────────────
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
