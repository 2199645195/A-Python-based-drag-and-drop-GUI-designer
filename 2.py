
from industrial_widgets import CameraWidget, GaugeWidget, TowerLightWidget
from my_widgets import DigitalClock, IPAddressEdit, LedIndicator, TagChip, ToggleSwitch
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
        if tag == 'panel_title': self.ui.label_1.setText(str(value))
        if tag == 'temp_value': self.ui.lcd_1.display(float(value) if value else 0)
        if tag == 'temp_unit': self.ui.label_2.setText(str(value))
        if tag == 'temp_bar': self.ui.progress_1.setValue(int(float(value)))

    def get_tag(self, tag: str):
        return self._data.get(tag)

class GeneratedWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Generated Application")
        self.resize(800, 400)

        qss_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'style.qss')
        if os.path.exists(qss_path):
            with open(qss_path, 'r', encoding='utf-8') as f:
                QApplication.instance().setStyleSheet(f.read())

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.btn = QPushButton("按钮", self.central_widget)
        self.btn.setGeometry(10, 30, 120, 36)

        self.tool_btn = QToolButton(self.central_widget)
        self.tool_btn.setGeometry(20, 90, 80, 30)
        self.tool_btn.setText("工具")

        self.led_1 = LedIndicator(self.central_widget)
        self.led_1.setGeometry(30, 150, 28, 28)
        self.led_1.setObjectName("led_1")

        self.ip_1 = IPAddressEdit(self.central_widget)
        self.ip_1.setGeometry(209, 330, 220, 50)
        self.ip_1.setObjectName("ip_1")

        self.widget_1 = GaugeWidget(self.central_widget)
        self.widget_1.setGeometry(20, 238, 120, 120)
        self.widget_1.setObjectName("widget_1")
        self.widget_1.setStyleSheet("GaugeWidget { background:#55aaff; color:#55ffff; }")

        self.widget_2 = TagChip(self.central_widget)
        self.widget_2.setGeometry(150, 20, 120, 36)
        self.widget_2.setObjectName("widget_2")

        self.widget_3 = DigitalClock(self.central_widget)
        self.widget_3.setGeometry(300, 17, 230, 60)
        self.widget_3.setObjectName("widget_3")

        self.widget_5 = CameraWidget(self.central_widget)
        self.widget_5.setGeometry(158, 119, 160, 120)
        self.widget_5.setObjectName("widget_5")
        self.widget_5.setStyleSheet("CameraWidget { background:#ff55ff; color:#00007f; }")

        self.frame = QFrame(self.central_widget)
        self.frame.setGeometry(370, 97, 280, 160)
        self.frame.setStyleSheet("QFrame{background:#1e1e1e;border:1px solid #333;border-radius:8px;}")

        self.label = QLabel("📊 实时温度监控", self.central_widget)
        self.label.setGeometry(390, 107, 200, 24)
        self.label.setStyleSheet("color:#aaa;font-size:14px;font-weight:bold;background:transparent;border:none;")

        self.lcd = QLCDNumber(self.central_widget)
        self.lcd.setGeometry(390, 147, 160, 64)
        self.lcd.setProperty("role", "success")
        self.lcd.setStyleSheet("QLCDNumber{background:#0d0d0d;border:1px solid #333;border-radius:4px;color:#00ff88;}")
        self.lcd.display(0)

        self.label_1 = QLabel("°C", self.central_widget)
        self.label_1.setGeometry(550, 157, 60, 32)
        self.label_1.setStyleSheet("color:#00ff88;font-size:24px;font-weight:bold;background:transparent;border:none;")

        self.progress = QProgressBar(self.central_widget)
        self.progress.setGeometry(390, 217, 248, 22)
        self.progress.setProperty("role", "success")
        self.progress.setStyleSheet("QProgressBar{background:#0d0d0d;border:1px solid #333;border-radius:4px;text-align:center;color:#aaa;}QProgressBar::chunk{background:#00ff88;border-radius:3px;}")
        self.progress.setValue(45)

        self.widget_4 = TowerLightWidget(self.central_widget)
        self.widget_4.setGeometry(679, 28, 120, 180)
        self.widget_4.setObjectName("widget_4")

        self.widget_6 = ToggleSwitch(self.central_widget)
        self.widget_6.setGeometry(237, 280, 52, 28)
        self.widget_6.setObjectName("widget_6")

        self.widget_7 = TagChip(self.central_widget)
        self.widget_7.setGeometry(490, 280, 120, 36)
        self.widget_7.setObjectName("widget_7")
        self.widget_7.setStyleSheet("TagChip { background:#55aaff; }")

        self.svg_icon = Svg_icon(self.central_widget)
        self.svg_icon.setGeometry(660, 270, 110, 110)
        self.svg_icon.setObjectName("svg_icon_1")


        # 初始化数据绑定管理器
        self.data_binder = DataBinder(self)
        # TODO: 在此处启动您的通信线程，调用 self.data_binder.update_tag(tag, value) 刷新UI

    # 设计基准尺寸: 800x400
    def resizeEvent(self, event):
        super().resizeEvent(event)
        w = self.central_widget.width()
        h = self.central_widget.height()
        sx = w / 800
        sy = h / 400
        self.frame_1.move(int(370 * sx), int(97 * sy))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GeneratedWindow()
    window.show()
    sys.exit(app.exec())