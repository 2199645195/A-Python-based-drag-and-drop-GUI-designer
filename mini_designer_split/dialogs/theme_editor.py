"""mini_designer_split/dialogs/theme_editor.py — 主题编辑器对话框"""

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPlainTextEdit,
    QPushButton, QFileDialog, QMessageBox,
)
from PySide6.QtGui import QFont, QFontMetrics, QKeySequence, QShortcut


class ThemeEditorDialog(QDialog):
    """编辑 QSS 样式表，修改后自动实时预览到设计器画布"""
    qss_changed = Signal(str)

    def __init__(self, current_qss, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🎨 主题编辑器")
        self.resize(700, 500)
        layout = QVBoxLayout(self)

        hint = QLabel("编辑 QSS 样式表，修改后自动实时预览到设计器画布")
        hint.setStyleSheet("color:#666; font-size:12px; padding:4px;")
        layout.addWidget(hint)

        self.editor = QPlainTextEdit()
        self.editor.setPlainText(current_qss)
        self.editor.setStyleSheet(
            "QPlainTextEdit { font-family: 'Consolas', monospace; font-size: 12px; }"
        )
        layout.addWidget(self.editor)

        btn_layout = QHBoxLayout()
        for label, slot in [
            ("🔄 重置为默认", self._reset_default),
            ("📂 从文件加载", self._load_from_file),
            ("💾 保存为文件", self._save_to_file),
            ("✅ 应用并关闭", self.accept),
            ("❌ 取消", self.reject),
        ]:
            btn = QPushButton(label)
            btn.clicked.connect(slot)
            btn_layout.addWidget(btn)
        layout.addLayout(btn_layout)

        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(
            lambda: self.qss_changed.emit(self.editor.toPlainText())
        )
        self.editor.textChanged.connect(lambda: self._debounce_timer.start(300))

    def _reset_default(self):
        from ..config import DEFAULT_QSS
        self.editor.setPlainText(DEFAULT_QSS)

    def _load_from_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "加载QSS文件", "", "QSS Files (*.qss);;All Files (*)"
        )
        if path:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self.editor.setPlainText(f.read())
            except Exception as e:
                QMessageBox.warning(self, "加载失败", str(e))

    def _save_to_file(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "保存QSS文件", "custom_theme.qss", "QSS Files (*.qss)"
        )
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(self.editor.toPlainText())
                QMessageBox.information(self, "保存成功", f"已保存至:\n{path}")
            except Exception as e:
                QMessageBox.warning(self, "保存失败", str(e))

    def get_qss(self):
        return self.editor.toPlainText()
