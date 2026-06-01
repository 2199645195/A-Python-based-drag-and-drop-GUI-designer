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

        self.label = QLabel("温度：--", self.central_widget)
        self.label.setGeometry(60, 100, 100, 30)

        self.btn = QPushButton("打开设置", self.central_widget)
        self.btn.setGeometry(30, 40, 120, 36)


    def retranslateUi(self, MainWindow):
        pass
