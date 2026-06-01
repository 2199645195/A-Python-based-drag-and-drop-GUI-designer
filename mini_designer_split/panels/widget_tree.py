"""mini_designer_split/panels/widget_tree.py — 控件层级树面板"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTreeWidget, QTreeWidgetItem,
    QAbstractItemView, QMenu,
)

from ..commands import (
    ReorderWidgetCmd, ExtractWidgetCmd,
    _ReparentIntoContainerCmd, _ReparentBetweenContainersCmd,
)


class _DragTree(QTreeWidget):
    """支持拖拽改变父子关系的树控件"""

    def __init__(self, panel, parent=None):
        super().__init__(parent)
        self._panel = panel
        self._highlight_item = None

    def dragMoveEvent(self, event):
        super().dragMoveEvent(event)
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
    item_selected = Signal(object)

    def __init__(self, canvas, parent=None):
        super().__init__(parent)
        self.canvas = canvas
        self.setMinimumWidth(180)
        self.setMaximumWidth(300)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        self.header = QLabel("<b>📁 控件层级</b>")
        self.header.setStyleSheet(
            "padding:4px 8px; font-size:12px;"
            " background:#f0f0f0; border-bottom:1px solid #ddd;"
        )
        layout.addWidget(self.header)

        self.tree = _DragTree(self)
        self.tree.setHeaderHidden(True)
        self.tree.setDragEnabled(True)
        self.tree.setAcceptDrops(True)
        self.tree.setDropIndicatorShown(True)
        self.tree.setDragDropMode(QAbstractItemView.InternalMove)
        self.tree.setDefaultDropAction(Qt.MoveAction)
        self.tree.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tree.setStyleSheet(
            "QTreeWidget{font-size:12px;}"
            " QTreeWidget::item{padding:2px 4px;}"
            " QTreeWidget::item:selected{background:#4A90D9;color:#fff;}"
        )
        layout.addWidget(self.tree)

        self.tree.itemClicked.connect(self._on_item_clicked)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)

    def rebuild(self):
        self.tree.clear()
        for w in self.canvas._canvas_widgets:
            if w.property("_designer_hidden"):
                continue
            item = self._build_item(w)
            self.tree.addTopLevelItem(item)
            if hasattr(w, "_content_layout"):
                self._build_children(item, w._content_layout)

    def _build_item(self, w):
        name = w.objectName()
        display = w.property("_display_name") or ""
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
        snap = {}
        for ri in range(self.tree.topLevelItemCount()):
            ti = self.tree.topLevelItem(ri)
            wid = ti.data(0, Qt.UserRole)
            if wid:
                snap[wid] = (None, ri)
            self._snapshot_children(ti, snap)
        return snap

    def _snapshot_children(self, parent_item, snap):
        for ci in range(parent_item.childCount()):
            child = parent_item.child(ci)
            wid = child.data(0, Qt.UserRole)
            parent_wid = parent_item.data(0, Qt.UserRole)
            if wid:
                snap[wid] = (parent_wid, ci)
            self._snapshot_children(child, snap)

    def _sync_tree_to_canvas(self, old_state):
        new_state = self._snapshot_tree()
        for wid, (new_parent_wid, new_idx) in new_state.items():
            old = old_state.get(wid)
            if old is None:
                continue
            old_parent_wid, old_idx = old
            if old_parent_wid == new_parent_wid and old_idx == new_idx:
                continue
            w = self._find_widget_by_id(wid)
            if not w:
                continue
            old_container = (
                self._find_widget_by_id(old_parent_wid)
                if old_parent_wid else None
            )
            new_container = (
                self._find_widget_by_id(new_parent_wid)
                if new_parent_wid else None
            )
            if old_container is None and new_container is None:
                self._reorder_canvas_widget(w, new_idx)
            elif old_container and new_container is None:
                self.canvas.history.push(
                    ExtractWidgetCmd(
                        self.canvas, w, old_container, old_idx
                    )
                )
            elif old_container is None and new_container:
                self._move_into_container(w, new_container, new_idx)
            elif old_container and new_container:
                self._move_between_containers(
                    w, old_container, new_container, new_idx
                )
        self.canvas.widget_modified.emit()
        self.rebuild()

    def _reorder_canvas_widget(self, w, new_idx):
        if w not in self.canvas._canvas_widgets:
            return
        self.canvas._canvas_widgets.remove(w)
        self.canvas._canvas_widgets.insert(
            min(new_idx, len(self.canvas._canvas_widgets)), w
        )
        w.raise_()

    def _move_into_container(self, w, container, idx):
        if w not in self.canvas._canvas_widgets:
            return
        old_idx = self.canvas._canvas_widgets.index(w)
        self.canvas.history.push(
            _ReparentIntoContainerCmd(
                self.canvas, w, container, old_idx, idx
            )
        )

    def _move_between_containers(self, w, old_container, new_container, new_idx):
        old_idx = (
            old_container._content_layout.indexOf(w)
            if hasattr(old_container, '_content_layout')
            else 0
        )
        self.canvas.history.push(
            _ReparentBetweenContainersCmd(
                self.canvas, w, old_container, new_container,
                old_idx, new_idx,
            )
        )

    def _on_item_clicked(self, item, col):
        wid = item.data(0, Qt.UserRole)
        w = self._find_widget_by_id(wid)
        if w:
            self.canvas._select(w)
            self.item_selected.emit(w)

    def _show_context_menu(self, pos):
        item = self.tree.itemAt(pos)
        if not item:
            return
        wid = item.data(0, Qt.UserRole)
        w = self._find_widget_by_id(wid)
        if not w:
            return
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
        if not chosen:
            return
        if chosen == act_select:
            self.canvas._select(w)
        elif in_container and chosen == act_up:
            ly = parent._content_layout
            idx = ly.indexOf(w)
            if idx > 0:
                self.canvas.history.push(
                    ReorderWidgetCmd(parent, w, idx, idx - 1)
                )
                self.canvas.widget_modified.emit()
        elif in_container and chosen == act_down:
            ly = parent._content_layout
            idx = ly.indexOf(w)
            if idx < ly.count() - 1:
                self.canvas.history.push(
                    ReorderWidgetCmd(parent, w, idx, idx + 1)
                )
                self.canvas.widget_modified.emit()
        elif in_container and chosen == act_extract:
            ly = parent._content_layout
            idx = ly.indexOf(w)
            self.canvas.history.push(
                ExtractWidgetCmd(self.canvas, w, parent, idx)
            )
            self.canvas._deselect()
        elif chosen == act_lock:
            self.canvas._toggle_lock()
        elif chosen == act_hide:
            self.canvas._toggle_hide()
        elif chosen == act_delete:
            self.canvas._delete_selected()
