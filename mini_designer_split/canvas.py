"""mini_designer_split/canvas.py — 设计器画布核心"""

import json, os, math, random
from collections import defaultdict, deque

from PySide6.QtCore import (
    Qt, QMimeData, QEvent, Signal, QRect, QPoint, QSize, QTimer, QRectF, QPointF,
)
from PySide6.QtGui import QDrag, QColor, QFont, QPainter, QPen, QKeySequence, QShortcut, QBrush
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QListWidget, QTreeWidget, QTableWidget, QTextEdit as QWTextEdit,
    QTextBrowser, QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox,
    QSlider, QProgressBar, QCheckBox, QRadioButton, QGroupBox,
    QLCDNumber, QDial, QCommandLinkButton, QTabWidget, QScrollArea,
    QToolButton, QDialogButtonBox, QCalendarWidget, QStackedWidget,
    QSplitter, QSizePolicy, QApplication, QMenu, QFileDialog, QInputDialog,
)

from .config import (
    MIME_TYPE, HANDLE_SIZE, HANDLE_HALF, MIN_W, MIN_H, HANDLE_CURSORS,
    VIEWPORT_WIDGETS, SNAP_THRESHOLD, ARROW_STEP, DESIGN_WIDTH, DESIGN_HEIGHT,
    GRID_SIZE, SIZE_POLICY_MAP, SIZE_POLICY_NAMES, _policy_to_str,
    WIDGET_ROLES, BINDABLE_WIDGETS, WIDGET_SIGNALS,
    get_display_to_entry, NAME_TO_PREFIX, DEFAULT_SIZES, _sanitize,
    INDUSTRIAL_TEMPLATES,
)
from .commands import (
    AddWidgetCmd, DeleteWidgetCmd, MoveWidgetCmd, ResizeWidgetCmd,
    PropertyChangeCmd, BatchPropertyChangeCmd, BatchAlignCmd,
    ReorderWidgetCmd, ExtractWidgetCmd, InsertTemplateCmd,
    _ReparentIntoContainerCmd, _ReparentBetweenContainersCmd,
    HistoryManager,
)
from .codegen import CodeGenerator
from .dialogs.signal_slot import SignalSlotDialog
from .dialogs.callback_editor import CallbackEditorDialog


class _Placeholder(QLabel):
    """画布空白时的占位提示"""
    pass


class DesignerCanvas(QWidget):
    """设计器画布 — 控件拖拽/选择/移动/缩放/对齐/预览"""

    selection_changed = Signal(object)
    widget_modified = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMinimumSize(400, 400)
        self.setMouseTracking(True)

        self._canvas_widgets = []
        self.history = HistoryManager()
        self._clipboard_data = None
        self._style_clipboard = None
        self._multi_selection = []
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
        self._pages = [{"name": "页面1", "widgets": []}]
        self._current_page = 0

        self._placeholder = _Placeholder(
            "将左侧控件拖拽到此处\nCtrl+点击多选 | G键切换网格 | 右键信号/槽", self
        )
        self._placeholder.setAlignment(Qt.AlignCenter)
        self._placeholder.setStyleSheet(
            "color:#bbb; font-size:16px; background:transparent; border:none;"
        )
        self._placeholder.resize(400, 60)

        self._handles = {}
        for pos in HANDLE_CURSORS:
            h = QFrame(self)
            h.setFixedSize(HANDLE_SIZE, HANDLE_SIZE)
            h.setStyleSheet("background:#4A90D9; border:1px solid white;")
            h.setCursor(HANDLE_CURSORS[pos])
            h.setVisible(False)
            h._is_handle = True
            h._handle_pos = pos
            h.installEventFilter(self)
            self._handles[pos] = h

        self._selected = None
        self._move_active = False
        self._resize_active = False
        self._active_handle = None
        self._drag_start_mouse = QPoint()
        self._drag_start_geom = QRect()
        self._snap_guides = []
        self._insert_indicator = None
        self._drag_start_geoms = {}

        # 快捷键
        QShortcut(QKeySequence.Delete, self).activated.connect(self._delete_selected)
        QShortcut(QKeySequence("Ctrl+Z"), self).activated.connect(self.undo)
        QShortcut(QKeySequence("Ctrl+Y"), self).activated.connect(self.redo)
        QShortcut(QKeySequence("Ctrl+C"), self).activated.connect(self._copy_selected)
        QShortcut(QKeySequence("Ctrl+V"), self).activated.connect(self._paste_widget)
        QShortcut(QKeySequence(Qt.Key_Up), self).activated.connect(
            lambda: self._arrow_move(0, -ARROW_STEP)
        )
        QShortcut(QKeySequence(Qt.Key_Down), self).activated.connect(
            lambda: self._arrow_move(0, ARROW_STEP)
        )
        QShortcut(QKeySequence(Qt.Key_Left), self).activated.connect(
            lambda: self._arrow_move(-ARROW_STEP, 0)
        )
        QShortcut(QKeySequence(Qt.Key_Right), self).activated.connect(
            lambda: self._arrow_move(ARROW_STEP, 0)
        )
        QShortcut(QKeySequence(Qt.Key_Tab), self).activated.connect(
            lambda: self._tab_navigate(1)
        )
        QShortcut(QKeySequence("Shift+Tab"), self).activated.connect(
            lambda: self._tab_navigate(-1)
        )
        QShortcut(QKeySequence("G"), self).activated.connect(self._toggle_grid)

    # ── 撤销/重做快捷方法 ──
    def undo(self):
        self.history.undo()
        self._deselect()
        self.widget_modified.emit()
        self.update()

    def redo(self):
        self.history.redo()
        self._deselect()
        self.widget_modified.emit()
        self.update()

    # ── 网格 ──
    def _toggle_grid(self):
        self._grid_enabled = not self._grid_enabled
        self.update()
        win = self.window()
        if hasattr(win, "grid_action"):
            win.grid_action.setChecked(self._grid_enabled)
            win.grid_action.setText(
                "📐 网格:ON" if self._grid_enabled else "📐 网格:OFF"
            )
        if hasattr(win, "statusBar"):
            state = "开启" if self._grid_enabled else "关闭"
            win.statusBar().showMessage(f"网格已{state} (G键切换)")

    # ── 预览模式 ──
    def enter_preview_mode(self):
        """进入运行时预览模式 — 隐藏所有编辑辅助元素"""
        self._preview_mode = True
        self._deselect()
        for h in self._handles.values():
            h.setVisible(False)
        for w in self._canvas_widgets:
            w.setAttribute(Qt.WA_TransparentForMouseEvents, False)
            if hasattr(w, 'start') and hasattr(w, '_demo_timer'):
                w.start()
        self.setCursor(Qt.ArrowCursor)
        if self._preview_btn is None:
            self._preview_btn = QPushButton("✕ 退出预览 (ESC)", self)
            self._preview_btn.setStyleSheet(
                "QPushButton{background:#E74C3C;color:#fff;border:none;"
                "border-radius:4px;padding:6px 14px;font-size:12px;font-weight:bold;}"
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
            win.statusBar().showMessage(
                "🔍 预览模式 — 控件可交互 | 按 ESC 退出"
            )

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
            win.statusBar().showMessage(
                "✅ 已返回编辑模式 | G键切换网格"
            )
        if hasattr(win, "btn_preview"):
            win.btn_preview.setChecked(False)
            win.btn_preview.setText("🔍 预览")

    # ── 多页面管理 ──
    def page_count(self):
        return len(self._pages)

    def current_page(self):
        return self._current_page

    def page_name(self, idx=None):
        if idx is None:
            idx = self._current_page
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
        if len(self._pages) <= 1:
            return False
        self._save_current_page()
        for w in self._pages[idx]["widgets"]:
            w.hide()
            w.deleteLater()
        del self._pages[idx]
        if self._current_page >= len(self._pages):
            self._current_page = len(self._pages) - 1
        self._canvas_widgets = self._pages[self._current_page]["widgets"]
        for w in self._canvas_widgets:
            if not w.property("_designer_hidden"):
                w.show()
        self._deselect()
        self.widget_modified.emit()
        return True

    def switch_page(self, idx):
        """切换到指定页面"""
        if idx == self._current_page or idx < 0 or idx >= len(self._pages):
            return
        self._save_current_page()
        for w in self._canvas_widgets:
            w.hide()
        self._current_page = idx
        self._canvas_widgets = self._pages[idx]["widgets"]
        for w in self._canvas_widgets:
            if not w.property("_designer_hidden"):
                w.show()
        self._deselect()
        self.widget_modified.emit()

    def rename_page(self, idx, name):
        if 0 <= idx < len(self._pages):
            self._pages[idx]["name"] = name
            self.widget_modified.emit()

    def _save_current_page(self):
        if 0 <= self._current_page < len(self._pages):
            self._pages[self._current_page]["widgets"] = self._canvas_widgets

    # ── 网格对齐 ──
    def _snap_to_grid(self, value):
        if not self._grid_enabled:
            return value
        return round(value / GRID_SIZE) * GRID_SIZE

    def set_canvas_size(self, w, h):
        self.design_width = int(w)
        self.design_height = int(h)
        self.setMinimumSize(self.design_width, self.design_height)
        self.resize(self.design_width, self.design_height)
        if self._placeholder:
            self._placeholder.move(
                (self.width() - self._placeholder.width()) // 2,
                (self.height() - self._placeholder.height()) // 2,
            )
        self.update()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        ph = self._placeholder
        ph.move(
            (self.width() - ph.width()) // 2,
            (self.height() - ph.height()) // 2,
        )
        if self._preview_btn:
            self._preview_btn.move(self.width() - 140, 8)

    def wheelEvent(self, event):
        if self._preview_mode:
            return
        if event.modifiers() & Qt.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self._zoom_factor = min(2.0, self._zoom_factor + 0.1)
            else:
                self._zoom_factor = max(0.5, self._zoom_factor - 0.1)
            self._zoom_factor = round(self._zoom_factor, 1)
            self._update_handles()
            self.update()
            win = self.window()
            if hasattr(win, "statusBar"):
                win.statusBar().showMessage(
                    f"🔍 缩放: {int(self._zoom_factor*100)}%  |  Ctrl+滚轮调节"
                )
            event.accept()
        else:
            super().wheelEvent(event)

    # ── 拖放 ──
    def dragEnterEvent(self, e):
        if e.mimeData().hasFormat(MIME_TYPE):
            e.acceptProposedAction()
        else:
            e.ignore()

    def dragMoveEvent(self, e):
        if e.mimeData().hasFormat(MIME_TYPE):
            e.acceptProposedAction()
            self._update_insert_indicator(e.position().toPoint())
            self.update()
        else:
            e.ignore()

    def dropEvent(self, e):
        display_name = bytes(e.mimeData().data(MIME_TYPE)).decode()
        pos = e.position().toPoint()
        self._insert_indicator = None
        self.history.push(AddWidgetCmd(self, display_name, pos))
        self.widget_modified.emit()
        e.acceptProposedAction()

    def _tab_navigate(self, direction):
        visible_widgets = [
            w for w in self._canvas_widgets
            if w.isVisible() and not w.property("_designer_hidden")
        ]
        if not visible_widgets:
            return
        if self._selected is None:
            self._select(visible_widgets[0])
            return
        try:
            idx = visible_widgets.index(self._selected)
        except ValueError:
            idx = -1
        self._select(visible_widgets[(idx + direction) % len(visible_widgets)])

    def align_widgets(self, align_type):
        widgets = (
            self._multi_selection
            if len(self._multi_selection) >= 2
            else ([self._selected] if self._selected else [])
        )
        widgets = [
            w for w in widgets
            if w.isVisible() and not w.property("_designer_hidden")
        ]
        if len(widgets) < 2:
            self._update_status_bar("⚠️ 至少需要选中2个控件才能对齐")
            return
        old_geos = [QRect(w.geometry()) for w in widgets]
        new_geos = [QRect(g) for g in old_geos]
        if align_type == "left":
            target = min(g.x() for g in old_geos)
            [g.setX(target) for g in new_geos]
        elif align_type == "right":
            target = max(g.right() for g in old_geos)
            [g.setRight(target) for g in new_geos]
        elif align_type == "top":
            target = min(g.y() for g in old_geos)
            [g.setY(target) for g in new_geos]
        elif align_type == "bottom":
            target = max(g.bottom() for g in old_geos)
            [g.setBottom(target) for g in new_geos]
        elif align_type == "hcenter":
            target = sum(g.center().x() for g in old_geos) // len(old_geos)
            [g.moveCenter(QPoint(target, g.center().y())) for g in new_geos]
        elif align_type == "vcenter":
            target = sum(g.center().y() for g in old_geos) // len(old_geos)
            [g.moveCenter(QPoint(g.center().x(), target)) for g in new_geos]
        elif align_type == "same_width":
            target = max(g.width() for g in old_geos)
            [g.setWidth(target) for g in new_geos]
        elif align_type == "same_height":
            target = max(g.height() for g in old_geos)
            [g.setHeight(target) for g in new_geos]
        elif align_type == "distribute_h":
            sp = sorted(
                zip(old_geos, range(len(old_geos))), key=lambda p: p[0].x()
            )
            if len(sp) >= 3:
                tw = sum(g.width() for g, _ in sp)
                le = sp[0][0].x()
                re_ = sp[-1][0].right()
                gap = (re_ - le - tw) // (len(sp) - 1) if len(sp) > 1 else 0
                cx = le
                for g, idx in sp:
                    new_geos[idx].setX(cx)
                    cx += g.width() + gap
        elif align_type == "distribute_v":
            sp = sorted(
                zip(old_geos, range(len(old_geos))), key=lambda p: p[0].y()
            )
            if len(sp) >= 3:
                th = sum(g.height() for g, _ in sp)
                te = sp[0][0].y()
                be = sp[-1][0].bottom()
                gap = (be - te - th) // (len(sp) - 1) if len(sp) > 1 else 0
                cy = te
                for g, idx in sp:
                    new_geos[idx].setY(cy)
                    cy += g.height() + gap
        self.history.push(BatchAlignCmd(self, widgets, old_geos, new_geos))
        self.widget_modified.emit()
        self.update()
        self._update_status_bar(
            f"✅ 已对齐: {align_type} ({len(widgets)}个控件)"
        )

    def insert_template(self, template_name):
        tmpl = INDUSTRIAL_TEMPLATES.get(template_name)
        if not tmpl:
            return
        base_pos = QPoint(
            self.width() // 2 - 140, self.height() // 2 - 80
        )
        self.history.push(InsertTemplateCmd(self, tmpl["widgets"], base_pos))
        self._update_status_bar(f"🏭 已插入模板: {template_name}")

    # ── 复制/粘贴 ──
    def _copy_selected(self):
        w = self._selected
        if not w:
            return
        self._clipboard_data = {
            "display_name": w.property("_display_name"),
            "role": w.property("role") or "default",
            "objectName": w.objectName(),
            "styleSheet": w.styleSheet(),
            "w": w.width(), "h": w.height(),
            "hSizePolicy": _policy_to_str(w.sizePolicy().horizontalPolicy()),
            "vSizePolicy": _policy_to_str(w.sizePolicy().verticalPolicy()),
            "minWidth": w.minimumWidth(), "minHeight": w.minimumHeight(),
            "maxWidth": w.maximumWidth(), "maxHeight": w.maximumHeight(),
            "tag": w.property("_tag") or "",
            "anchor_left": bool(w.property("_anchor_left")),
            "anchor_right": bool(w.property("_anchor_right")),
            "anchor_top": bool(w.property("_anchor_top")),
            "anchor_bottom": bool(w.property("_anchor_bottom")),
        }
        if hasattr(w, "text") and not isinstance(w, QGroupBox):
            self._clipboard_data["text"] = w.text()
        if hasattr(w, "title") and isinstance(w, QGroupBox):
            self._clipboard_data["title"] = w.title()
        if isinstance(w, (QLineEdit, QWTextEdit)):
            self._clipboard_data["placeholderText"] = w.placeholderText()
        if hasattr(w, "value") and callable(getattr(w, "value", None)):
            self._clipboard_data["value"] = w.value()
        self._update_status_bar(f"📋 已复制: {w.objectName()}")

    def _copy_style(self):
        w = self._selected
        if not w:
            return
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
        if not self._style_clipboard:
            return
        targets = (
            self._multi_selection if len(self._multi_selection) >= 2
            else ([self._selected] if self._selected else [])
        )
        targets = [
            w for w in targets
            if w.isVisible() and not w.property("_designer_hidden")
        ]
        if not targets:
            return
        sc = self._style_clipboard
        for w in targets:
            w.setProperty("role", sc["role"])
            w.style().unpolish(w)
            w.style().polish(w)
            if sc.get("styleSheet"):
                w.setStyleSheet(sc["styleSheet"])
            if "fontFamily" in sc and hasattr(w, 'setFont'):
                f = QFont(
                    sc["fontFamily"],
                    sc.get("fontSize", 9)
                )
                f.setBold(sc.get("fontBold", False))
                f.setItalic(sc.get("fontItalic", False))
                w.setFont(f)
        self.widget_modified.emit()
        self.update()
        self._update_status_bar(
            f"🎨 已粘贴样式到 {len(targets)} 个控件"
        )

    def _paste_widget(self):
        if not self._clipboard_data:
            return
        data = self._clipboard_data
        paste_pos = (
            QPoint(self._selected.x() + 10, self._selected.y() + 10)
            if self._selected
            else QPoint(self.width() // 2 - 60, self.height() // 2 - 18)
        )
        dn = data.get("display_name")
        if not dn:
            return
        entry_map = get_display_to_entry()
        if dn not in entry_map:
            return
        w = self._create_widget_internal(dn, paste_pos)
        if not w:
            return
        w.resize(data.get("w", 100), data.get("h", 30))
        if "objectName" in data:
            w.setObjectName(data["objectName"])
        if "role" in data:
            w.setProperty("role", data["role"])
            w.style().unpolish(w)
            w.style().polish(w)
        if "styleSheet" in data and data["styleSheet"]:
            w.setStyleSheet(data["styleSheet"])
        if "text" in data and hasattr(w, "setText"):
            w.setText(data["text"])
        if "title" in data and hasattr(w, "setTitle"):
            w.setTitle(data["title"])
        if "placeholderText" in data and hasattr(w, "setPlaceholderText"):
            w.setPlaceholderText(data["placeholderText"])
        if "value" in data and hasattr(w, "setValue"):
            try:
                w.setValue(data["value"])
            except Exception:
                pass
        if data.get("tag"):
            w.setProperty("_tag", data["tag"])
        w.setProperty("_anchor_left", data.get("anchor_left", False))
        w.setProperty("_anchor_right", data.get("anchor_right", False))
        w.setProperty("_anchor_top", data.get("anchor_top", False))
        w.setProperty("_anchor_bottom", data.get("anchor_bottom", False))
        sp = w.sizePolicy()
        sp.setHorizontalPolicy(
            SIZE_POLICY_MAP.get(
                data.get("hSizePolicy", "Preferred"), QSizePolicy.Preferred
            )
        )
        sp.setVerticalPolicy(
            SIZE_POLICY_MAP.get(
                data.get("vSizePolicy", "Preferred"), QSizePolicy.Preferred
            )
        )
        w.setSizePolicy(sp)
        w.setMinimumWidth(data.get("minWidth", 0))
        w.setMinimumHeight(data.get("minHeight", 0))
        w.setMaximumWidth(data.get("maxWidth", 16777215))
        w.setMaximumHeight(data.get("maxHeight", 16777215))
        # 将创建操作加入撤销栈
        cmd = AddWidgetCmd.__new__(AddWidgetCmd)
        cmd.canvas = self
        cmd.display_name = dn
        cmd.pos = paste_pos
        cmd.widget = w
        self.history.undo_stack.append(cmd)
        self.history.redo_stack.clear()
        self.widget_modified.emit()
        self._update_status_bar(f"📋 已粘贴: {w.objectName()}")

    def _arrow_move(self, dx, dy):
        w = self._selected
        if not w or w.property("_locked"):
            return
        parent = w.parent()
        if parent and hasattr(parent, "_content_layout"):
            return
        old_pos = w.pos()
        step = GRID_SIZE if self._grid_enabled else ARROW_STEP
        new_x = max(
            0,
            min(
                old_pos.x() + dx * step // ARROW_STEP,
                self.width() - w.width(),
            ),
        )
        new_y = max(
            0,
            min(
                old_pos.y() + dy * step // ARROW_STEP,
                self.height() - w.height(),
            ),
        )
        if self._grid_enabled:
            new_x = self._snap_to_grid(new_x)
            new_y = self._snap_to_grid(new_y)
        new_pos = QPoint(new_x, new_y)
        if new_pos != old_pos:
            self.history.push(MoveWidgetCmd(self, w, old_pos, new_pos))
            self.widget_modified.emit()
            self._update_handles()
            self.update()
            self._update_status_bar(
                f"微调: {w.objectName()} → ({new_x}, {new_y})"
            )

    def _toggle_lock(self):
        w = self._selected
        if not w:
            return
        locked = not bool(w.property("_locked"))
        w.setProperty("_locked", locked)
        self._update_status_bar(
            f"{'🔒 已锁定' if locked else '🔓 已解锁'}: {w.objectName()}"
        )
        self.widget_modified.emit()

    def _toggle_hide(self):
        w = self._selected
        if not w:
            return
        hidden = not bool(w.property("_designer_hidden"))
        w.setProperty("_designer_hidden", hidden)
        if hidden:
            w.hide()
            self._deselect()
        else:
            w.show()
            self._select(w)
        self._update_status_bar(
            f"{'👁️‍🗨️ 已隐藏' if hidden else '👁️ 已显示'}: "
            f"{w.objectName() if not hidden else '(已隐藏)'}"
        )
        self.widget_modified.emit()

    # ── 吸附 ──
    def _calc_snap_guides(self, moving_rect, exclude_widget=None):
        guides = []
        snap_x, snap_y = None, None
        min_dx, min_dy = SNAP_THRESHOLD + 1, SNAP_THRESHOLD + 1
        edges_x = [
            moving_rect.left(), moving_rect.center().x(), moving_rect.right()
        ]
        edges_y = [
            moving_rect.top(), moving_rect.center().y(), moving_rect.bottom()
        ]
        for w in self._canvas_widgets:
            if w is exclude_widget or not w.isVisible():
                continue
            r = w.geometry()
            for ex in edges_x:
                for tx in [r.left(), r.center().x(), r.right()]:
                    dx = abs(ex - tx)
                    if dx < min_dx:
                        min_dx = dx
                        snap_x = tx
            for ey in edges_y:
                for ty in [r.top(), r.center().y(), r.bottom()]:
                    dy = abs(ey - ty)
                    if dy < min_dy:
                        min_dy = dy
                        snap_y = ty
        parent = self._selected.parent() if self._selected else None
        in_container = parent and hasattr(parent, '_content_layout')
        if in_container:
            cr = parent.geometry()
            boundary_x = [cr.left() + 8, cr.right() - 8]
            boundary_y = [cr.top() + 8, cr.bottom() - 8]
        else:
            boundary_x = [0, self.width()]
            boundary_y = [0, self.height()]
        for ex in edges_x:
            for bx in boundary_x:
                dx = abs(ex - bx)
                if dx < min_dx:
                    min_dx = dx
                    snap_x = bx
        for ey in edges_y:
            for by in boundary_y:
                dy = abs(ey - by)
                if dy < min_dy:
                    min_dy = dy
                    snap_y = by
        if min_dx <= SNAP_THRESHOLD and snap_x is not None:
            guides.append(('x', snap_x))
        if min_dy <= SNAP_THRESHOLD and snap_y is not None:
            guides.append(('y', snap_y))
        return guides, snap_x, snap_y, min_dx, min_dy

    def _update_insert_indicator(self, pos):
        self._insert_indicator = None
        for w in reversed(self._canvas_widgets):
            if (
                hasattr(w, "_content_layout")
                and w.geometry().contains(pos)
            ):
                ly = w._content_layout
                count = ly.count()
                if count == 0:
                    self._insert_indicator = (w, w.geometry().top() + 8)
                else:
                    insert_y = w.geometry().bottom() - 8
                    for i in range(count):
                        item = ly.itemAt(i)
                        if item and item.widget() and pos.y() < item.widget().geometry().bottom():
                            insert_y = item.widget().geometry().top()
                            break
                    self._insert_indicator = (w, insert_y)
                return

    def _install_filter_recursive(self, widget):
        widget.installEventFilter(self)
        if isinstance(widget, VIEWPORT_WIDGETS):
            vp = widget.viewport()
            if vp:
                vp.installEventFilter(self)
        if hasattr(widget, "_content_layout"):
            ly = widget._content_layout
            for i in range(ly.count()):
                child = ly.itemAt(i).widget()
                if child:
                    self._install_filter_recursive(child)

    # ── 控件创建/移除 ──
    def _create_widget_internal(self, display_name, drop_pos):
        entry_map = get_display_to_entry()
        entry = entry_map.get(display_name)
        if not entry:
            return None
        _, qt_cls, init_kwargs = entry[:3]
        src_file = entry[3] if len(entry) > 3 else None
        container = next(
            (
                w
                for w in reversed(self._canvas_widgets)
                if hasattr(w, "_content_layout")
                and w.geometry().contains(drop_pos)
            ),
            None,
        )
        if qt_cls is None and "layout" in init_kwargs:
            lt = init_kwargs["layout"]
            c = "#4A90D9" if lt == "vbox" else "#E67E22"
            lc = QVBoxLayout if lt == "vbox" else QHBoxLayout
            w = QFrame()
            w.setFrameShape(QFrame.StyledPanel)
            w.setMinimumSize(80, 60)
            w.setStyleSheet(
                f"QFrame{{border:2px dashed {c};background:rgba(255,255,255,0.04);}}"
            )
            ly = lc(w)
            ly.setContentsMargins(8, 8, 8, 8)
            ly.setSpacing(4)
            w._content_layout = ly
        elif qt_cls:
            try:
                w = qt_cls()
            except Exception as e:
                print(f"[Canvas] 创建控件失败 {display_name}: {e}")
                return None
            if "text" in init_kwargs and hasattr(w, "setText"):
                w.setText(init_kwargs["text"])
            if "title" in init_kwargs and hasattr(w, "setTitle"):
                w.setTitle(init_kwargs["title"])
            if "placeholderText" in init_kwargs and hasattr(w, "setPlaceholderText"):
                w.setPlaceholderText(init_kwargs["placeholderText"])
            if "items" in init_kwargs and hasattr(w, "addItems"):
                w.addItems(init_kwargs["items"])
            if "range" in init_kwargs and hasattr(w, "setRange"):
                w.setRange(*init_kwargs["range"])
            if "value" in init_kwargs and hasattr(w, "setValue"):
                w.setValue(init_kwargs["value"])
            if "decimals" in init_kwargs and hasattr(w, "setDecimals"):
                w.setDecimals(init_kwargs["decimals"])
            if "orientation" in init_kwargs and hasattr(w, "setOrientation"):
                w.setOrientation(init_kwargs["orientation"])
            if "frameShape" in init_kwargs and hasattr(w, "setFrameShape"):
                w.setFrameShape(init_kwargs["frameShape"])
            if "openExternalLinks" in init_kwargs and hasattr(w, "setOpenExternalLinks"):
                w.setOpenExternalLinks(init_kwargs["openExternalLinks"])
        else:
            return None

        w.setProperty("_display_name", display_name)
        w.setProperty("role", "default")
        w.setProperty("_locked", False)
        w.setProperty("_designer_hidden", False)
        w.setProperty("_tag", "")
        w.setProperty("_anchor_left", False)
        w.setProperty("_anchor_right", False)
        if src_file:
            w.setProperty("_custom_source", src_file)
        w.setProperty("_anchor_top", False)
        w.setProperty("_anchor_bottom", False)

        existing = set()

        def collect(ws):
            for ww in ws:
                existing.add(ww.objectName())
                if hasattr(ww, "_content_layout"):
                    collect(
                        [
                            ww._content_layout.itemAt(i).widget()
                            for i in range(ww._content_layout.count())
                            if ww._content_layout.itemAt(i)
                            and ww._content_layout.itemAt(i).widget()
                        ]
                    )

        collect(self._canvas_widgets)
        prefix = NAME_TO_PREFIX.get(display_name, _sanitize(display_name))
        i = 1
        while f"{prefix}_{i}" in existing:
            i += 1
        w.setObjectName(f"{prefix}_{i}")
        w.setProperty("_auto_objectName", True)

        if container:
            w.setParent(container)
            container._content_layout.addWidget(w)
        else:
            w.setParent(self)
            sz = DEFAULT_SIZES.get(display_name, QSize(120, 36))
            w.resize(sz)
            x = max(
                0,
                min(
                    drop_pos.x() - sz.width() // 2,
                    self.width() - sz.width(),
                ),
            )
            y = max(
                0,
                min(
                    drop_pos.y() - sz.height() // 2,
                    self.height() - sz.height(),
                ),
            )
            if self._grid_enabled:
                x = self._snap_to_grid(x)
                y = self._snap_to_grid(y)
            w.move(x, y)
            self._canvas_widgets.append(w)

        self._install_filter_recursive(w)
        w.show()
        if self._placeholder.isVisible():
            self._placeholder.setVisible(False)
        self._select(w)
        return w

    def _remove_widget_internal(self, widget):
        self._deselect()
        if widget in self._canvas_widgets:
            self._canvas_widgets.remove(widget)
        widget.hide()
        widget.deleteLater()
        if not self._canvas_widgets:
            self._placeholder.setVisible(True)

    # ── 属性应用 ──
    def _apply_property(self, widget, prop, value):
        try:
            if prop == "objectName":
                widget.setObjectName(value)
            elif prop == "text" and hasattr(widget, "setText"):
                widget.setText(value)
            elif prop == "title":
                if hasattr(widget, "setGaugeTitle"):
                    widget.setGaugeTitle(value)
                elif hasattr(widget, "setTitle"):
                    widget.setTitle(value)
            elif prop == "unit" and hasattr(widget, "setUnit"):
                widget.setUnit(value)
            elif prop == "placeholderText" and hasattr(widget, "setPlaceholderText"):
                widget.setPlaceholderText(value)
            elif prop == "role":
                widget.setProperty("role", value)
                widget.style().unpolish(widget)
                widget.style().polish(widget)
            elif prop == "tag":
                widget.setProperty("_tag", value)
            elif prop == "anchor_left":
                widget.setProperty("_anchor_left", value)
            elif prop == "anchor_right":
                widget.setProperty("_anchor_right", value)
            elif prop == "anchor_top":
                widget.setProperty("_anchor_top", value)
            elif prop == "anchor_bottom":
                widget.setProperty("_anchor_bottom", value)
            elif prop == "value":
                if isinstance(widget, (QSpinBox, QProgressBar, QDial)):
                    widget.setValue(int(float(value)))
                elif isinstance(widget, (QDoubleSpinBox, QSlider)):
                    widget.setValue(float(value))
                elif isinstance(widget, QLCDNumber):
                    widget.display(int(float(value)))
            elif prop == "x":
                widget.move(max(0, int(value)), widget.y())
            elif prop == "y":
                widget.move(widget.x(), max(0, int(value)))
            elif prop == "width":
                widget.resize(max(MIN_W, int(value)), widget.height())
            elif prop == "height":
                widget.resize(widget.width(), max(MIN_H, int(value)))
            elif prop == "hSizePolicy":
                sp = widget.sizePolicy()
                sp.setHorizontalPolicy(
                    SIZE_POLICY_MAP.get(value, QSizePolicy.Preferred)
                )
                widget.setSizePolicy(sp)
            elif prop == "vSizePolicy":
                sp = widget.sizePolicy()
                sp.setVerticalPolicy(
                    SIZE_POLICY_MAP.get(value, QSizePolicy.Preferred)
                )
                widget.setSizePolicy(sp)
            elif prop == "minWidth":
                widget.setMinimumWidth(max(0, int(value)))
            elif prop == "minHeight":
                widget.setMinimumHeight(max(0, int(value)))
            elif prop == "maxWidth":
                widget.setMaximumWidth(max(0, int(value)))
            elif prop == "maxHeight":
                widget.setMaximumHeight(max(0, int(value)))
            elif prop in (
                "marginLeft", "marginTop", "marginRight", "marginBottom"
            ) and hasattr(widget, "_content_layout"):
                m = widget._content_layout.contentsMargins()
                vals = {
                    "marginLeft": m.left(),
                    "marginTop": m.top(),
                    "marginRight": m.right(),
                    "marginBottom": m.bottom(),
                }
                vals[prop] = max(0, int(value))
                widget._content_layout.setContentsMargins(
                    vals["marginLeft"], vals["marginTop"],
                    vals["marginRight"], vals["marginBottom"],
                )
                widget.update()
            elif prop == "spacing" and hasattr(widget, "_content_layout"):
                widget._content_layout.setSpacing(max(0, int(value)))
                widget.update()
            elif prop == "styleSheet":
                widget.setStyleSheet(value)
        except (ValueError, TypeError):
            pass
        self.widget_modified.emit()

    # ── JSON 安全序列化 ──
    @staticmethod
    def _to_json_safe(val, default=""):
        if val is None:
            return default
        if isinstance(val, (str, int, float, bool)):
            return val
        try:
            return str(val)
        except Exception:
            return default

    def _collect_widget_info(self, w):
        sp = w.sizePolicy()
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
        text_attr = None
        try:
            if hasattr(w, "text") and not isinstance(w, QGroupBox):
                t = w.text()
                text_attr = t if isinstance(t, str) else str(t) if t is not None else None
        except Exception:
            text_attr = None
        title_attr = None
        try:
            if hasattr(w, "title") and isinstance(w, QGroupBox):
                t = w.title()
                title_attr = t if isinstance(t, str) else str(t) if t is not None else None
        except Exception:
            title_attr = None
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
        if text_attr is not None:
            info["text"] = text_attr
        if title_attr is not None:
            info["title"] = title_attr
        if placeholder_attr is not None:
            info["placeholderText"] = placeholder_attr
        if value_attr is not None:
            info["value"] = value_attr
        src = w.property("_custom_source")
        if src:
            info["_custom_source"] = self._to_json_safe(src)
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

    # ── 项目保存/加载 ──
    def save_project(self, path):
        import traceback as _tb
        try:
            self._save_current_page()
            pages_data = []
            for pi, p in enumerate(self._pages):
                pw_list = []
                for wi, w in enumerate(list(p["widgets"])):
                    try:
                        pw_list.append(self._collect_widget_info(w))
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
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        self.clear_canvas()
        self.history.undo_stack.clear()
        self.history.redo_stack.clear()
        for p in self._pages:
            for w in p.get("widgets", []):
                w.hide()
                w.deleteLater()
        self._pages = [{"name": "页面1", "widgets": []}]
        self._current_page = 0
        self._canvas_widgets = self._pages[0]["widgets"]
        if isinstance(raw, list):
            self._signal_connections = []
            self._load_page_widgets(raw, 0)
        else:
            self._signal_connections = raw.get("signal_connections", [])
            self._callback_code = raw.get("callback_code", {})
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
                    if not w.property("_designer_hidden"):
                        w.show()
            else:
                self._load_page_widgets(raw.get("widgets", []), 0)
        self._deselect()
        self.widget_modified.emit()

    def _load_page_widgets(self, widget_data, page_idx):
        for info in widget_data:
            dn = info.get("display_name")
            if not dn:
                continue
            entry_map = get_display_to_entry()
            if dn not in entry_map:
                print(f"[Load] 跳过未知控件: {dn}")
                continue
            pos = QPoint(info.get("x", 0), info.get("y", 0))
            w = self._create_widget_internal(dn, pos)
            if not w:
                continue
            w.setGeometry(
                info.get("x", 0), info.get("y", 0),
                info.get("w", 100), info.get("h", 30),
            )
            if "objectName" in info:
                w.setObjectName(info["objectName"])
            if "role" in info:
                w.setProperty("role", info["role"])
                w.style().unpolish(w)
                w.style().polish(w)
            if "styleSheet" in info and info["styleSheet"]:
                w.setStyleSheet(info["styleSheet"])
            if "text" in info and hasattr(w, "setText"):
                w.setText(info["text"])
            if "title" in info and hasattr(w, "setTitle"):
                w.setTitle(info["title"])
            if "placeholderText" in info and hasattr(w, "setPlaceholderText"):
                w.setPlaceholderText(info["placeholderText"])
            if "value" in info and hasattr(w, "setValue"):
                try:
                    w.setValue(info["value"])
                except Exception:
                    pass
            if "tag" in info and info["tag"]:
                w.setProperty("_tag", info["tag"])
            if "anchor_left" in info:
                w.setProperty("_anchor_left", info["anchor_left"])
            if "anchor_right" in info:
                w.setProperty("_anchor_right", info["anchor_right"])
            if "anchor_top" in info:
                w.setProperty("_anchor_top", info["anchor_top"])
            if "anchor_bottom" in info:
                w.setProperty("_anchor_bottom", info["anchor_bottom"])
            if "hSizePolicy" in info or "vSizePolicy" in info:
                sp = w.sizePolicy()
                sp.setHorizontalPolicy(
                    SIZE_POLICY_MAP.get(
                        info.get("hSizePolicy", "Preferred"),
                        QSizePolicy.Preferred,
                    )
                )
                sp.setVerticalPolicy(
                    SIZE_POLICY_MAP.get(
                        info.get("vSizePolicy", "Preferred"),
                        QSizePolicy.Preferred,
                    )
                )
                w.setSizePolicy(sp)
            if "minWidth" in info:
                w.setMinimumWidth(info["minWidth"])
            if "minHeight" in info:
                w.setMinimumHeight(info["minHeight"])
            if "maxWidth" in info:
                w.setMaximumWidth(info["maxWidth"])
            if "maxHeight" in info:
                w.setMaximumHeight(info["maxHeight"])
            if info.get("locked"):
                w.setProperty("_locked", True)
            if info.get("hidden"):
                w.setProperty("_designer_hidden", True)
                w.hide()
            if info.get("_custom_source"):
                w.setProperty("_custom_source", info["_custom_source"])

    # ── 查找/状态/选择 ──
    def _find_target_widget(self, obj):
        w = obj
        while w is not None and w is not self:
            if getattr(w, '_is_handle', False):
                return None
            p = w.parent()
            if p and hasattr(p, '_content_layout'):
                return w
            if p is self:
                return None if isinstance(w, _Placeholder) else w
            w = p
        return None

    def _find_canvas_top(self, obj):
        return self._find_target_widget(obj)

    def _update_status_bar(self, msg=None):
        win = self.window()
        if hasattr(win, "statusBar"):
            undo_hint = " | Ctrl+Z 可撤销" if self.history.can_undo() else ""
            grid_hint = (
                " | 📐 网格:ON" if self._grid_enabled else " | 📐 网格:OFF"
            )
            win.statusBar().showMessage(
                (msg or "就绪 | G键切换网格 | 右键→信号/槽")
                + grid_hint + undo_hint
            )

    def _select(self, w, additive=False):
        if additive and w in self._multi_selection:
            self._multi_selection.remove(w)
            self._selected = (
                self._multi_selection[-1] if self._multi_selection else None
            )
        elif additive:
            self._multi_selection.append(w)
            self._selected = w
        else:
            if self._selected is w and not self._multi_selection:
                return
            self._deselect()
            self._selected = w
            self._multi_selection = [w]
        self._update_handles()
        self.selection_changed.emit(self._selected)
        self.update()
        if self._selected:
            g = self._selected.geometry()
            lock_icon = " 🔒" if self._selected.property("_locked") else ""
            tag = self._selected.property("_tag") or ""
            tag_hint = f" | 🏷️{tag}" if tag else ""
            multi_hint = (
                f" | 多选:{len(self._multi_selection)}"
                if len(self._multi_selection) > 1
                else ""
            )
            self._update_status_bar(
                f"选中: {self._selected.objectName()}{lock_icon}{tag_hint}"
                f" | ({g.x()},{g.y()}) | {g.width()}×{g.height()}{multi_hint}"
            )
        else:
            self._update_status_bar()

    def _deselect(self):
        if not self._selected and not self._multi_selection:
            return
        self._selected = None
        self._multi_selection = []
        for h in self._handles.values():
            h.setVisible(False)
        self.selection_changed.emit(None)
        self.update()
        self._update_status_bar()

    def _update_handles(self):
        w = self._selected
        if not w:
            for h in self._handles.values():
                h.setVisible(False)
            return
        parent = w.parent()
        in_container = parent and hasattr(parent, "_content_layout")
        if in_container or w.property("_locked"):
            for h in self._handles.values():
                h.setVisible(False)
            return
        g = w.geometry()
        cx, cy = g.x() + g.width() // 2, g.y() + g.height() // 2
        pm = {
            "tl": (g.left(), g.top()),
            "tc": (cx, g.top()),
            "tr": (g.right(), g.top()),
            "ml": (g.left(), cy),
            "mr": (g.right(), cy),
            "bl": (g.left(), g.bottom()),
            "bc": (cx, g.bottom()),
            "br": (g.right(), g.bottom()),
        }
        for n, (hx, hy) in pm.items():
            self._handles[n].move(hx - HANDLE_HALF, hy - HANDLE_HALF)
            self._handles[n].setVisible(True)
            self._handles[n].raise_()

    # ── 绘制 ──
    def paintEvent(self, e):
        super().paintEvent(e)
        if self._preview_mode:
            return
        p = QPainter(self)
        p.scale(self._zoom_factor, self._zoom_factor)
        if self._grid_enabled:
            end_x = int(self.width() / self._zoom_factor) + GRID_SIZE
            end_y = int(self.height() / self._zoom_factor) + GRID_SIZE
            p.setPen(QPen(QColor("#e8e8e8"), 1, Qt.SolidLine))
            for x in range(0, end_x, GRID_SIZE):
                p.drawLine(x, 0, x, end_y)
            for y in range(0, end_y, GRID_SIZE):
                p.drawLine(0, y, end_x, y)
            p.setPen(QPen(QColor("#d0d0d0"), 1, Qt.SolidLine))
            big = GRID_SIZE * 5
            for x in range(0, end_x, big):
                p.drawLine(x, 0, x, end_y)
            for y in range(0, end_y, big):
                p.drawLine(0, y, end_x, y)
        for w in self._multi_selection:
            if w is self._selected:
                continue
            p.setPen(QPen(QColor("#4A90D9"), 1, Qt.DashLine))
            p.drawRect(w.geometry().adjusted(-1, -1, 1, 1))
        if self._selected:
            p.setPen(QPen(QColor("#4A90D9"), 2, Qt.DashLine))
            p.drawRect(self._selected.geometry().adjusted(-1, -1, 1, 1))
        if self._snap_guides:
            p.setPen(QPen(QColor("#E74C3C"), 1, Qt.SolidLine))
            for axis, pos in self._snap_guides:
                if axis == 'x':
                    p.drawLine(pos, 0, pos, self.height())
                else:
                    p.drawLine(0, pos, self.width(), pos)
        if self._insert_indicator:
            container, y = self._insert_indicator
            cr = container.geometry()
            p.setPen(QPen(QColor("#4A90D9"), 3, Qt.SolidLine))
            p.drawLine(cr.left() + 4, y, cr.right() - 4, y)
        p.end()

    # ── 事件过滤 ──
    def eventFilter(self, obj, event):
        if self._preview_mode:
            if (
                event.type() == QEvent.ShortcutOverride
                and event.key() == Qt.Key_Escape
            ):
                return False
            return super().eventFilter(obj, event)
        et = event.type()
        if et == QEvent.Wheel and event.modifiers() & Qt.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self._zoom_factor = min(2.0, self._zoom_factor + 0.1)
            else:
                self._zoom_factor = max(0.5, self._zoom_factor - 0.1)
            self._zoom_factor = round(self._zoom_factor, 1)
            self._update_handles()
            self.update()
            win = self.window()
            if hasattr(win, "statusBar"):
                win.statusBar().showMessage(
                    f"🔍 缩放: {int(self._zoom_factor*100)}%  |  Ctrl+滚轮调节"
                )
            return True
        if et == QEvent.ContextMenu:
            target = self._find_target_widget(obj)
            if target:
                self._select(target)
                global_pos = event.globalPos()
                QTimer.singleShot(
                    0,
                    lambda gp=global_pos: self._show_context_menu(gp),
                )
                return True
            return super().eventFilter(obj, event)
        is_h = getattr(obj, "_is_handle", False)
        if is_h:
            if (
                et == QEvent.MouseButtonPress
                and event.button() == Qt.LeftButton
                and self._selected
            ):
                self._resize_active = True
                self._active_handle = obj._handle_pos
                self._drag_start_mouse = self.mapFromGlobal(
                    obj.mapToGlobal(event.position().toPoint())
                )
                self._drag_start_geom = QRect(self._selected.geometry())
                return True
            if et == QEvent.MouseMove and self._resize_active:
                cur = self.mapFromGlobal(
                    obj.mapToGlobal(event.position().toPoint())
                )
                g = QRect(self._drag_start_geom)
                dx = cur.x() - self._drag_start_mouse.x()
                dy = cur.y() - self._drag_start_mouse.y()
                h = self._active_handle
                if "r" in h:
                    g.setRight(max(g.left() + MIN_W, g.right() + dx))
                if "b" in h:
                    g.setBottom(max(g.top() + MIN_H, g.bottom() + dy))
                if "l" in h:
                    g.setLeft(min(g.right() - MIN_W, g.left() + dx))
                if "t" in h:
                    g.setTop(min(g.bottom() - MIN_H, g.top() + dy))
                if self._grid_enabled:
                    g.setX(self._snap_to_grid(g.x()))
                    g.setY(self._snap_to_grid(g.y()))
                    g.setWidth(
                        max(MIN_W, self._snap_to_grid(g.width()))
                    )
                    g.setHeight(
                        max(MIN_H, self._snap_to_grid(g.height()))
                    )
                self._selected.setGeometry(g)
                self._update_handles()
                self.update()
                self._update_status_bar(
                    f"缩放: {self._selected.objectName()} | {g.width()}×{g.height()}"
                )
                return True
            if et == QEvent.MouseButtonRelease and self._resize_active:
                new_geo = QRect(self._selected.geometry())
                if new_geo != self._drag_start_geom:
                    self.history.push(
                        ResizeWidgetCmd(
                            self,
                            self._selected,
                            QRect(self._drag_start_geom),
                            new_geo,
                        )
                    )
                    self.widget_modified.emit()
                self._resize_active = False
                self._active_handle = None
                g = self._selected.geometry()
                self._update_status_bar(
                    f"选中: {self._selected.objectName()} | "
                    f"({g.x()},{g.y()}) | {g.width()}×{g.height()}"
                )
                return True
            return super().eventFilter(obj, event)
        if et == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
            target = self._find_target_widget(obj)
            if target:
                ctrl_pressed = bool(event.modifiers() & Qt.ControlModifier)
                self._select(target, additive=ctrl_pressed)
                parent = target.parent()
                in_container = parent and hasattr(parent, "_content_layout")
                if not in_container and not target.property("_locked"):
                    self._move_active = True
                    self._drag_start_mouse = self.mapFromGlobal(
                        obj.mapToGlobal(event.position().toPoint())
                    )
                    self._drag_start_geom = QRect(target.geometry())
                    self._drag_start_geoms = {}
                    for mw in self._multi_selection:
                        p = mw.parent()
                        if (
                            not (p and hasattr(p, "_content_layout"))
                            and not mw.property("_locked")
                        ):
                            self._drag_start_geoms[id(mw)] = QRect(
                                mw.geometry()
                            )
                return True
        if (
            et == QEvent.MouseMove
            and self._move_active
            and event.buttons() & Qt.LeftButton
            and self._selected
        ):
            cur = self.mapFromGlobal(
                obj.mapToGlobal(event.position().toPoint())
            )
            delta = cur - self._drag_start_mouse
            raw_x = self._drag_start_geom.x() + delta.x()
            raw_y = self._drag_start_geom.y() + delta.y()
            test_rect = QRect(
                raw_x, raw_y,
                self._selected.width(), self._selected.height(),
            )
            guides, snap_x, snap_y, min_dx, min_dy = self._calc_snap_guides(
                test_rect, self._selected
            )
            nx = (
                snap_x
                if (min_dx <= SNAP_THRESHOLD and snap_x is not None)
                else raw_x
            )
            ny = (
                snap_y
                if (min_dy <= SNAP_THRESHOLD and snap_y is not None)
                else raw_y
            )
            if min_dx <= SNAP_THRESHOLD and snap_x is not None:
                diffs = [
                    abs(raw_x - snap_x),
                    abs(raw_x + self._selected.width() // 2 - snap_x),
                    abs(raw_x + self._selected.width() - snap_x),
                ]
                best = diffs.index(min(diffs))
                if best == 0:
                    nx = snap_x
                elif best == 1:
                    nx = snap_x - self._selected.width() // 2
                else:
                    nx = snap_x - self._selected.width()
            if min_dy <= SNAP_THRESHOLD and snap_y is not None:
                diffs = [
                    abs(raw_y - snap_y),
                    abs(raw_y + self._selected.height() // 2 - snap_y),
                    abs(raw_y + self._selected.height() - snap_y),
                ]
                best = diffs.index(min(diffs))
                if best == 0:
                    ny = snap_y
                elif best == 1:
                    ny = snap_y - self._selected.height() // 2
                else:
                    ny = snap_y - self._selected.height()
            if min_dx > SNAP_THRESHOLD and self._grid_enabled:
                nx = self._snap_to_grid(nx)
            if min_dy > SNAP_THRESHOLD and self._grid_enabled:
                ny = self._snap_to_grid(ny)
            nx = max(0, min(nx, self.width() - self._selected.width()))
            ny = max(0, min(ny, self.height() - self._selected.height()))
            main_dx = nx - self._drag_start_geom.x()
            main_dy = ny - self._drag_start_geom.y()
            self._selected.move(nx, ny)
            if (
                hasattr(self, '_drag_start_geoms')
                and len(self._drag_start_geoms) > 1
            ):
                for mw in self._multi_selection:
                    if mw is self._selected:
                        continue
                    p = mw.parent()
                    if p and hasattr(p, "_content_layout"):
                        continue
                    if mw.property("_locked"):
                        continue
                    sg = self._drag_start_geoms.get(id(mw))
                    if sg is None:
                        continue
                    new_mx = max(
                        0,
                        min(
                            sg.x() + main_dx,
                            self.width() - mw.width(),
                        ),
                    )
                    new_my = max(
                        0,
                        min(
                            sg.y() + main_dy,
                            self.height() - mw.height(),
                        ),
                    )
                    mw.move(new_mx, new_my)
            self._snap_guides = guides
            self._update_handles()
            self.update()
            count = len(self._multi_selection)
            hint = (
                f"移动: {self._selected.objectName()} ({count}个控件) | ({nx},{ny})"
                if count > 1
                else f"移动: {self._selected.objectName()} | ({nx},{ny})"
            )
            self.selection_changed.emit(self._selected)
            self._update_status_bar(hint)
            return True
        if et == QEvent.MouseButtonRelease and self._move_active:
            self._snap_guides = []
            if (
                hasattr(self, '_drag_start_geoms')
                and len(self._drag_start_geoms) > 1
            ):
                moved = []
                old_geos = []
                new_geos = []
                for mw in self._multi_selection:
                    p = mw.parent()
                    if p and hasattr(p, "_content_layout"):
                        continue
                    if mw.property("_locked"):
                        continue
                    sg = self._drag_start_geoms.get(id(mw))
                    if sg is None:
                        continue
                    new_g = QRect(mw.geometry())
                    if new_g.topLeft() != sg.topLeft():
                        moved.append(mw)
                        old_geos.append(sg)
                        new_geos.append(new_g)
                if moved:
                    self.history.push(
                        BatchAlignCmd(self, moved, old_geos, new_geos)
                    )
                    self.widget_modified.emit()
            else:
                new_pos = self._selected.pos()
                old_pos = self._drag_start_geom.topLeft()
                if new_pos != old_pos:
                    self.history.push(
                        MoveWidgetCmd(
                            self, self._selected, old_pos, new_pos
                        )
                    )
                    self.widget_modified.emit()
            self._move_active = False
            self._drag_start_geoms = {}
            g = (
                self._selected.geometry()
                if self._selected
                else QRect()
            )
            self._update_status_bar(
                f"选中: {self._selected.objectName() if self._selected else ''} | "
                f"({g.x()},{g.y()}) | {g.width()}×{g.height()}"
                if self._selected
                else ""
            )
            return True
        return super().eventFilter(obj, event)

    def mousePressEvent(self, e):
        c = self.childAt(e.position().toPoint())
        if not c or isinstance(c, _Placeholder):
            self._deselect()
        super().mousePressEvent(e)

    # ── 右键菜单 ──
    def _show_context_menu(self, global_pos):
        w = self._selected
        if not w:
            return
        menu = QMenu(self)
        parent = w.parent()
        in_container = parent and hasattr(parent, "_content_layout")
        action_map = {}
        act_signals = menu.addAction("🔗 信号/槽编辑器...")
        action_map[act_signals] = "signals"
        menu.addSeparator()
        if in_container:
            ly = parent._content_layout
            idx = ly.indexOf(w)
            count = ly.count()
            act_up = menu.addAction("⬆️ 上移")
            act_up.setEnabled(idx > 0)
            action_map[act_up] = "up"
            act_down = menu.addAction("⬇️ 下移")
            act_down.setEnabled(idx < count - 1)
            action_map[act_down] = "down"
            menu.addSeparator()
            act_extract = menu.addAction("📤 移出容器")
            action_map[act_extract] = "extract"
            menu.addSeparator()
        locked = bool(w.property("_locked"))
        act_lock = menu.addAction(f"{'🔓 解锁' if locked else '🔒 锁定'}")
        action_map[act_lock] = "lock"
        hidden = bool(w.property("_designer_hidden"))
        act_hide = menu.addAction(
            f"{'👁️ 显示' if hidden else '👁️‍🗨️ 隐藏'}"
        )
        action_map[act_hide] = "hide"
        menu.addSeparator()
        act_delete = menu.addAction("🗑️ 删除控件")
        action_map[act_delete] = "delete"
        menu.addSeparator()
        act_copy_style = menu.addAction("🎨 复制样式")
        action_map[act_copy_style] = "copy_style"
        act_paste_style = menu.addAction("🖌️ 粘贴样式")
        act_paste_style.setEnabled(self._style_clipboard is not None)
        action_map[act_paste_style] = "paste_style"
        menu.addSeparator()
        act_copy = menu.addAction("📋 复制 objectName")
        action_map[act_copy] = "copy"
        menu.addSeparator()
        callback_menu = menu.addMenu("✏️ 编辑回调函数")
        widget_name = w.objectName()
        related_connections = [
            c for c in self._signal_connections
            if c["source"] == widget_name
        ]
        if related_connections:
            for conn in related_connections:
                slot_name = conn["slot"]
                has_code = (
                    slot_name in self._callback_code
                    and self._callback_code[slot_name].strip()
                )
                label = f"  {slot_name}" + (" ✅" if has_code else "")
                act_cb = callback_menu.addAction(label)
                act_cb.setData(slot_name)
                action_map[act_cb] = ("edit_callback", slot_name)
        else:
            act_no_conn = callback_menu.addAction(
                " (暂无连接，请先添加信号/槽...)"
            )
            act_no_conn.setEnabled(False)
            action_map[act_no_conn] = "noop"
        chosen = menu.exec(global_pos)
        if chosen is None or chosen not in action_map:
            return
        at = action_map[chosen]
        if isinstance(at, tuple) and at[0] == "edit_callback":
            slot_name = at[1]
            existing_code = self._callback_code.get(slot_name, "")
            dlg = CallbackEditorDialog(
                self, slot_name, existing_code, self.window()
            )
            if dlg.exec() == QDialog.Accepted:
                self._callback_code[slot_name] = dlg.get_code()
                self.widget_modified.emit()
        elif at == "signals":
            dlg = SignalSlotDialog(self, self.window())
            dlg.exec()
        elif at == "up":
            ly = parent._content_layout
            idx = ly.indexOf(w)
            self.history.push(ReorderWidgetCmd(parent, w, idx, idx - 1))
            self.widget_modified.emit()
        elif at == "down":
            ly = parent._content_layout
            idx = ly.indexOf(w)
            self.history.push(ReorderWidgetCmd(parent, w, idx, idx + 1))
            self.widget_modified.emit()
        elif at == "extract":
            ly = parent._content_layout
            idx = ly.indexOf(w)
            self.history.push(ExtractWidgetCmd(self, w, parent, idx))
            self._deselect()
        elif at == "lock":
            self._toggle_lock()
        elif at == "hide":
            self._toggle_hide()
        elif at == "delete":
            self._delete_selected()
        elif at == "copy_style":
            self._copy_style()
        elif at == "paste_style":
            self._paste_style()
        elif at == "copy":
            QApplication.clipboard().setText(w.objectName())

    def _delete_selected(self):
        if not self._selected:
            return
        self.history.push(DeleteWidgetCmd(self, self._selected))
        self.widget_modified.emit()

    def clear_canvas(self):
        self._deselect()
        for p in self._pages:
            for w in list(p["widgets"]):
                w.hide()
                w.deleteLater()
        self._pages = [{"name": "页面1", "widgets": []}]
        self._current_page = 0
        self._canvas_widgets = self._pages[0]["widgets"]
        self._signal_connections.clear()
        self._callback_code.clear()
        self._placeholder.setVisible(True)
        self.widget_modified.emit()
