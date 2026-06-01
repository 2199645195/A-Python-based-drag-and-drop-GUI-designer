import sys
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMainWindow

from window_main import Ui_MainWindow
from window_settings import Ui_MainWindow as Ui_Dialog


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.ui.btn.clicked.connect(self.open_settings)

    def open_settings(self):
        self._settings = QMainWindow()
        self._settings.setWindowFlags(Qt.Dialog)
        self._settings.setWindowModality(Qt.ApplicationModal)
        Ui_Dialog().setupUi(self._settings)
        self._settings.show()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
