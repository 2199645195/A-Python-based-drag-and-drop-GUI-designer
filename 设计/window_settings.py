from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QComboBox, QGroupBox, QFrame,
    QCheckBox, QRadioButton, QSpinBox, QDoubleSpinBox, QSlider,
    QProgressBar, QTextEdit, QTextBrowser, QDateEdit, QTimeEdit,
    QTabWidget, QScrollArea, QToolButton, QDialogButtonBox,
    QCalendarWidget, QDial, QLCDNumber, QCommandLinkButton,
    QStackedWidget, QListWidget, QTreeWidget, QTableWidget, QSplitter,
    QSizePolicy,
)


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setWindowTitle('Generated Application')
        MainWindow.resize(800, 600)

        import os
        qss_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'style.qss')
        if os.path.exists(qss_path):
            with open(qss_path, 'r', encoding='utf-8') as f:
                MainWindow.setStyleSheet(f.read())

        self.central_widget = QWidget()
        MainWindow.setCentralWidget(self.central_widget)

        self.label = QLabel("设置温度上限", self.central_widget)
        self.label.setGeometry(60, 60, 100, 30)

        self.line_edit = QLineEdit(self.central_widget)
        self.line_edit.setGeometry(150, 58, 160, 32)
        self.line_edit.setPlaceholderText("请输入...")

        self.btn = QPushButton("确定", self.central_widget)
        self.btn.setGeometry(50, 110, 120, 36)


    def retranslateUi(self, MainWindow):
        pass
