import sys, os
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QComboBox, QGroupBox, QFrame,
    QCheckBox, QRadioButton, QSpinBox, QDoubleSpinBox, QSlider,
    QProgressBar, QTextEdit, QTextBrowser, QDateEdit, QTimeEdit,
    QTabWidget, QScrollArea, QToolButton, QDialogButtonBox,
    QCalendarWidget, QDial, QLCDNumber, QCommandLinkButton,
    QStackedWidget, QListWidget, QTreeWidget, QTableWidget, QSplitter,
    QSizePolicy, QSpacerItem,
)


class GeneratedWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Generated Application")
        self.resize(800, 600)

        qss_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'style.qss')
        if os.path.exists(qss_path):
            with open(qss_path, 'r', encoding='utf-8') as f:
                QApplication.instance().setStyleSheet(f.read())

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.btn = QPushButton("按钮", self.central_widget)
        self.btn.setGeometry(160, 180, 120, 36)


        # 信号/槽连接
        self.btn.clicked.connect(self.on_btn_test_clicked)


    def on_btn_test_clicked(self):
        # TODO: 在此编写 on_btn_test_clicked 的回调逻辑
        print("按钮被点击了！")
        self.btn.setText("已点击")
        pass


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GeneratedWindow()
    window.show()
    sys.exit(app.exec())