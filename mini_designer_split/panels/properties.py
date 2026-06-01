"""mini_designer_split/panels/properties.py — 属性编辑器面板"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QComboBox, QCheckBox, QSizePolicy,
    QGroupBox, QDialogButtonBox, QLineEdit,
)
from PySide6.QtWidgets import QTextEdit as QWTextEdit
from PySide6.QtGui import QColor

from ..config import (
    WIDGET_ROLES, BINDABLE_WIDGETS, SIZE_POLICY_MAP, SIZE_POLICY_NAMES,
    _policy_to_str, _sanitize, _sanitize,
)
from ..commands import (
    PropertyChangeCmd, BatchPropertyChangeCmd,
)


class PropertyEditor(QWidget):
    """属性编辑面板 — 显示和编辑选中控件的属性"""

    property_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.header = QLabel("<b>属性面板</b>")
        self.header.setStyleSheet("padding:4px 8px; font-size:13px;")
        layout.addWidget(self.header)

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["属性", "值"])
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.Stretch
        )
        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.Stretch
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(
            QAbstractItemView.DoubleClicked
            | QAbstractItemView.EditKeyPressed
        )
        self.table.setStyleSheet(
            "QTableWidget{gridline-color:#ddd;font-size:12px;}"
            " QTableWidget::item{padding:4px;}"
        )
        layout.addWidget(self.table)

        self._widget = None
        self._batch_widgets = []
        self._busy = False
        self.table.cellChanged.connect(self._on_cell_changed)

    def set_widget(self, widget=None):
        self._widget = widget
        self._batch_widgets = []
        self._refresh()

    def set_batch_widgets(self, widgets):
        self._widget = None
        self._batch_widgets = list(widgets)
        self._refresh()

    def _get_widget_value(self, w, prop):
        try:
            if prop == "objectName":
                return w.objectName()
            elif prop == "text":
                return w.text() if hasattr(w, "text") else None
            elif prop == "title":
                return w.title() if hasattr(w, "title") else None
            elif prop == "placeholderText":
                return (
                    w.placeholderText()
                    if hasattr(w, "placeholderText")
                    else None
                )
            elif prop == "role":
                return w.property("role") or "default"
            elif prop == "tag":
                return w.property("_tag") or ""
            elif prop == "styleSheet":
                return w.styleSheet()
            elif prop == "value":
                return (
                    str(w.value())
                    if hasattr(w, "value") and callable(w.value)
                    else None
                )
            elif prop == "width":
                return str(w.width())
            elif prop == "height":
                return str(w.height())
            elif prop == "minWidth":
                return str(w.minimumWidth())
            elif prop == "minHeight":
                return str(w.minimumHeight())
            elif prop == "maxWidth":
                return str(w.maximumWidth())
            elif prop == "maxHeight":
                return str(w.maximumHeight())
        except Exception:
            return None
        return None

    def _refresh(self):
        self._busy = True
        self.table.setRowCount(0)
        if self._batch_widgets and len(self._batch_widgets) >= 2:
            self.header.setText(
                f"<b>批量编辑 ({len(self._batch_widgets)} 个控件)</b>"
            )
            self._refresh_batch()
            self._busy = False
            return
        self.header.setText("<b>属性面板</b>")
        w = self._widget
        if not w:
            self._busy = False
            return

        props = []
        props.append(("objectName", w.objectName(), True))
        if isinstance(w, BINDABLE_WIDGETS) or hasattr(w, 'setValue'):
            props.append(("tag", w.property("_tag") or "", True))
        cls_name = type(w).__name__
        roles = WIDGET_ROLES.get(cls_name, [])
        if roles:
            props.append(("role", w.property("role") or "default", True))
        if hasattr(w, "text") and not isinstance(
            w, (QGroupBox, QDialogButtonBox)
        ):
            props.append(("text", w.text(), True))
        if hasattr(w, "title") and isinstance(w, QGroupBox):
            props.append(("title", w.title(), True))
        if (
            hasattr(w, "title")
            and callable(getattr(w, "title", None))
            and not isinstance(w, QGroupBox)
        ):
            props.append(("title", w.title(), True))
        if hasattr(w, 'setGaugeTitle'):
            props.append(("title", w._title, True))
        if hasattr(w, 'setUnit'):
            props.append(("unit", w._unit, True))
        if isinstance(w, (QLineEdit, QWTextEdit)):
            props.append(("placeholderText", w.placeholderText(), True))
        if hasattr(w, "value") and callable(getattr(w, "value", None)):
            props.append(("value", str(w.value()), True))

        parent = w.parent()
        in_container = parent and hasattr(parent, "_content_layout")
        if in_container:
            sp = w.sizePolicy()
            props.append(("hSizePolicy", _policy_to_str(sp.horizontalPolicy()), True))
            props.append(("vSizePolicy", _policy_to_str(sp.verticalPolicy()), True))
            props.append(("minWidth", str(w.minimumWidth()), True))
            props.append(("minHeight", str(w.minimumHeight()), True))
            props.append(("maxWidth", str(w.maximumWidth()), True))
            props.append(("maxHeight", str(w.maximumHeight()), True))
        else:
            g = w.geometry()
            props += [
                ("x", str(g.x()), True),
                ("y", str(g.y()), True),
                ("width", str(g.width()), True),
                ("height", str(g.height()), True),
                ("anchor_left", "✓" if w.property("_anchor_left") else "", True),
                ("anchor_right", "✓" if w.property("_anchor_right") else "", True),
                ("anchor_top", "✓" if w.property("_anchor_top") else "", True),
                ("anchor_bottom", "✓" if w.property("_anchor_bottom") else "", True),
            ]
        props.append(("styleSheet", w.styleSheet(), True))
        if hasattr(w, "_content_layout"):
            ly = w._content_layout
            margins = ly.contentsMargins()
            props.append(("marginLeft", str(margins.left()), True))
            props.append(("marginTop", str(margins.top()), True))
            props.append(("marginRight", str(margins.right()), True))
            props.append(("marginBottom", str(margins.bottom()), True))
            props.append(("spacing", str(ly.spacing()), True))
        self._render_props(props, w)
        self._busy = False

    def _refresh_batch(self):
        widgets = self._batch_widgets
        candidate_props = [
            ("role", lambda w: type(w).__name__ in WIDGET_ROLES),
            ("text", lambda w: hasattr(w, "text") and not isinstance(w, (QGroupBox, QDialogButtonBox))),
            ("title", lambda w: hasattr(w, "title") and isinstance(w, QGroupBox)),
            ("placeholderText", lambda w: isinstance(w, (QLineEdit, QWTextEdit))),
            ("tag", lambda w: isinstance(w, BINDABLE_WIDGETS) or hasattr(w, 'setValue')),
            ("width", lambda w: True),
            ("height", lambda w: True),
            ("minWidth", lambda w: True),
            ("minHeight", lambda w: True),
            ("maxWidth", lambda w: True),
            ("maxHeight", lambda w: True),
            ("styleSheet", lambda w: True),
        ]
        props = []
        for prop_name, condition in candidate_props:
            applicable = [w for w in widgets if condition(w)]
            if not applicable:
                continue
            values = [self._get_widget_value(w, prop_name) for w in applicable]
            values = [v for v in values if v is not None]
            if not values:
                continue
            all_same = all(v == values[0] for v in values)
            display_val = values[0] if all_same else "(混合)"
            props.append((prop_name, display_val, True))
        if not props:
            self.table.setRowCount(1)
            ki = QTableWidgetItem("提示")
            ki.setFlags(ki.flags() & ~Qt.ItemIsEditable)
            ki.setBackground(QColor("#f0f0f0"))
            self.table.setItem(0, 0, ki)
            vi = QTableWidgetItem("选中控件无公共可编辑属性")
            vi.setFlags(vi.flags() & ~Qt.ItemIsEditable)
            vi.setForeground(QColor("#999"))
            self.table.setItem(0, 1, vi)
            return
        self._render_props(props, None)

    def _render_props(self, props, single_widget):
        row = 0
        for prop, value, _ in props:
            self.table.insertRow(row)
            ki = QTableWidgetItem(prop)
            ki.setFlags(ki.flags() & ~Qt.ItemIsEditable)
            ki.setBackground(QColor("#f0f0f0"))
            self.table.setItem(row, 0, ki)
            if prop == "objectName" and single_widget:
                vi = QTableWidgetItem(str(value) if value is not None else "")
                is_auto = single_widget.property("_auto_objectName")
                if is_auto:
                    f = vi.font()
                    f.setItalic(True)
                    vi.setFont(f)
                    vi.setForeground(QColor("#999"))
                    vi.setToolTip(
                        "此为自动生成的临时名称，设置tag后将自动同步为语义化名称"
                    )
                self.table.setItem(row, 1, vi)
            elif prop in (
                "anchor_left", "anchor_right",
                "anchor_top", "anchor_bottom",
            ) and single_widget:
                cb = QCheckBox()
                cb.setChecked(value == "✓")
                cb.stateChanged.connect(
                    lambda state, widget=single_widget, p=prop:
                        self._on_anchor_changed(widget, p, state)
                )
                self.table.setCellWidget(row, 1, cb)
            elif prop == "role":
                if single_widget:
                    roles = WIDGET_ROLES.get(type(single_widget).__name__, [])
                elif self._batch_widgets:
                    all_roles = set()
                    for bw in self._batch_widgets:
                        rn = type(bw).__name__
                        if rn in WIDGET_ROLES:
                            all_roles.update(WIDGET_ROLES[rn])
                    roles = sorted(all_roles)
                else:
                    roles = []
                combo = QComboBox()
                combo.addItems(roles)
                if value != "(混合)":
                    combo.setCurrentText(value)
                combo.currentTextChanged.connect(
                    lambda text, p=prop: self._on_combo_changed(p, text)
                )
                self.table.setCellWidget(row, 1, combo)
            elif prop in ("hSizePolicy", "vSizePolicy") and single_widget:
                combo = QComboBox()
                combo.addItems(SIZE_POLICY_NAMES)
                combo.setCurrentText(value)
                combo.currentTextChanged.connect(
                    lambda text, widget=single_widget, p=prop:
                        self._on_size_policy_changed(widget, p, text)
                )
                self.table.setCellWidget(row, 1, combo)
            else:
                vi = QTableWidgetItem(str(value) if value is not None else "")
                if value == "(混合)":
                    vi.setForeground(QColor("#999"))
                    f = vi.font()
                    f.setItalic(True)
                    vi.setFont(f)
                self.table.setItem(row, 1, vi)
            row += 1

    def _on_combo_changed(self, prop, value):
        if self._busy:
            return
        if self._batch_widgets and len(self._batch_widgets) >= 2:
            self._apply_batch_property(prop, value)
        elif self._widget and prop == "role":
            self._on_role_changed(self._widget, value)

    def _apply_batch_property(self, prop, value):
        if not self._batch_widgets:
            return
        canvas = self._batch_widgets[0].parent()
        while canvas and getattr(canvas, "history", None) is None:
            canvas = canvas.parent()
        if not canvas:
            return
        old_vals, applicable_widgets = [], []
        for w in self._batch_widgets:
            ov = self._get_widget_value(w, prop)
            if ov is not None:
                old_vals.append(ov)
                applicable_widgets.append(w)
        if not applicable_widgets:
            return
        canvas.history.push(
            BatchPropertyChangeCmd(canvas, applicable_widgets, prop, old_vals, value)
        )
        canvas.widget_modified.emit()
        self.property_changed.emit()

    def _on_anchor_changed(self, widget, prop, state):
        if self._busy or not widget:
            return
        checked = state == Qt.Checked
        old_val = "✓" if widget.property(f"_{prop}") else ""
        new_val = "✓" if checked else ""
        if old_val == new_val:
            return
        canvas = widget.parent()
        while canvas and getattr(canvas, "history", None) is None:
            canvas = canvas.parent()
        if canvas:
            canvas.history.push(
                PropertyChangeCmd(canvas, widget, prop, old_val, new_val)
            )
        self.property_changed.emit()

    def _on_role_changed(self, widget, role):
        if self._busy or not widget:
            return
        old_role = widget.property("role") or "default"
        if old_role == role:
            return
        canvas = widget.parent()
        while canvas and getattr(canvas, "history", None) is None:
            canvas = canvas.parent()
        if canvas:
            canvas.history.push(
                PropertyChangeCmd(canvas, widget, "role", old_role, role)
            )
        self.property_changed.emit()

    def _on_size_policy_changed(self, widget, prop, policy_name):
        if self._busy or not widget or policy_name not in SIZE_POLICY_MAP:
            return
        sp = widget.sizePolicy()
        old_val = (
            _policy_to_str(sp.horizontalPolicy())
            if prop == "hSizePolicy"
            else _policy_to_str(sp.verticalPolicy())
        )
        if old_val == policy_name:
            return
        canvas = widget.parent()
        while canvas and not isinstance(
            getattr(canvas, "history", None) is not None
        ):
            canvas = canvas.parent()
        if canvas:
            canvas.history.push(
                PropertyChangeCmd(canvas, widget, prop, old_val, policy_name)
            )
        self.property_changed.emit()

    def _on_cell_changed(self, row, col):
        if self._busy or col != 1:
            return
        prop = self.table.item(row, 0).text()
        if prop in (
            "role", "hSizePolicy", "vSizePolicy",
            "anchor_left", "anchor_right", "anchor_top", "anchor_bottom",
        ):
            return
        value = self.table.item(row, 1).text()
        if self._batch_widgets and len(self._batch_widgets) >= 2:
            self._apply_batch_property(prop, value)
            return
        if not self._widget:
            return
        canvas = self._widget.parent()
        while canvas and getattr(canvas, "history", None) is None:
            canvas = canvas.parent()
        if not canvas:
            return
        old_val = ""
        w = self._widget
        try:
            if prop == "objectName":
                old_val = w.objectName()
                w.setProperty("_auto_objectName", False)
            elif prop == "tag":
                old_val = w.property("_tag") or ""
                if value and w.property("_auto_objectName"):
                    new_obj_name = (
                        _sanitize(value)
                    )
                    existing_names = set()
                    for cw in canvas._canvas_widgets:
                        if cw is not w:
                            existing_names.add(cw.objectName())
                    final_name = new_obj_name
                    suffix = 1
                    while final_name in existing_names:
                        final_name = f"{new_obj_name}_{suffix}"
                        suffix += 1
                    w.setObjectName(final_name)
                    w.setProperty("_auto_objectName", False)
            elif prop == "text":
                old_val = w.text() if hasattr(w, "text") else ""
            elif prop == "title":
                if hasattr(w, "setGaugeTitle"):
                    old_val = w._title
                elif hasattr(w, "title") and callable(getattr(w, "title", None)):
                    old_val = w.title()
                else:
                    old_val = ""
            elif prop == "unit" and hasattr(w, "setUnit"):
                old_val = w._unit
            elif prop == "placeholderText":
                old_val = (
                    w.placeholderText()
                    if hasattr(w, "placeholderText")
                    else ""
                )
            elif prop == "value":
                old_val = (
                    str(w.value())
                    if hasattr(w, "value") and callable(w.value)
                    else ""
                )
            elif prop in ("x", "y", "width", "height"):
                g = w.geometry()
                old_val = str(
                    {"x": g.x(), "y": g.y(), "width": g.width(), "height": g.height()}[prop]
                )
            elif prop == "minWidth":
                old_val = str(w.minimumWidth())
            elif prop == "minHeight":
                old_val = str(w.minimumHeight())
            elif prop == "maxWidth":
                old_val = str(w.maximumWidth())
            elif prop == "maxHeight":
                old_val = str(w.maximumHeight())
            elif prop in (
                "marginLeft", "marginTop", "marginRight", "marginBottom"
            ) and hasattr(w, "_content_layout"):
                m = w._content_layout.contentsMargins()
                vals = {
                    "marginLeft": m.left(), "marginTop": m.top(),
                    "marginRight": m.right(), "marginBottom": m.bottom(),
                }
                old_val = str(vals.get(prop, 0))
            elif prop == "spacing" and hasattr(w, "_content_layout"):
                old_val = str(w._content_layout.spacing())
            elif prop == "styleSheet":
                old_val = w.styleSheet()
        except Exception:
            old_val = ""
        if str(old_val) == value:
            return
        canvas.history.push(
            PropertyChangeCmd(canvas, w, prop, old_val, value)
        )
        self._refresh()
        self.property_changed.emit()

    def refresh(self):
        self._refresh()
