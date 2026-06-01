"""mini_designer_split/codegen.py — 代码生成器"""

import os, re
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QSizePolicy, QPushButton, QToolButton, QCommandLinkButton,
    QCheckBox, QRadioButton, QLabel, QGroupBox, QLineEdit, QComboBox,
    QSpinBox, QDoubleSpinBox, QSlider, QProgressBar, QTextEdit as QWTextEdit,
    QLCDNumber, QDial, QFrame, QSplitter, QTreeWidget, QTableWidget,
)

from .config import (
    BINDABLE_WIDGETS, NAME_TO_PREFIX, SIZE_POLICY_MAP, _esc, _sanitize, _policy_to_str,
    CUSTOM_WIDGETS,
)


class CodeGenerator:
    """生成器：将画布上的控件布局导出为可运行的 Python 代码"""

    @staticmethod
    def generate(canvas, as_ui_class=False, qss_filename="style.qss") -> str:
        if as_ui_class:
            return CodeGenerator._generate_ui_class(canvas, qss_filename=qss_filename)
        canvas._save_current_page()
        multi_page = canvas.page_count() > 1
        lines = [
            "import sys, os",
            "from PySide6.QtWidgets import (",
            "    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,",
            "    QPushButton, QLabel, QLineEdit, QComboBox, QGroupBox, QFrame,",
            "    QCheckBox, QRadioButton, QSpinBox, QDoubleSpinBox, QSlider,",
            "    QProgressBar, QTextEdit, QTextBrowser, QDateEdit, QTimeEdit,",
            "    QTabWidget, QScrollArea, QToolButton, QDialogButtonBox,",
            "    QCalendarWidget, QDial, QLCDNumber, QCommandLinkButton,",
            "    QStackedWidget, QListWidget, QTreeWidget, QTableWidget, QSplitter,",
            "    QSizePolicy, QSpacerItem,",
            ")",
            "",
        ]

        custom_imports = CodeGenerator._collect_custom_imports(canvas)
        for imp in custom_imports:
            lines.insert(0, imp)
        if custom_imports:
            lines.insert(0, "")

        tag_bindings = CodeGenerator._collect_tag_bindings(canvas)
        if tag_bindings:
            lines.extend(CodeGenerator._generate_data_binder(tag_bindings))
            lines.append("")

        _resize_fn = "setFixedSize" if getattr(canvas, "_fixed_canvas", False) else "resize"
        lines.extend([
            "class GeneratedWindow(QMainWindow):",
            "    def __init__(self):",
            "        super().__init__()",
            '        self.setWindowTitle("Generated Application")',
            f"        self.{_resize_fn}({canvas.design_width}, {canvas.design_height})",
            "",
            f"        qss_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '{qss_filename}')",
            "        if os.path.exists(qss_path):",
            "            with open(qss_path, 'r', encoding='utf-8') as f:",
            "                QApplication.instance().setStyleSheet(f.read())",
            "",
        ])

        obj_name_map = {}
        if multi_page:
            CodeGenerator._emit_multipage(canvas, lines, tag_bindings, obj_name_map)
        else:
            lines += [
                "        self.central_widget = QWidget()",
                "        self.setCentralWidget(self.central_widget)",
                "",
            ]
            used = {}
            for w in canvas._canvas_widgets:
                if w.property("_designer_hidden"):
                    continue
                CodeGenerator._emit(w, lines, used, "self.central_widget", "        ", obj_name_map)
            if tag_bindings:
                lines.append("")
                lines.append("        # 初始化数据绑定管理器")
                lines.append("        self.data_binder = DataBinder(self)")
                lines.append("        # TODO: 在此处启动您的通信线程，调用 self.data_binder.update_tag(tag, value) 刷新UI")

        # 信号/槽连接
        if canvas._signal_connections:
            lines.append("")
            lines.append("        # 信号/槽连接")
            for conn in canvas._signal_connections:
                sig = conn["signal"].split("(")[0]
                src_var = obj_name_map.get(conn["source"], conn["source"])
                lines.append(f"        self.{src_var}.{sig}.connect(self.{conn['slot']})")
            lines.append("")
            generated_slots = set()
            for conn in canvas._signal_connections:
                slot = conn["slot"]
                if slot not in generated_slots:
                    generated_slots.add(slot)
                    callback_code = (canvas._callback_code or {}).get(slot, "").strip()
                    if callback_code:
                        if obj_name_map:
                            for obj_name, var_name in sorted(obj_name_map.items(), key=lambda x: -len(x[0])):
                                callback_code = callback_code.replace(f"self.{obj_name}", f"self.{var_name}")
                        lines.append("")
                        for cb_line in callback_code.split("\n"):
                            lines.append(f"    {cb_line}")
                        lines.append("")
                    else:
                        lines.append(f"    def {slot}(self):")
                        lines.append(f"        # TODO: 实现 {slot}")
                        lines.append("        pass")
                        lines.append("")

        anchor_widgets = CodeGenerator._collect_anchor_widgets(canvas)
        if anchor_widgets:
            lines.append("")
            lines.extend(CodeGenerator._generate_resize_event(anchor_widgets, used, canvas))

        lines += [
            "",
            'if __name__ == "__main__":',
            "    app = QApplication(sys.argv)",
            "    window = GeneratedWindow()",
            "    window.show()",
            "    sys.exit(app.exec())",
        ]
        return "\n".join(lines)

    @staticmethod
    def _generate_ui_class(canvas, qss_filename="style.qss") -> str:
        canvas._save_current_page()
        lines = [
            "from PySide6.QtWidgets import (",
            "    QWidget, QVBoxLayout, QHBoxLayout,",
            "    QPushButton, QLabel, QLineEdit, QComboBox, QGroupBox, QFrame,",
            "    QCheckBox, QRadioButton, QSpinBox, QDoubleSpinBox, QSlider,",
            "    QProgressBar, QTextEdit, QTextBrowser, QDateEdit, QTimeEdit,",
            "    QTabWidget, QScrollArea, QToolButton, QDialogButtonBox,",
            "    QCalendarWidget, QDial, QLCDNumber, QCommandLinkButton,",
            "    QStackedWidget, QListWidget, QTreeWidget, QTableWidget, QSplitter,",
            "    QSizePolicy,",
            ")",
            "",
        ]

        custom_imports = CodeGenerator._collect_custom_imports(canvas)
        for imp in custom_imports:
            lines.insert(0, imp)
        if custom_imports:
            lines.insert(0, "")

        tag_bindings = CodeGenerator._collect_tag_bindings(canvas)
        if tag_bindings:
            lines.extend(CodeGenerator._generate_data_binder(tag_bindings))
            lines.append("")

        _resize_fn = "setFixedSize" if getattr(canvas, "_fixed_canvas", False) else "resize"
        lines.extend([
            "class Ui_MainWindow(object):",
            "    def setupUi(self, MainWindow):",
            "        MainWindow.setWindowTitle('Generated Application')",
            f"        MainWindow.{_resize_fn}({canvas.design_width}, {canvas.design_height})",
            "",
            "        import os",
            f"        qss_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '{qss_filename}')",
            "        if os.path.exists(qss_path):",
            "            with open(qss_path, 'r', encoding='utf-8') as f:",
            "                MainWindow.setStyleSheet(f.read())",
            "",
            "        self.central_widget = QWidget()",
            "        MainWindow.setCentralWidget(self.central_widget)",
            "",
        ])
        obj_name_map = {}
        used = {}
        for w in canvas._canvas_widgets:
            if w.property("_designer_hidden"):
                continue
            CodeGenerator._emit(w, lines, used, "self.central_widget", "        ", obj_name_map)
        if tag_bindings:
            lines.append("")
            lines.append("        self.data_binder = DataBinder(self)")
        if canvas._signal_connections:
            lines.append("")
            for conn in canvas._signal_connections:
                sig = conn["signal"].split("(")[0]
                src_var = obj_name_map.get(conn["source"], conn["source"])
                lines.append(f"        self.{src_var}.{sig}.connect(self.{conn['slot']})")
        lines += [
            "",
            "    def retranslateUi(self, MainWindow):",
            "        pass",
            "",
        ]
        return "\n".join(lines)

    @staticmethod
    def _emit_multipage(canvas, lines, tag_bindings, obj_name_map=None):
        pages = canvas._pages
        page_names = [p["name"] for p in pages]
        btn_width = 120
        lines += [
            "        # ── 多页面布局 ──",
            "        self.central_widget = QWidget()",
            "        self.setCentralWidget(self.central_widget)",
            "        main_layout = QHBoxLayout(self.central_widget)",
            "        main_layout.setContentsMargins(0, 0, 0, 0)",
            "        main_layout.setSpacing(0)",
            "",
            "        # 侧边导航栏",
            "        self.nav_widget = QWidget()",
            f"        self.nav_widget.setFixedWidth({btn_width + 20})",
            "        self.nav_widget.setStyleSheet('QWidget{background:#2c3e50;}')",
            "        nav_layout = QVBoxLayout(self.nav_widget)",
            "        nav_layout.setContentsMargins(4, 8, 4, 8)",
            "        nav_layout.setSpacing(4)",
            "",
            "        self.nav_buttons = []",
            "        self.stack = QStackedWidget()",
            "",
        ]
        for i, pname in enumerate(page_names):
            safe_name = _sanitize(pname) or f"page{i}"
            lines += [
                f"        btn_{safe_name} = QPushButton('{_esc(pname)}')",
                f"        btn_{safe_name}.setFixedHeight(36)",
                "        btn_{safe_name}.setStyleSheet('QPushButton{{color:#ecf0f1;background:transparent;border:none;text-align:left;padding:8px 12px;font-size:12px;border-radius:4px;}}"
                "QPushButton:hover{{background:#34495e;}}QPushButton:checked{{background:#4A90D9;font-weight:bold;}}')",
                f"        btn_{safe_name}.setCheckable(True)",
                f"        btn_{safe_name}.clicked.connect(lambda checked, idx={i}: self.stack.setCurrentIndex(idx))",
                f"        nav_layout.addWidget(btn_{safe_name})",
                f"        self.nav_buttons.append(btn_{safe_name})",
                f"        # ── 页面: {pname} ──",
                f"        page_{safe_name} = QWidget()",
                f"        self.stack.addWidget(page_{safe_name})",
                "",
            ]
        lines += [
            "        nav_layout.addStretch()",
            "        main_layout.addWidget(self.nav_widget)",
            "        main_layout.addWidget(self.stack)",
            "        self.nav_buttons[0].setChecked(True) if self.nav_buttons else None",
            "",
        ]
        for i, p in enumerate(pages):
            safe_name = _sanitize(p["name"]) or f"page{i}"
            used = {}
            for w in p["widgets"]:
                if w.property("_designer_hidden"):
                    continue
                CodeGenerator._emit(w, lines, used, f"page_{safe_name}", "        ", obj_name_map)
        if tag_bindings:
            lines.append("")
            lines.append("        # 初始化数据绑定管理器")
            lines.append("        self.data_binder = DataBinder(self)")
            lines.append("        # TODO: 启动通信线程，调用 self.data_binder.update_tag(tag, value) 刷新UI")

    @staticmethod
    def _collect_custom_imports(canvas):
        custom_cls_to_file = {}
        for display_name, cls, kwargs, filepath in CUSTOM_WIDGETS:
            custom_cls_to_file[cls] = filepath

        cls_to_file = {}
        def scan(widgets):
            for w in widgets:
                if w.property("_designer_hidden"):
                    continue
                cls = type(w)
                mod = cls.__module__
                if cls in custom_cls_to_file:
                    cls_to_file[cls] = custom_cls_to_file[cls]
                elif w.property("_custom_source"):
                    src = w.property("_custom_source")
                    if os.path.isfile(src):
                        cls_to_file[cls] = src
                elif cls.__name__ not in cls_to_file and mod not in ('__main__', 'builtins') and not mod.startswith('PySide6'):
                    for display_name, ccls, kwargs, fp in CUSTOM_WIDGETS:
                        if ccls.__name__ == cls.__name__:
                            cls_to_file[cls] = fp
                            break
                if hasattr(w, "_content_layout"):
                    children = [
                        w._content_layout.itemAt(i).widget()
                        for i in range(w._content_layout.count())
                        if w._content_layout.itemAt(i) and w._content_layout.itemAt(i).widget()
                    ]
                    scan(children)

        scan(canvas._canvas_widgets)
        for p in canvas._pages:
            if p["widgets"] is not canvas._canvas_widgets:
                scan(p["widgets"])

        file_to_classes = {}
        for cls, fp in cls_to_file.items():
            mod_name = os.path.splitext(os.path.basename(fp))[0]
            file_to_classes.setdefault(mod_name, []).append(cls.__name__)

        imports = []
        for mod_name, class_names in file_to_classes.items():
            imports.append(f"from {mod_name} import {', '.join(sorted(class_names))}")
        return imports

    @staticmethod
    def _collect_tag_bindings(canvas):
        bindings = []
        def scan(widgets):
            for w in widgets:
                tag = w.property("_tag")
                if tag and (isinstance(w, BINDABLE_WIDGETS) or hasattr(w, 'setValue')):
                    bindings.append((tag, w.objectName(), type(w).__name__))
                if hasattr(w, "_content_layout"):
                    ly = w._content_layout
                    children = [
                        ly.itemAt(i).widget()
                        for i in range(ly.count())
                        if ly.itemAt(i) and ly.itemAt(i).widget()
                    ]
                    scan(children)
        scan(canvas._canvas_widgets)
        return bindings

    @staticmethod
    def _generate_data_binder(bindings):
        lines = [
            "class DataBinder:",
            '    """',
            "    数据绑定管理器 - 由设计器自动生成",
            "    外部通信线程通过 update_tag(tag, value) 统一刷新UI",
            '    """',
            "    def __init__(self, ui):",
            "        self.ui = ui",
            "        self._data = {}",
            "",
            "    def update_tag(self, tag: str, value):",
            "        self._data[tag] = value",
        ]
        for tag, var_name, cls_name in bindings:
            safe_tag = tag.replace("'", "\\'")
            if cls_name in ("QLabel", "QGroupBox", "QLineEdit"):
                lines.append(f"        if tag == '{safe_tag}': self.ui.{var_name}.setText(str(value))")
            elif cls_name == "QLCDNumber":
                lines.append(f"        if tag == '{safe_tag}': self.ui.{var_name}.display(float(value) if value else 0)")
            elif cls_name in ("QProgressBar", "QSlider"):
                lines.append(f"        if tag == '{safe_tag}': self.ui.{var_name}.setValue(int(float(value)))")
            elif cls_name in ("QSpinBox", "QDoubleSpinBox"):
                lines.append(f"        if tag == '{safe_tag}': self.ui.{var_name}.setValue(float(value))")
            elif cls_name in ("QCheckBox", "QRadioButton"):
                lines.append(f"        if tag == '{safe_tag}': self.ui.{var_name}.setChecked(bool(value))")
            else:
                lines.append(f"        if tag == '{safe_tag}': self.ui.{var_name}.setValue(float(value))  # 通用: 自定义控件")
        lines.extend([
            "",
            "    def get_tag(self, tag: str):",
            "        return self._data.get(tag)",
        ])
        return lines

    @staticmethod
    def _collect_anchor_widgets(canvas):
        result = []
        for w in canvas._canvas_widgets:
            if w.property("_designer_hidden"):
                continue
            parent = w.parent()
            if parent and hasattr(parent, "_content_layout"):
                continue
            al = bool(w.property("_anchor_left"))
            ar = bool(w.property("_anchor_right"))
            at = bool(w.property("_anchor_top"))
            ab = bool(w.property("_anchor_bottom"))
            if al or ar or at or ab:
                result.append((w.objectName(), w.geometry(), al, ar, at, ab))
        return result

    @staticmethod
    def _generate_resize_event(anchor_widgets, used, canvas):
        lines = [
            f"    # 设计基准尺寸: {canvas.design_width}x{canvas.design_height}",
            "    def resizeEvent(self, event):",
            "        super().resizeEvent(event)",
            "        w = self.central_widget.width()",
            "        h = self.central_widget.height()",
            f"        sx = w / {canvas.design_width}",
            f"        sy = h / {canvas.design_height}",
        ]
        dw, dh = canvas.design_width, canvas.design_height
        for var_name, geo, al, ar, at, ab in anchor_widgets:
            x, y, gw, gh = geo.x(), geo.y(), geo.width(), geo.height()
            if al and ar:
                lines.append(f"        self.{var_name}.setGeometry(int({x} * sx), int({y} * sy), w - int({x} * sx) - int({(dw - x - gw)} * sx), int({gh} * sy))")
            elif al:
                lines.append(f"        self.{var_name}.move(int({x} * sx), int({y} * sy))")
            elif ar:
                lines.append(f"        self.{var_name}.move(w - int({dw - x - gw} * sx) - {gw}, int({y} * sy))")
            if at and ab and not (al and ar):
                lines.append(f"        self.{var_name}.setGeometry(self.{var_name}.x(), int({y} * sy), self.{var_name}.width(), h - int({y} * sy) - int({(dh - y - gh)} * sy))")
            elif at and not (al or ar):
                lines.append(f"        self.{var_name}.move(self.{var_name}.x(), int({y} * sy))")
            elif ab and not (al or ar):
                lines.append(f"        self.{var_name}.move(self.{var_name}.x(), h - int({dh - y - gh} * sy) - {gh})")
        return lines

    @staticmethod
    def _var(widget, used):
        display_name = widget.property("_display_name") or ""
        prefix = NAME_TO_PREFIX.get(display_name, _sanitize(type(widget).__name__))
        obj_name = widget.objectName()
        default_pattern = f"{prefix}_\\d+"
        base = _sanitize(obj_name) if obj_name and not re.match(default_pattern, obj_name) else prefix
        if base not in used:
            used[base] = 0
            return base
        used[base] += 1
        return f"{base}_{used[base]}"

    @staticmethod
    def _emit(w, lines, used, parent_ref, indent, obj_name_map=None):
        var = CodeGenerator._var(w, used)
        if obj_name_map is not None:
            obj_name = w.objectName()
            if obj_name:
                obj_name_map[obj_name] = var
        g = w.geometry()
        cls = type(w).__name__
        if hasattr(w, "_content_layout"):
            ly_cls = type(w._content_layout).__name__
            ly_var = f"ly_{var}"
            lines.append(f"{indent}# ── Container: {var} ──")
            lines.append(f"{indent}self.{var} = QFrame({parent_ref})")
            lines.append(f"{indent}self.{var}.setGeometry({g.x()}, {g.y()}, {g.width()}, {g.height()})")
            ss = w.styleSheet()
            if ss:
                lines.append(f'{indent}self.{var}.setStyleSheet("{_esc(ss)}")')
            lines.append(f"{indent}self.{ly_var} = {ly_cls}(self.{var})")
            lines.append(f"{indent}self.{ly_var}.setContentsMargins(8, 8, 8, 8)")
            lines.append(f"{indent}self.{ly_var}.setSpacing(4)")
            lines.append("")
            for i in range(w._content_layout.count()):
                cw = w._content_layout.itemAt(i).widget()
                if cw and not cw.property("_designer_hidden"):
                    CodeGenerator._emit_child(cw, lines, used, f"self.{ly_var}", indent, obj_name_map)
            return

        ctor_args, post_init = "", []
        if isinstance(w, (QPushButton, QCheckBox, QRadioButton, QCommandLinkButton)):
            if hasattr(w, "text") and w.text():
                ctor_args = f'"{_esc(w.text())}"'
        elif isinstance(w, QToolButton):
            if hasattr(w, "text") and w.text():
                post_init.append(f'self.{var}.setText("{_esc(w.text())}")')
        elif isinstance(w, QLabel):
            ctor_args = f'"{_esc(w.text())}"'
            if w.openExternalLinks():
                post_init.append(f"self.{var}.setOpenExternalLinks(True)")
        elif isinstance(w, QGroupBox):
            ctor_args = f'"{_esc(w.title())}"'
        elif isinstance(w, QLineEdit) and w.placeholderText():
            post_init.append(f'self.{var}.setPlaceholderText("{_esc(w.placeholderText())}")')
        elif isinstance(w, QComboBox):
            items = [w.itemText(i) for i in range(w.count())]
            if items:
                escaped_items = ", ".join([f'"{_esc(i)}"' for i in items])
                post_init.append(f"self.{var}.addItems([{escaped_items}])")
        elif isinstance(w, QSpinBox):
            post_init += [
                f"self.{var}.setRange({w.minimum()}, {w.maximum()})",
                f"self.{var}.setValue({w.value()})",
            ]
        elif isinstance(w, QDoubleSpinBox):
            post_init += [
                f"self.{var}.setRange({w.minimum()}, {w.maximum()})",
                f"self.{var}.setDecimals({w.decimals()})",
                f"self.{var}.setValue({w.value()})",
            ]
        elif isinstance(w, QSlider):
            ctor_args = "Qt.Horizontal" if w.orientation() == Qt.Horizontal else "Qt.Vertical"
            post_init.append(f"self.{var}.setValue({w.value()})")
        elif isinstance(w, QProgressBar):
            post_init.append(f"self.{var}.setValue({w.value()})")
        elif isinstance(w, QLCDNumber):
            post_init.append(f"self.{var}.display({w.intValue()})")
        elif isinstance(w, QDial):
            post_init += [
                f"self.{var}.setRange({w.minimum()}, {w.maximum()})",
                f"self.{var}.setValue({w.value()})",
            ]
        elif isinstance(w, QWTextEdit) and w.placeholderText():
            post_init.append(f'self.{var}.setPlaceholderText("{_esc(w.placeholderText())}")')
        elif isinstance(w, QTreeWidget):
            post_init += [
                "self.{var}.setHeaderLabels(['列1', '列2'])",
                f"self.{var}.setColumnCount(2)",
            ]
        elif isinstance(w, QTableWidget):
            post_init += [
                f"self.{var}.setRowCount(3)",
                f"self.{var}.setColumnCount(3)",
            ]
        elif isinstance(w, QSplitter):
            ctor_args = "Qt.Horizontal" if w.orientation() == Qt.Horizontal else "Qt.Vertical"

        if cls not in (
            "QPushButton", "QToolButton", "QLabel", "QGroupBox", "QLineEdit",
            "QComboBox", "QCheckBox", "QRadioButton", "QSpinBox", "QDoubleSpinBox",
            "QSlider", "QProgressBar", "QLCDNumber", "QDial", "QCommandLinkButton",
            "QFrame", "QSplitter",
        ):
            lines.append(f"{indent}self.{var} = {cls}({parent_ref})")
            lines.append(f"{indent}self.{var}.setGeometry({g.x()}, {g.y()}, {g.width()}, {g.height()})")
            role = w.property("role") or "default"
            if role != "default":
                lines.append(f'{indent}self.{var}.setProperty("role", "{role}")')
            obj_name = w.objectName()
            if obj_name:
                lines.append(f'{indent}self.{var}.setObjectName("{obj_name}")')
            ss = w.styleSheet()
            if ss:
                lines.append(f'{indent}self.{var}.setStyleSheet("{_esc(ss)}")')
            lines.append("")
            return

        lines.append(
            f"{indent}self.{var} = {cls}({ctor_args}, {parent_ref})" if ctor_args
            else f"{indent}self.{var} = {cls}({parent_ref})"
        )
        lines.append(f"{indent}self.{var}.setGeometry({g.x()}, {g.y()}, {g.width()}, {g.height()})")
        role = w.property("role") or "default"
        if role != "default":
            lines.append(f'{indent}self.{var}.setProperty("role", "{role}")')
        obj_name = w.objectName()
        display_name = w.property("_display_name") or ""
        default_prefix = NAME_TO_PREFIX.get(display_name, _sanitize(cls))
        if obj_name and not re.match(f"{default_prefix}_\\d+", obj_name):
            lines.append(f'{indent}self.{var}.setObjectName("{obj_name}")')
        ss = w.styleSheet()
        if ss:
            lines.append(f'{indent}self.{var}.setStyleSheet("{_esc(ss)}")')
        for pi in post_init:
            lines.append(f"{indent}{pi}")
        lines.append("")

    @staticmethod
    def _emit_child(w, lines, used, layout_ref, indent, obj_name_map=None):
        var = CodeGenerator._var(w, used)
        if obj_name_map is not None:
            obj_name = w.objectName()
            if obj_name:
                obj_name_map[obj_name] = var
        cls = type(w).__name__
        ctor_args, post_init = "", []
        if isinstance(w, (QPushButton, QCheckBox, QRadioButton, QLabel, QCommandLinkButton)):
            if hasattr(w, "text") and w.text():
                ctor_args = f'"{_esc(w.text())}"'
        elif isinstance(w, QToolButton):
            if hasattr(w, "text") and w.text():
                post_init.append(f'self.{var}.setText("{_esc(w.text())}")')
        elif isinstance(w, QGroupBox):
            ctor_args = f'"{_esc(w.title())}"'
        elif isinstance(w, QLineEdit) and w.placeholderText():
            post_init.append(f'self.{var}.setPlaceholderText("{_esc(w.placeholderText())}")')
        elif isinstance(w, QLabel) and w.openExternalLinks():
            post_init.append(f"self.{var}.setOpenExternalLinks(True)")
        elif isinstance(w, QTreeWidget):
            post_init += [
                f"self.{var}.setHeaderLabels(['列1', '列2'])",
                f"self.{var}.setColumnCount(2)",
            ]
        elif isinstance(w, QTableWidget):
            post_init += [
                f"self.{var}.setRowCount(3)",
                f"self.{var}.setColumnCount(3)",
            ]
        elif isinstance(w, QSplitter):
            ctor_args = "Qt.Horizontal" if w.orientation() == Qt.Horizontal else "Qt.Vertical"

        lines.append(
            f"{indent}self.{var} = {cls}({ctor_args})" if ctor_args
            else f"{indent}self.{var} = {cls}()"
        )
        role = w.property("role") or "default"
        if role != "default":
            lines.append(f'{indent}self.{var}.setProperty("role", "{role}")')
        sp = w.sizePolicy()
        h_pol = _policy_to_str(sp.horizontalPolicy())
        v_pol = _policy_to_str(sp.verticalPolicy())
        if h_pol != "Preferred" or v_pol != "Preferred":
            lines.append(f'{indent}self.{var}.setSizePolicy(QSizePolicy.{h_pol}, QSizePolicy.{v_pol})')
        if w.minimumWidth() > 0 or w.minimumHeight() > 0:
            lines.append(f'{indent}self.{var}.setMinimumSize({w.minimumWidth()}, {w.minimumHeight()})')
        if w.maximumWidth() < 16777215 or w.maximumHeight() < 16777215:
            lines.append(f'{indent}self.{var}.setMaximumSize({w.maximumWidth()}, {w.maximumHeight()})')
        lines.append(f"{indent}{layout_ref}.addWidget(self.{var})")
        for pi in post_init:
            lines.append(f"{indent}{pi}")
        lines.append("")
