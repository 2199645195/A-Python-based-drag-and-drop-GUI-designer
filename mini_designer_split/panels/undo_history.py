"""mini_designer_split/panels/undo_history.py — 撤销历史面板"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QPushButton,
)


class UndoHistoryPanel(QWidget):
    """撤销历史面板 — 显示操作列表，点击回退到任意步骤"""

    def __init__(self, canvas, parent=None):
        super().__init__(parent)
        self.canvas = canvas
        self.setMinimumWidth(180)
        self.setMaximumWidth(400)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.header = QLabel("<b>📜 撤销历史</b>")
        self.header.setStyleSheet(
            "padding:4px 8px; font-size:12px;"
            " background:#f0f0f0; border-bottom:1px solid #ddd;"
        )
        layout.addWidget(self.header)

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(
            "QListWidget{font-size:11px;}"
            " QListWidget::item{padding:3px 6px;}"
        )
        layout.addWidget(self.list_widget)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(4)
        self.btn_undo_step = QPushButton("↩ 回退一步")
        self.btn_redo_step = QPushButton("↪ 前进一步")
        self.btn_clear_history = QPushButton("清空历史")
        for btn in [
            self.btn_undo_step, self.btn_redo_step, self.btn_clear_history
        ]:
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
            desc = getattr(cmd, 'description', '操作') or '操作'
            item = QListWidgetItem(desc)
            item.setData(Qt.UserRole, id(cmd))
            self.list_widget.addItem(item)
        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(self.list_widget.count() - 1)
        self.btn_undo_step.setEnabled(self.canvas.history.can_undo())
        self.btn_redo_step.setEnabled(self.canvas.history.can_redo())

    def _on_item_clicked(self, item):
        target_id = item.data(Qt.UserRole)
        target_idx = None
        for i, cmd in enumerate(self.canvas.history.undo_stack):
            if id(cmd) == target_id:
                target_idx = i
                break
        if target_idx is None:
            return
        current_top = len(self.canvas.history.undo_stack) - 1
        steps = current_top - target_idx
        for _ in range(steps):
            self.canvas.undo()
        self.canvas.widget_modified.emit()

    def _clear_history(self):
        self.canvas.history.undo_stack.clear()
        self.canvas.history.redo_stack.clear()
        self.canvas.widget_modified.emit()
