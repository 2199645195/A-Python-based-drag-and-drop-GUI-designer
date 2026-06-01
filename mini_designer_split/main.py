"""mini_designer_split/main.py — 入口点

使用方式:
    cd mini_designer_split && python main.py
    或
    python -m mini_designer_split.main
"""

import sys
import os

# 兼容两种运行方式:
#   python main.py               (在 mini_designer_split/ 目录内)
#   python -m mini_designer_split.main  (在项目根目录)
if __name__ == "__main__" and __package__ is None:
    __package__ = "mini_designer_split"
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication

from .app import DesignerMainWindow


def main():
    app = QApplication(sys.argv)
    win = DesignerMainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
