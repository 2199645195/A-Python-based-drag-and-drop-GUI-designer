"""mini_designer_split/panels/toolbox.py — 控件工具箱面板"""

from PySide6.QtCore import Qt, QEvent, QMimeData
from PySide6.QtGui import QDrag, QColor, QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLineEdit, QListWidget, QListWidgetItem,
    QAbstractItemView,
)

from ..config import MIME_TYPE, get_all_categories


class WidgetToolbox(QWidget):
    """左侧工具箱 — 显示所有可拖拽的控件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍 搜索控件...")
        self.search.setClearButtonEnabled(True)
        self.search.setStyleSheet(
            "QLineEdit{padding:4px 8px;border:1px solid #ccc;"
            "border-radius:4px;margin:2px 4px;font-size:12px;}"
        )
        self.search.textChanged.connect(self._filter)
        layout.addWidget(self.search)

        self.list_widget = QListWidget()
        self.list_widget.setDragEnabled(True)
        self.list_widget.setSelectionMode(QAbstractItemView.NoSelection)
        self.list_widget.setStyleSheet(
            "QListWidget{background:#e8e8e8;border:1px solid #ccc;font-size:12px;}"
            " QListWidget::item{padding:5px 8px;}"
            " QListWidget::item:hover{background:#d0d8e8;}"
        )
        self.list_widget.setMaximumWidth(200)
        self.list_widget.setMinimumWidth(150)
        layout.addWidget(self.list_widget)

        self._all_items = []  # (display_text, is_header, category_name, widget_name)
        self.list_widget.viewport().installEventFilter(self)
        self.populate()

    def setMaximumWidth(self, w):
        self.list_widget.setMaximumWidth(w)

    def setMinimumWidth(self, w):
        self.list_widget.setMinimumWidth(w)

    def eventFilter(self, obj, event):
        if obj is self.list_widget.viewport() and event.type() == QEvent.MouseMove:
            item = self.list_widget.itemAt(event.position().toPoint())
            if item:
                wt = item.data(Qt.UserRole)
                if wt:
                    drag = QDrag(self)
                    mime = QMimeData()
                    mime.setData(MIME_TYPE, wt.encode())
                    drag.setMimeData(mime)
                    drag.exec(Qt.CopyAction)
        return super().eventFilter(obj, event)

    def populate(self):
        self._all_items = []
        for cat, items in get_all_categories():
            self._all_items.append(
                (f"── {cat} ──", True, cat, None)
            )
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
                continue
            if ft:
                if (
                    ft in text.lower()
                    or ft in (name or "").lower()
                    or ft in cat.lower()
                ):
                    if visible_cat != cat:
                        header_text = f"── {cat} ──"
                        h = QListWidgetItem(header_text)
                        h.setFlags(Qt.NoItemFlags)
                        h.setForeground(QColor("#888"))
                        f = QFont()
                        f.setBold(True)
                        f.setPointSize(10)
                        h.setFont(f)
                        self.list_widget.addItem(h)
                        visible_cat = cat
                    item = QListWidgetItem(text)
                    item.setData(Qt.UserRole, name)
                    self.list_widget.addItem(item)
            else:
                if visible_cat != cat:
                    header_text = f"── {cat} ──"
                    h = QListWidgetItem(header_text)
                    h.setFlags(Qt.NoItemFlags)
                    h.setForeground(QColor("#888"))
                    f = QFont()
                    f.setBold(True)
                    f.setPointSize(10)
                    h.setFont(f)
                    self.list_widget.addItem(h)
                    visible_cat = cat
                item = QListWidgetItem(text)
                item.setData(Qt.UserRole, name)
                self.list_widget.addItem(item)

    def _filter(self, text):
        self._rebuild_list(text)

    def mouseMoveEvent(self, event):
        item = self.list_widget.itemAt(
            self.list_widget.viewport().mapFrom(self, event.position().toPoint())
        )
        if not item:
            return
        wt = item.data(Qt.UserRole)
        if not wt:
            return
        drag = QDrag(self)
        mime = QMimeData()
        mime.setData(MIME_TYPE, wt.encode())
        drag.setMimeData(mime)
        drag.exec(Qt.CopyAction)
