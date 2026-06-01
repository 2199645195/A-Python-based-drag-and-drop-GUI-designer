"""mini_designer_split/app.py — 主窗口应用"""

import os, shutil

from PySide6.QtCore import Qt, QTimer, QSettings
from PySide6.QtGui import QKeySequence, QShortcut, QFontMetrics
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QLabel, QPushButton, QLineEdit, QTextEdit,
    QTabWidget, QTabBar, QScrollArea, QToolBar, QToolButton,
    QFileDialog, QMessageBox, QInputDialog, QDialog, QSpinBox,
    QListWidget, QListWidgetItem, QMenu, QStyleFactory, QSizePolicy,
    QStatusBar,
)

from .config import (
    DEFAULT_QSS, DARK_QSS, ACTIVE_QSS, DARK_MODE, INDUSTRIAL_TEMPLATES,
    DESIGN_WIDTH, DESIGN_HEIGHT,
)
from .canvas import DesignerCanvas
from .panels import WidgetToolbox, WidgetTreePanel, PropertyEditor
from .panels.simulator import DataSimulatorPanel
from .panels.undo_history import UndoHistoryPanel
from .dialogs import (
    CustomWidgetLoader, ThemeEditorDialog, SignalSlotDialog,
)
from .codegen import CodeGenerator


class DesignerMainWindow(QMainWindow):
    """Mini Designer 主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(
            "Mini Designer v19 — 控件树/预览/图表/仪表/数据模拟"
        )
        self._current_file = None
        self._ui_class_mode = False
        self._custom_widget_files = []
        self._setup_ui()

        QShortcut(QKeySequence("Ctrl+S"), self).activated.connect(
            self._save_project
        )
        QShortcut(QKeySequence("Ctrl+N"), self).activated.connect(
            self._new_project
        )
        QShortcut(QKeySequence("Ctrl+O"), self).activated.connect(
            self._load_project
        )

        QApplication.instance().setStyle(QStyleFactory.create("Fusion"))
        QApplication.instance().setStyleSheet(ACTIVE_QSS)
        self._wire()
        self._restore_state()
        self._auto_load_custom_widgets()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(0)

        # ── 对齐工具栏 ──
        self.align_toolbar = QToolBar("对齐工具")
        self.align_toolbar.setMovable(False)
        for label, at in [
            ("⬅️左", "left"), ("➡️右", "right"),
            ("⬆️顶", "top"), ("⬇️底", "bottom"),
            ("↔️水平居中", "hcenter"), ("↕️垂直居中", "vcenter"),
            ("═等宽", "same_width"), ("║等高", "same_height"),
            ("⋯水平等距", "distribute_h"), ("⋮垂直等距", "distribute_v"),
        ]:
            action = self.align_toolbar.addAction(label)
            action.triggered.connect(
                lambda checked, a=at: self.canvas.align_widgets(a)
            )
        self.align_toolbar.addSeparator()
        self.grid_action = self.align_toolbar.addAction("📐 网格:ON")
        self.grid_action.setCheckable(True)
        self.grid_action.setChecked(True)
        self.grid_action.triggered.connect(self._toggle_grid_action)
        self.addToolBar(Qt.TopToolBarArea, self.align_toolbar)

        # ── 主分割 ──
        top_split = QSplitter(Qt.Horizontal)
        self.toolbox = WidgetToolbox()
        self.canvas = DesignerCanvas()
        self.props = PropertyEditor()
        self.props.setMinimumWidth(220)
        self.props.setMaximumWidth(400)

        # 左侧面板
        left_tabs = QTabWidget()
        left_tabs.addTab(self.toolbox, "🧰 工具箱")
        self.widget_tree = WidgetTreePanel(self.canvas)
        left_tabs.addTab(self.widget_tree, "📁 控件树")

        # 右侧面板
        right_tabs = QTabWidget()
        right_tabs.addTab(self.props, "📋 属性")
        self.data_sim = DataSimulatorPanel(self.canvas)
        right_tabs.addTab(self.data_sim, "🔬 模拟器")
        self.history_panel = UndoHistoryPanel(self.canvas)
        right_tabs.addTab(self.history_panel, "📜 历史")

        # 画布区域 + 页面标签栏
        canvas_area = QWidget()
        canvas_area_layout = QVBoxLayout(canvas_area)
        canvas_area_layout.setContentsMargins(0, 0, 0, 0)
        canvas_area_layout.setSpacing(0)

        page_bar = QWidget()
        page_bar.setStyleSheet(
            "background:#e8e8e8;border-bottom:1px solid #ccc;"
        )
        page_bar_layout = QHBoxLayout(page_bar)
        page_bar_layout.setContentsMargins(4, 2, 4, 2)
        page_bar_layout.setSpacing(2)
        self.page_tabs = QTabBar()
        self.page_tabs.setTabsClosable(True)
        self.page_tabs.setMovable(True)
        self.page_tabs.setExpanding(False)
        self.page_tabs.setToolTip(
            "双击标签可重命名 | 拖拽可排序 | 点击 ⨉ 删除"
        )
        self.page_tabs.setStyleSheet("""
            QTabBar::tab{min-width:80px;padding:6px 28px 6px 14px;
              font-size:12px;font-weight:bold;background:#c8c8c8;
              border:1px solid #aaa;border-bottom:none;
              border-radius:6px 6px 0 0;margin-right:3px;color:#333;}
            QTabBar::tab:selected{background:#fff;color:#4A90D9;
              border-bottom:2px solid #4A90D9;}
            QTabBar::tab:hover{background:#d8d8d8;}
            QTabBar::close-button{image:...;width:14px;height:14px;}
            QTabBar::close-button:hover{image:...;}
        """)
        self.page_tabs.addTab("页面1")
        btn_add_page = QPushButton("＋ 新建页")
        btn_add_page.setMinimumWidth(80)
        btn_add_page.setStyleSheet(
            "QPushButton{background:#4A90D9;color:#fff;border:none;"
            "border-radius:4px;padding:3px 10px;font-size:12px;font-weight:bold;}"
            " QPushButton:hover{background:#357ABD;}"
        )
        page_bar_layout.addWidget(self.page_tabs)
        page_bar_layout.addWidget(btn_add_page)
        page_bar_layout.addStretch()
        canvas_area_layout.addWidget(page_bar)

        self.canvas_scroll = QScrollArea()
        self.canvas_scroll.setWidgetResizable(False)
        self.canvas_scroll.setWidget(self.canvas)
        self.canvas_scroll.setStyleSheet(
            "QScrollArea{background:#e0e0e0;border:none;}"
        )
        self.canvas.setMinimumSize(DESIGN_WIDTH, DESIGN_HEIGHT)
        canvas_area_layout.addWidget(self.canvas_scroll)

        self.page_tabs.currentChanged.connect(self._on_page_tab_changed)
        self.page_tabs.tabCloseRequested.connect(self._on_page_close)
        self.page_tabs.tabBarDoubleClicked.connect(self._on_page_rename)
        btn_add_page.clicked.connect(self._on_add_page)

        top_split.addWidget(left_tabs)
        top_split.addWidget(canvas_area)
        top_split.addWidget(right_tabs)
        top_split.setSizes([200, 700, 300])

        # ── 底部面板 ──
        bottom = QWidget()
        bl = QVBoxLayout(bottom)
        bl.setContentsMargins(0, 4, 0, 0)
        bl.setSpacing(4)

        BUTTON_STYLE = "QToolButton{padding:4px 8px;font-size:11px;}"

        self.toolbar_row1 = QToolBar("常用工具栏")
        self.toolbar_row1.setMovable(False)
        self.toolbar_row1.setStyleSheet(
            "QToolBar{spacing:2px;padding:1px 4px;border:none;}"
        )
        self.btn_template = self._add_tb_btn2(self.toolbar_row1, "🏭 模板", BUTTON_STYLE)
        self.btn_undo = self._add_tb_btn2(self.toolbar_row1, "↩ 撤销", BUTTON_STYLE)
        self.btn_undo.setEnabled(False)
        self.btn_redo = self._add_tb_btn2(self.toolbar_row1, "↪ 重做", BUTTON_STYLE)
        self.btn_redo.setEnabled(False)
        self.btn_canvas_size = self._add_tb_btn2(self.toolbar_row1, "📐 800×600", BUTTON_STYLE)
        self.toolbar_row1.addSeparator()
        self.btn_preview = self._add_tb_btn2(
            self.toolbar_row1, "🔍 预览",
            "QToolButton{background:#27AE60;color:#fff;border:none;"
            "padding:4px 8px;border-radius:4px;font-weight:bold;font-size:11px;}"
            " QToolButton:hover{background:#219A52;}"
            " QToolButton:checked{background:#E74C3C;}"
        )
        self.btn_preview.setCheckable(True)
        bl.addWidget(self.toolbar_row1)

        self.toolbar_row2 = QToolBar("工具/文件")
        self.toolbar_row2.setMovable(False)
        self.toolbar_row2.setStyleSheet(
            "QToolBar{spacing:2px;padding:1px 4px;border:none;}"
        )
        self.btn_dark = self._add_tb_btn2(self.toolbar_row2, "🌙 暗色", BUTTON_STYLE)
        self.btn_dark.setCheckable(True)
        self.btn_custom = self._add_tb_btn2(self.toolbar_row2, "🧩 自定义控件", BUTTON_STYLE)
        self.btn_theme = self._add_tb_btn2(self.toolbar_row2, "🎨 主题", BUTTON_STYLE)
        self.btn_ui_class = self._add_tb_btn2(self.toolbar_row2, "🪟 独立窗口", BUTTON_STYLE)
        self.btn_ui_class.setCheckable(True)
        self.btn_fixed = self._add_tb_btn2(self.toolbar_row2, "🔒 固定画布", BUTTON_STYLE)
        self.btn_fixed.setCheckable(True)
        self.toolbar_row2.addSeparator()
        self.btn_save = self._add_tb_btn2(self.toolbar_row2, "💾 保存", BUTTON_STYLE)
        self.btn_load = self._add_tb_btn2(self.toolbar_row2, "📂 打开", BUTTON_STYLE)
        self.btn_export_project = self._add_tb_btn2(self.toolbar_row2, "📦 导出", BUTTON_STYLE)
        self.btn_export_qss = self._add_tb_btn2(self.toolbar_row2, "导出 QSS", BUTTON_STYLE)
        self.toolbar_row2.addSeparator()
        self.btn_clear = self._add_tb_btn2(self.toolbar_row2, "🗑️ 清空", BUTTON_STYLE)
        bl.addWidget(self.toolbar_row2)

        code_header = QWidget()
        code_header_l = QHBoxLayout(code_header)
        code_header_l.setContentsMargins(4, 0, 4, 2)
        code_header_l.setSpacing(6)
        code_label = QLabel("<b>生成代码</b>")
        code_label.setStyleSheet("font-size: 12px; color: #555;")
        code_header_l.addWidget(code_label)
        code_header_l.addStretch()
        self.btn_copy = QPushButton("📋 复制代码")
        self.btn_copy.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        code_header_l.addWidget(self.btn_copy)
        bl.addWidget(code_header)

        self.code_view = QTextEdit()
        self.code_view.setReadOnly(True)
        self.code_view.setStyleSheet(
            "QTextEdit{background:#1e1e1e;color:#d4d4d4;"
            "font-family:'Consolas',monospace;font-size:12px;"
            "border:1px solid #333;border-radius:4px;}"
        )
        bl.addWidget(self.code_view)

        self.main_split = QSplitter(Qt.Vertical)
        self.main_split.addWidget(top_split)
        self.main_split.addWidget(bottom)
        self.main_split.setSizes([600, 300])
        root.addWidget(self.main_split)

        self.statusBar().showMessage(
            "就绪 | G键切换网格 | 右键→信号/槽 | Ctrl+Z/Y"
        )
        self.statusBar().setStyleSheet(
            "QStatusBar { font-size: 11px; color: #666;"
            " border-top: 1px solid #e0e0e0; }"
        )

    def _add_tb_btn(self, text, style=""):
        btn = QToolButton()
        btn.setText(text)
        btn.setToolButtonStyle(Qt.ToolButtonTextOnly)
        if style:
            btn.setStyleSheet(style)
        fm = btn.fontMetrics()
        btn.setMinimumWidth(fm.horizontalAdvance(text) + 20)
        self.bottom_toolbar.addWidget(btn)
        return btn

    def _add_tb_btn2(self, toolbar, text, style=""):
        btn = QToolButton()
        btn.setText(text)
        btn.setToolButtonStyle(Qt.ToolButtonTextOnly)
        if style:
            btn.setStyleSheet(style)
        fm = btn.fontMetrics()
        btn.setMinimumWidth(fm.horizontalAdvance(text) + 16)
        toolbar.addWidget(btn)
        return btn

    # ── 自动加载自定义控件 ──
    def _auto_load_custom_widgets(self):
        settings = QSettings("MiniDesigner", "v19")
        saved_paths = settings.value("custom_widget_paths", [])
        if saved_paths and isinstance(saved_paths, list):
            valid_paths = [p for p in saved_paths if os.path.isfile(p)]
            if valid_paths:
                count = CustomWidgetLoader.register_widgets(valid_paths)
                self._custom_widget_files = valid_paths
                self.toolbox.populate()
                self.statusBar().showMessage(
                    f"✅ 自动加载 {count} 个自定义控件"
                )

    def _restore_state(self):
        settings = QSettings("MiniDesigner", "v19")
        saved_geom = settings.value("window_geometry")
        if saved_geom:
            self.restoreGeometry(saved_geom)
        else:
            screen = QApplication.primaryScreen().availableGeometry()
            w = int(screen.width() * 0.85)
            h = int(screen.height() * 0.85)
            self.setGeometry(
                (screen.width() - w) // 2,
                (screen.height() - h) // 2, w, h,
            )
        ms = settings.value("main_split_sizes")
        if ms:
            self.main_split.restoreState(ms)
        ts = settings.value("top_split_sizes")
        if ts:
            t = self.main_split.widget(0)
            if isinstance(t, QSplitter):
                t.restoreState(ts)
        dark = settings.value("dark_mode", False)
        if isinstance(dark, str):
            dark = dark.lower() == "true"
        if dark:
            self.btn_dark.setChecked(True)
            self._toggle_dark_mode(True)

    def closeEvent(self, event):
        settings = QSettings("MiniDesigner", "v19")
        settings.setValue("window_geometry", self.saveGeometry())
        settings.setValue("dark_mode", DARK_MODE)
        settings.setValue("main_split_sizes", self.main_split.saveState())
        t = self.main_split.widget(0)
        if isinstance(t, QSplitter):
            settings.setValue("top_split_sizes", t.saveState())
        settings.setValue("custom_widget_paths", self._custom_widget_files)
        super().closeEvent(event)

    def _wire(self):
        def on_selection_changed(widget):
            if len(self.canvas._multi_selection) >= 2:
                self.props.set_batch_widgets(self.canvas._multi_selection)
            else:
                self.props.set_widget(widget)

        self.canvas.selection_changed.connect(on_selection_changed)
        self.canvas.widget_modified.connect(self._refresh_code)
        self.canvas.widget_modified.connect(self.props.refresh)
        self.canvas.widget_modified.connect(self._update_undo_redo_state)
        self.canvas.widget_modified.connect(self.history_panel.refresh)

        self.btn_undo.clicked.connect(self.canvas.undo)
        self.btn_redo.clicked.connect(self.canvas.redo)

        self.props.property_changed.connect(self._refresh_code)
        self.props.property_changed.connect(
            lambda: (self.canvas._update_handles(), self.canvas.update())
        )

        self.btn_copy.clicked.connect(self._copy_code)
        self.btn_clear.clicked.connect(self._clear)
        self.btn_export_qss.clicked.connect(self._export_qss)
        self.btn_export_project.clicked.connect(self._export_project)
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

        self.canvas.widget_modified.connect(self.widget_tree.rebuild)
        self.canvas.widget_modified.connect(self._sync_page_tabs)
        self.widget_tree.item_selected.connect(
            lambda w: self.props.set_widget(w)
        )

        self.widget_tree.rebuild()
        self._sync_page_tabs()
        self._refresh_code()

    # ── 各交互方法 ──
    def _toggle_grid_action(self, checked):
        self.canvas._grid_enabled = checked
        self.grid_action.setText(
            "📐 网格:ON" if checked else "📐 网格:OFF"
        )
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
            act.triggered.connect(
                lambda checked, ww=w, hh=h, ll=label:
                    self._set_canvas_size(ww, hh, ll)
            )
        menu.addSeparator()
        act_custom = menu.addAction("✏️ 自定义尺寸...")
        act_custom.triggered.connect(self._custom_canvas_size_dialog)
        btn_rect = self.btn_canvas_size.rect()
        global_pos = self.btn_canvas_size.mapToGlobal(
            QPoint(0, btn_rect.height())
        )
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
        w_spin = QSpinBox()
        w_spin.setRange(200, 10000)
        w_spin.setValue(self.canvas.design_width)
        form.addWidget(w_spin)
        form.addWidget(QLabel("高度:"))
        h_spin = QSpinBox()
        h_spin.setRange(200, 10000)
        h_spin.setValue(self.canvas.design_height)
        form.addWidget(h_spin)
        ly.addLayout(form)
        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("确定")
        btn_cancel = QPushButton("取消")
        btn_layout.addStretch()
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        ly.addLayout(btn_layout)
        btn_ok.clicked.connect(dlg.accept)
        btn_cancel.clicked.connect(dlg.reject)
        if dlg.exec() == QDialog.Accepted:
            self._set_canvas_size(w_spin.value(), h_spin.value())

    def _toggle_dark_mode(self, checked):
        global ACTIVE_QSS, DARK_MODE
        DARK_MODE = checked
        ACTIVE_QSS = DARK_QSS if checked else DEFAULT_QSS
        QApplication.instance().setStyleSheet(ACTIVE_QSS)
        self.btn_dark.setText("☀️ 亮色" if checked else "🌙 暗色")
        QSettings("MiniDesigner", "v19").setValue("dark_mode", checked)

    def _toggle_preview(self, checked):
        if checked:
            self.canvas.enter_preview_mode()
            self.btn_preview.setText("✕ 退出预览")
        else:
            self.canvas.exit_preview_mode()
            self.btn_preview.setText("🔍 预览")

    def _on_page_tab_changed(self, idx):
        if idx >= 0 and idx < self.canvas.page_count():
            self.canvas.switch_page(idx)
            self._refresh_code()

    def _on_page_close(self, idx):
        if self.canvas.page_count() <= 1:
            self.statusBar().showMessage("⚠️ 至少保留一个页面")
            return
        self.canvas.remove_page(idx)
        self._sync_page_tabs()
        self._refresh_code()

    def _on_page_rename(self, idx):
        if idx < 0 or idx >= self.canvas.page_count():
            return
        old_name = self.canvas.page_name(idx)
        new_name, ok = QInputDialog.getText(
            self, "重命名页面", "页面名称:", text=old_name
        )
        if ok and new_name.strip():
            self.canvas.rename_page(idx, new_name.strip())
            self._sync_page_tabs()
            self._refresh_code()

    def _on_add_page(self):
        idx = self.canvas.add_page()
        self._sync_page_tabs()
        self.page_tabs.setCurrentIndex(idx)
        self._refresh_code()
        self.statusBar().showMessage(f"✅ 新建页面: {self.canvas.page_name(idx)}")

    def _sync_page_tabs(self):
        self.page_tabs.blockSignals(True)
        while self.page_tabs.count() > 0:
            self.page_tabs.removeTab(0)
        for i in range(self.canvas.page_count()):
            self.page_tabs.addTab(self.canvas.page_name(i))
        self.page_tabs.setCurrentIndex(self.canvas.current_page())
        self.page_tabs.blockSignals(False)

    def _new_project(self):
        if self.canvas._canvas_widgets:
            r = QMessageBox.question(
                self, "新建项目", "当前画布有未保存的内容，是否清空？",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
            )
            if r != QMessageBox.Yes:
                return
        self.canvas.clear_canvas()
        self.canvas.history.undo_stack.clear()
        self.canvas.history.redo_stack.clear()
        self._current_file = None
        self._sync_page_tabs()
        self.setWindowTitle("Mini Designer v19 — 新建项目")
        self._refresh_code()
        self.statusBar().showMessage("✅ 已新建空白项目")

    def _show_template_menu(self):
        menu = QMenu(self)
        for name, tmpl in INDUSTRIAL_TEMPLATES.items():
            action = menu.addAction(name)
            action.setToolTip(tmpl["description"])
            action.triggered.connect(
                lambda checked, n=name: self.canvas.insert_template(n)
            )
        btn_rect = self.btn_template.rect()
        global_pos = self.btn_template.mapToGlobal(
            QPoint(0, btn_rect.height())
        )
        menu.exec(global_pos)

    def _load_custom_widgets(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("🧩 自定义控件文件管理")
        dlg.resize(520, 320)
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        btn_add = QPushButton("📂 添加文件")
        btn_add.setStyleSheet(
            "QPushButton{background:#4A90D9;color:#fff;border:none;"
            "border-radius:4px;padding:5px 12px;font-size:12px;font-weight:bold;}"
            "QPushButton:hover{background:#357ABD;}"
        )
        btn_remove = QPushButton("🗑 移除文件")
        btn_remove.setEnabled(False)
        btn_remove.setStyleSheet(
            "QPushButton{background:#E74C3C;color:#fff;border:none;"
            "border-radius:4px;padding:5px 12px;font-size:12px;font-weight:bold;}"
            "QPushButton:hover{background:#C0392B;}"
            "QPushButton:disabled{background:#ccc;color:#999;}"
        )
        btn_refresh = QPushButton("🔄 刷新")
        btn_refresh.setStyleSheet(
            "QPushButton{background:#f0f0f0;border:1px solid #ccc;"
            "border-radius:4px;padding:5px 12px;font-size:12px;}"
            "QPushButton:hover{background:#e0e0e0;}"
        )
        btn_close = QPushButton("✅ 完成")
        btn_close.setStyleSheet(
            "QPushButton{background:#27AE60;color:#fff;border:none;"
            "border-radius:4px;padding:5px 16px;font-size:12px;font-weight:bold;}"
            "QPushButton:hover{background:#219A52;}"
        )
        btn_row.addWidget(btn_add)
        btn_row.addWidget(btn_remove)
        btn_row.addWidget(btn_refresh)
        btn_row.addStretch()
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

        info_label = QLabel("每个文件独立显示，选中后点击「🗑 移除文件」即可退出")
        info_label.setStyleSheet("color:#888; font-size:11px; padding:2px 2px;")
        layout.addWidget(info_label)

        file_list = QListWidget()
        file_list.setAlternatingRowColors(True)
        file_list.setStyleSheet(
            "QListWidget{font-size:12px;border:1px solid #ddd;border-radius:4px;}"
            " QListWidget::item{padding:6px 8px;}"
            " QListWidget::item:selected{background:#4A90D9;color:#fff;}"
            " QListWidget::item:alternate{background:#f9f9f9;}"
        )
        for fp in self._custom_widget_files:
            item = QListWidgetItem(os.path.basename(fp))
            item.setData(Qt.UserRole, fp)
            item.setToolTip(fp)
            file_list.addItem(item)
        layout.addWidget(file_list, 1)

        widget_info_label = QLabel()
        widget_info_label.setWordWrap(True)
        widget_info_label.setStyleSheet(
            "color:#666; font-size:11px; padding:4px 6px;"
            " background:#f5f5f5; border:1px solid #e0e0e0;"
            " border-radius:4px;"
        )
        widget_info_label.setMaximumHeight(80)
        layout.addWidget(widget_info_label)

        def _update_widget_info():
            from .config import CUSTOM_WIDGETS as CW
            if not CW:
                widget_info_label.setText(
                    "💡 当前无自定义控件，点击「📂 添加文件」加载 .py 文件"
                )
                return
            lines = []
            for name, cls, kwargs, fp in CW:
                lines.append(
                    f"  • {name}  ({cls.__name__})  ← {os.path.basename(fp)}"
                )
            widget_info_label.setText(
                "📦 已注册控件:\n" + "\n".join(lines)
            )

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
            from .config import CUSTOM_WIDGETS as CW
            CW.clear()
            count = CustomWidgetLoader.register_widgets(
                self._custom_widget_files
            )
            self.toolbox.populate()
            settings = QSettings("MiniDesigner", "v19")
            settings.setValue("custom_widget_paths", self._custom_widget_files)
            self.statusBar().showMessage(
                f"✅ 已加载 {count} 个自定义控件"
                f"（{len(self._custom_widget_files)} 个文件）"
            )
            _refresh_file_list()

        def _add_files():
            paths, _ = QFileDialog.getOpenFileNames(
                dlg, "选择自定义控件Python文件", "", "Python Files (*.py)"
            )
            if not paths:
                return
            all_paths = list(dict.fromkeys(self._custom_widget_files + paths))
            if all_paths != self._custom_widget_files:
                self._custom_widget_files = all_paths
                _reload_custom_widgets()

        def _remove_selected():
            current = file_list.currentItem()
            if not current:
                return
            fp = current.data(Qt.UserRole)
            if not fp:
                return
            base_name = os.path.basename(fp)
            reply = QMessageBox.question(
                dlg, "确认移除",
                f"确定要移除文件「{base_name}」及其所有自定义控件？\n\n{fp}",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return
            self._custom_widget_files.remove(fp)
            _reload_custom_widgets()
            self.statusBar().showMessage(f"✅ 已移除文件: {base_name}")

        btn_add.clicked.connect(_add_files)
        btn_remove.clicked.connect(_remove_selected)
        btn_refresh.clicked.connect(_reload_custom_widgets)
        btn_close.clicked.connect(dlg.accept)
        dlg.exec()

    def _open_theme_editor(self):
        global ACTIVE_QSS
        dlg = ThemeEditorDialog(ACTIVE_QSS, self)
        dlg.qss_changed.connect(self._live_preview_qss)
        result = dlg.exec()
        if result == QDialog.Accepted:
            ACTIVE_QSS = dlg.get_qss()
            QApplication.instance().setStyleSheet(ACTIVE_QSS)
            self.statusBar().showMessage("✅ 主题已应用")
        else:
            QApplication.instance().setStyleSheet(ACTIVE_QSS)
            self.statusBar().showMessage("❌ 主题编辑已取消，已恢复")

    def _live_preview_qss(self, qss_text):
        try:
            QApplication.instance().setStyleSheet(qss_text)
        except Exception:
            pass

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
            self.statusBar().showMessage(
                "✅ 当前模式: Ui类模式 — 生成 class Ui_MainWindow(object)"
            )
        else:
            self.btn_ui_class.setText("🪟 独立窗口")
            self.btn_ui_class.setStyleSheet(
                "QToolButton{padding:5px 10px;font-size:12px;}"
            )
            self.statusBar().showMessage(
                "✅ 当前模式: 独立窗口 — 生成 class GeneratedWindow(QMainWindow)"
            )
        self._refresh_code()

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

    def _update_undo_redo_state(self):
        self.btn_undo.setEnabled(self.canvas.history.can_undo())
        self.btn_redo.setEnabled(self.canvas.history.can_redo())

    def _refresh_code(self):
        self.code_view.setPlainText(
            CodeGenerator.generate(
                self.canvas, as_ui_class=self._ui_class_mode
            )
        )

    def _copy_code(self):
        QApplication.clipboard().setText(self.code_view.toPlainText())
        self.btn_copy.setText("已复制!")
        self.btn_copy.setEnabled(False)
        QTimer.singleShot(
            1500,
            lambda: (
                self.btn_copy.setText("复制代码"),
                self.btn_copy.setEnabled(True),
            ),
        )

    def _clear(self):
        if (
            QMessageBox.question(
                self, "清空画布", "确定移除所有控件吗？",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
            )
            == QMessageBox.Yes
        ):
            self.canvas.clear_canvas()
            self.canvas.history.undo_stack.clear()
            self.canvas.history.redo_stack.clear()
            self._refresh_code()

    def _export_qss(self):
        global ACTIVE_QSS
        path, _ = QFileDialog.getSaveFileName(
            self, "导出全局样式表", "style.qss", "QSS Files (*.qss)"
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(ACTIVE_QSS)
            QMessageBox.information(
                self, "导出成功", f"样式表已保存至:\n{path}"
            )

    def _export_project(self):
        import shutil
        from .config import CUSTOM_WIDGETS as CW, _sanitize, ACTIVE_QSS, DARK_MODE

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
            self, "选择导出目标目录", "", QFileDialog.ShowDirsOnly
        )
        if not target_dir:
            return
        try:
            self.canvas._save_current_page()
            code = CodeGenerator.generate(
                self.canvas, as_ui_class=use_ui_class,
                qss_filename=f"{project_name}.qss"
            )
            if not code:
                raise RuntimeError("代码生成为空")

            # {name}.py
            with open(
                os.path.join(target_dir, f"{project_name}.py"), "w", encoding="utf-8"
            ) as f:
                f.write(code + "\n")

            reqs = ["PySide6>=6.5.0"]
            copied = []
            for _, _, _, filepath in CW:
                if not filepath or not os.path.isfile(filepath):
                    continue
                basename = os.path.basename(filepath)
                dest = os.path.join(target_dir, basename)
                if not os.path.exists(dest):
                    shutil.copy2(filepath, dest)
                    copied.append(basename)
                reqs.append(os.path.splitext(basename)[0])
            with open(
                os.path.join(target_dir, "requirements.txt"),
                "w", encoding="utf-8",
            ) as f:
                f.write("\n".join(reqs) + "\n")

            # {name}.json — 设计器可重新打开
            self.canvas.save_project(os.path.join(target_dir, f"{project_name}.json"))

            # {name}.qss — 样式表
            qss = ACTIVE_QSS if not DARK_MODE else DEFAULT_QSS
            with open(
                os.path.join(target_dir, f"{project_name}.qss"), "w", encoding="utf-8"
            ) as f:
                f.write(qss)

            tags_found = any(
                w.property("_tag")
                for p in self.canvas._pages
                for w in p.get("widgets", [])
                if not w.property("_designer_hidden")
            )
            if tags_found:
                with open(
                    os.path.join(target_dir, "opc_comm.py"),
                    "w", encoding="utf-8",
                ) as f:
                    f.write(
                        "import time, threading, random, math\n\n"
                        "class DataSource(threading.Thread):\n"
                        "    def __init__(self, data_binder):\n"
                        "        super().__init__(daemon=True)\n"
                        "        self.binder = data_binder\n"
                        "        self.running = True\n"
                        "    def run(self):\n"
                        "        t = 0\n"
                        "        while self.running:\n"
                        "            temp = 75 + 15 * math.sin(t * 0.5)\n"
                        "            self.binder.update_tag('temp_value', temp)\n"
                        "            time.sleep(0.5); t += 0.5\n"
                    )
            self.statusBar().showMessage(f"✅ 已导出 {project_name} 到: {target_dir}")
            QTimer.singleShot(
                200,
                lambda: QMessageBox.information(
                    self, "导出成功",
                    f"项目: {project_name}\n"
                    f"目录: {target_dir}\n"
                    f"{project_name}.py + {project_name}.json + {project_name}.qss + requirements.txt"
                    + (f"\n自定义控件: {', '.join(copied)}" if copied else "")
                    + ("\nopc_comm.py" if tags_found else ""),
                ),
            )
        except Exception as e:
            QTimer.singleShot(
                200,
                lambda: QMessageBox.critical(
                    self, "导出失败", str(e)[:200]
                ),
            )

    def _save_project(self):
        import traceback as _tb
        try:
            default = self._current_file or "untitled.json"
            path, _ = QFileDialog.getSaveFileName(
                self, "保存项目", default, "JSON Files (*.json)"
            )
            if not path:
                return
            self.canvas._deselect()
            self.canvas._save_current_page()
            QApplication.processEvents()
            self.canvas.save_project(path)
            self._current_file = path
            self.setWindowTitle(
                f"Mini Designer v19 — {os.path.basename(path)}"
            )
            self.statusBar().showMessage(f"✅ 已保存: {path}")
        except Exception as e:
            _tb.print_exc()
            self.statusBar().showMessage(f"❌ 保存失败: {str(e)[:80]}")

    def _load_project(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "打开项目", "", "JSON Files (*.json)"
        )
        if path:
            self.canvas.load_project(path)
            self._current_file = path
            self.setWindowTitle(
                f"Mini Designer v19 — {os.path.basename(path)}"
            )
            self._sync_page_tabs()
            self._refresh_code()
            self.statusBar().showMessage(f"✅ 已加载: {path}")


def main():
    app = QApplication([])
    win = DesignerMainWindow()
    win.show()
    app.exec()
