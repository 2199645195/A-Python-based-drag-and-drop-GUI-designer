#!/usr/bin/env python3
"""
svg_import.py — SVG 导入器
支持导入外部 SVG 矢量图作为设计器控件
"""
import os, json, base64

from PySide6.QtCore import Qt, QRectF, QByteArray
from PySide6.QtGui import QPainter, QColor, QPen, QFont
from PySide6.QtWidgets import QWidget, QSizePolicy


# ═══════════════════════════════════════════════════════════════
# SVG 渲染控件
# ═══════════════════════════════════════════════════════════════
class SvgWidget(QWidget):
    """导入的 SVG 矢量图控件"""
    _display_name = "SVG图元"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(32, 32)
        self._svg_data = None
        self._svg_name = ""
        self._border_color = QColor("#ccc")
        self._renderer = None
        self._value = 0.0

    def setValue(self, v): self._value = float(v); self.update()
    def value(self): return self._value

    def load_svg(self, filepath):
        """加载 SVG 文件"""
        from PySide6.QtSvg import QSvgRenderer
        self._svg_name = os.path.splitext(os.path.basename(filepath))[0]
        try:
            self._renderer = QSvgRenderer(filepath)
            if self._renderer.isValid():
                self._display_name = self._svg_name
                self.update()
                return True
        except Exception:
            pass
        return False

    def load_svg_from_data(self, svg_string, name="SVG"):
        """从字符串加载 SVG"""
        from PySide6.QtSvg import QSvgRenderer
        self._svg_name = name
        self._svg_source = svg_string
        self._display_name = name
        try:
            self._renderer = QSvgRenderer(QByteArray(svg_string.encode()))
            if self._renderer.isValid():
                self.update()
                return True
        except Exception:
            pass
        return False

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        if self._renderer and self._renderer.isValid():
            # 在 SVG 保持宽高比的情况下渲染
            svg_size = self._renderer.defaultSize()
            if svg_size.isValid() and svg_size.width() > 0 and svg_size.height() > 0:
                scale = min(self.width() / svg_size.width(), self.height() / svg_size.height())
                sw = svg_size.width() * scale
                sh = svg_size.height() * scale
                x = (self.width() - sw) / 2
                y = (self.height() - sh) / 2
                self._renderer.render(p, QRectF(x, y, sw, sh))
            else:
                self._renderer.render(p, QRectF(0, 0, self.width(), self.height()))
        else:
            # 无 SVG 时显示占位
            p.setPen(QPen(QColor("#ccc"), 1, Qt.DashLine))
            p.drawRoundedRect(QRectF(2, 2, self.width() - 4, self.height() - 4), 4, 4)
            p.setPen(QColor("#999"))
            p.setFont(QFont("Arial", 10))
            p.drawText(self.rect(), Qt.AlignCenter, "SVG")
        p.end()

    def sizeHint(self):
        if self._renderer and self._renderer.isValid():
            s = self._renderer.defaultSize()
            if s.isValid(): return s
        return super().sizeHint()


# ═══════════════════════════════════════════════════════════════
# SVG 图元管理器
# ═══════════════════════════════════════════════════════════════
SVG_LIBRARY = {}  # name -> {"filepath": ..., "svg_data": ...}
SVG_INDEX_FILE = "svg_library.json"


def load_svg_library():
    """加载 SVG 图元库索引"""
    global SVG_LIBRARY
    if os.path.exists(SVG_INDEX_FILE):
        try:
            with open(SVG_INDEX_FILE, "r", encoding="utf-8") as f:
                SVG_LIBRARY = json.load(f)
        except Exception:
            SVG_LIBRARY = {}


def save_svg_library():
    """保存 SVG 图元库索引"""
    try:
        with open(SVG_INDEX_FILE, "w", encoding="utf-8") as f:
            json.dump(SVG_LIBRARY, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def import_svg_file(filepath):
    """导入 SVG 文件并注册为控件，返回 SvgWidget 子类"""
    name = os.path.splitext(os.path.basename(filepath))[0]
    with open(filepath, "r", encoding="utf-8") as f:
        svg_data = f.read()

    # 存到库
    SVG_LIBRARY[name] = {"filepath": filepath, "svg_data": svg_data}
    save_svg_library()

    # 动态创建对应的类
    cls_name = f"Svg_{name.replace(' ', '_').replace('-', '_')}"
    new_cls = type(cls_name, (SvgWidget,), {
        "_display_name": f"SVG-{name}",
        "__init__": lambda self, parent=None: (
            SvgWidget.__init__(self, parent),
            self.load_svg_from_data(SVG_LIBRARY[name]["svg_data"], name)
        )[-1] if False else None,
    })
    # 用更简单的方式
    def make_init(n):
        def init(self, parent=None):
            SvgWidget.__init__(self, parent)
            self.load_svg_from_data(SVG_LIBRARY[n]["svg_data"], n)
        return init
    new_cls.__init__ = make_init(name)
    new_cls.__module__ = __name__
    return name, new_cls


def register_all_svg_widgets():
    """注册所有已导入的 SVG 控件，返回列表"""
    load_svg_library()
    results = []
    for name in list(SVG_LIBRARY.keys()):
        svg_data = SVG_LIBRARY[name].get("svg_data", "")
        if not svg_data:
            fp = SVG_LIBRARY[name].get("filepath", "")
            if fp and os.path.exists(fp):
                with open(fp, "r", encoding="utf-8") as f:
                    svg_data = f.read()
                    SVG_LIBRARY[name]["svg_data"] = svg_data
        if svg_data:
            cls_name = f"Svg_{name.replace(' ', '_').replace('-', '_')}"
            new_cls = type(cls_name, (SvgWidget,), {"_display_name": f"SVG-{name}"})
            def make_init(n, sd):
                def init(self, parent=None):
                    SvgWidget.__init__(self, parent)
                    self.load_svg_from_data(sd, n)
                return init
            new_cls.__init__ = make_init(name, svg_data)
            new_cls.__module__ = __name__
            results.append((f"SVG-{name}", new_cls, {}))
    save_svg_library()
    return results
