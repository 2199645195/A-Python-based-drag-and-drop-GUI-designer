"""mini_designer_split/dialogs/signal_slot.py — 信号/槽编辑器"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
    QComboBox, QLineEdit, QPushButton, QMessageBox, QMenu,
)
from PySide6.QtGui import QColor

from ..config import WIDGET_SIGNALS


class SignalSlotDialog(QDialog):
    """设计时信号/槽连接编辑器"""

    def __init__(self, canvas, parent=None):
        super().__init__(parent)
        self.canvas = canvas
        self.setWindowTitle("🔗 信号/槽编辑器")
        self.resize(560, 500)
        layout = QVBoxLayout(self)

        self.conn_list = QListWidget()
        layout.addWidget(self.conn_list)
        self.conn_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.conn_list.customContextMenuRequested.connect(self._show_conn_context_menu)

        form = QHBoxLayout()
        self.combo_source = QComboBox()
        self.combo_signal = QComboBox()
        self.edit_slot = QLineEdit()
        self.edit_slot.setPlaceholderText("槽函数名 (如 on_btn_start_clicked)")
        form.addWidget(QLabel("源:"))
        form.addWidget(self.combo_source)
        form.addWidget(QLabel("信号:"))
        form.addWidget(self.combo_signal)
        form.addWidget(QLabel("→"))
        form.addWidget(QLabel("槽:"))
        form.addWidget(self.edit_slot)
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
        from .callback_editor import CallbackEditorDialog
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
            self.conn_list.addItem(
                f"{conn['source']}.{conn['signal']} → {conn['slot']}"
            )

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
