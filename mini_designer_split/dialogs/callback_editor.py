"""mini_designer_split/dialogs/callback_editor.py — 回调函数编辑器"""

from PySide6.QtGui import QFont, QFontMetrics, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton,
)


class CallbackEditorDialog(QDialog):
    """回调函数编辑器 — 右键点击控件→编辑回调→自动集成到代码生成"""

    def __init__(self, canvas, slot_name, existing_code="", parent=None):
        super().__init__(parent)
        self.canvas = canvas
        self.slot_name = slot_name
        self.setWindowTitle(f"✏️ 编辑回调函数: {slot_name}")
        self.resize(700, 500)
        layout = QVBoxLayout(self)

        hint = QLabel(
            f"正在编辑回调函数: <b>{slot_name}</b>"
            "  按 <b>Ctrl+S</b> 保存  <b>ESC</b> 取消"
        )
        hint.setStyleSheet(
            "color:#666; font-size:12px; padding:4px;"
            " background:#f5f5f5; border-radius:4px;"
        )
        layout.addWidget(hint)

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

        help_text = QLabel(
            "💡 提示: 在此编写该回调函数的完整代码。"
            "函数签名中的 <code>self</code> 即为生成的窗口实例，"
            "可通过 <code>self.btn_start</code> 等方式访问其他控件。"
        )
        help_text.setWordWrap(True)
        help_text.setStyleSheet("color:#888; font-size:11px; padding:4px;")
        layout.addWidget(help_text)

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

        QShortcut(QKeySequence("Ctrl+S"), self).activated.connect(self.accept)

    def _default_code(self):
        return (
            f"def {self.slot_name}(self):\n"
            f"    # TODO: 在此编写 {self.slot_name} 的回调逻辑\n"
            f"    pass\n"
        )

    def get_code(self):
        return self.editor.toPlainText()
