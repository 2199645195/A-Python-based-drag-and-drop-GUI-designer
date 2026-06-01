
from camera_widget import CameraWidget
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


class DataBinder:
    """
    数据绑定管理器 - 由设计器自动生成
    外部通信线程通过 update_tag(tag, value) 统一刷新UI
    """
    def __init__(self, ui):
        self.ui = ui
        self._data = {}

    def update_tag(self, tag: str, value):
        self._data[tag] = value
        if tag == 'C:\\Users\\Ding\\Desktop\\微信图片_20260525193509_233_76.jpg': self.ui.c_users_ding_desktop_20260525193509_233_76_jpg.setValue(float(value))  # 通用: 自定义控件

    def get_tag(self, tag: str):
        return self._data.get(tag)

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

        # ── Camera: c_users_ding_desktop_20260525193509_233_76_jpg ──
        self.c_users_ding_desktop_20260525193509_233_76_jpg = CameraWidget(self.central_widget)
        self.c_users_ding_desktop_20260525193509_233_76_jpg.setGeometry(180, 130, 260, 160)
        self.c_users_ding_desktop_20260525193509_233_76_jpg.setObjectName("c_users_ding_desktop_20260525193509_233_76_jpg")
        self.c_users_ding_desktop_20260525193509_233_76_jpg.load_image(r"C:\\Users\\Ding\\Desktop\\微信图片_20260525193509_233_76.jpg")


        # 初始化数据绑定管理器
        self.data_binder = DataBinder(self)
        # TODO: 在此处启动您的通信线程，调用 self.data_binder.update_tag(tag, value) 刷新UI

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GeneratedWindow()
    window.show()
    sys.exit(app.exec())