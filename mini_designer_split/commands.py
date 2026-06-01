"""mini_designer_split/commands.py — 撤销/重做命令系统"""

from abc import ABC, abstractmethod
from PySide6.QtCore import QPoint, QRect
from PySide6.QtWidgets import QWidget


class Command(ABC):
    description = ""
    @abstractmethod
    def execute(self): ...
    @abstractmethod
    def undo(self): ...


class AddWidgetCmd(Command):
    def __init__(self, canvas, display_name, pos):
        self.canvas, self.display_name, self.pos = canvas, display_name, pos
        self.widget = None
        self.description = f"添加 {display_name}"
    def execute(self):
        self.widget = self.canvas._create_widget_internal(self.display_name, self.pos)
    def undo(self):
        if self.widget:
            self.canvas._remove_widget_internal(self.widget)


class DeleteWidgetCmd(Command):
    def __init__(self, canvas, widget):
        self.canvas, self.widget = canvas, widget
        self.display_name = widget.property("_display_name")
        self.geo = widget.geometry()
        self.role = widget.property("role") or "default"
        self.obj_name = widget.objectName()
        self.parent_container = None
        p = widget.parent()
        if p and hasattr(p, "_content_layout"):
            self.parent_container = p
        self.locked = bool(widget.property("_locked"))
        self.hidden = bool(widget.property("_designer_hidden"))
        self.tag = widget.property("_tag") or ""
        self.description = f"删除 {self.obj_name}"
    def execute(self):
        self.canvas._remove_widget_internal(self.widget)
    def undo(self):
        w = self.canvas._create_widget_internal(self.display_name, self.geo.topLeft())
        if w:
            w.setGeometry(self.geo)
            w.setProperty("role", self.role)
            w.setObjectName(self.obj_name)
            w.style().unpolish(w)
            w.style().polish(w)
            w.setProperty("_locked", self.locked)
            w.setProperty("_designer_hidden", self.hidden)
            w.setProperty("_tag", self.tag)
            if self.hidden:
                w.hide()
            if self.parent_container and hasattr(self.parent_container, "_content_layout"):
                self.parent_container._content_layout.removeWidget(w)
                self.parent_container._content_layout.addWidget(w)
            self.widget = w


class MoveWidgetCmd(Command):
    def __init__(self, canvas, widget, old_pos, new_pos):
        self.canvas, self.widget, self.old_pos, self.new_pos = canvas, widget, old_pos, new_pos
        self.description = f"移动 {widget.objectName()}"
    def execute(self):
        self.widget.move(self.new_pos)
    def undo(self):
        self.widget.move(self.old_pos)


class ResizeWidgetCmd(Command):
    def __init__(self, canvas, widget, old_geo, new_geo):
        self.canvas, self.widget, self.old_geo, self.new_geo = canvas, widget, old_geo, new_geo
        self.description = f"缩放 {widget.objectName()}"
    def execute(self):
        self.widget.setGeometry(self.new_geo)
    def undo(self):
        self.widget.setGeometry(self.old_geo)


class PropertyChangeCmd(Command):
    def __init__(self, canvas, widget, prop, old_val, new_val):
        self.canvas, self.widget, self.prop = canvas, widget, prop
        self.old_val, self.new_val = old_val, new_val
        self.description = f"修改 {prop}: {old_val} → {new_val}"
    def execute(self):
        self.canvas._apply_property(self.widget, self.prop, self.new_val)
    def undo(self):
        self.canvas._apply_property(self.widget, self.prop, self.old_val)


class BatchPropertyChangeCmd(Command):
    def __init__(self, canvas, widgets, prop, old_vals, new_val):
        self.canvas, self.widgets, self.prop = canvas, widgets, prop
        self.old_vals, self.new_val = old_vals, new_val
        self.description = f"批量修改 {prop} ({len(widgets)}个)"
    def execute(self):
        for w in self.widgets:
            self.canvas._apply_property(w, self.prop, self.new_val)
    def undo(self):
        for w, old_val in zip(self.widgets, self.old_vals):
            self.canvas._apply_property(w, self.prop, old_val)


class BatchAlignCmd(Command):
    def __init__(self, canvas, widgets, old_geos, new_geos):
        self.canvas, self.widgets = canvas, widgets
        self.old_geos, self.new_geos = old_geos, new_geos
        self.description = f"批量移动/对齐 ({len(widgets)}个)"
    def execute(self):
        for w, g in zip(self.widgets, self.new_geos):
            w.setGeometry(g)
    def undo(self):
        for w, g in zip(self.widgets, self.old_geos):
            w.setGeometry(g)


class ReorderWidgetCmd(Command):
    def __init__(self, container, widget, old_index, new_index):
        self.container, self.widget = container, widget
        self.old_index, self.new_index = old_index, new_index
        self.description = f"调整顺序 {widget.objectName()}"
    def execute(self):
        ly = self.container._content_layout
        ly.removeWidget(self.widget)
        ly.insertWidget(self.new_index, self.widget)
        self.widget.show()
        ly.update()
    def undo(self):
        ly = self.container._content_layout
        ly.removeWidget(self.widget)
        ly.insertWidget(self.old_index, self.widget)
        self.widget.show()
        ly.update()


class ExtractWidgetCmd(Command):
    def __init__(self, canvas, widget, container, index_in_layout):
        self.canvas, self.widget, self.container = canvas, widget, container
        self.index_in_layout = index_in_layout
        self.extract_pos = None
        self.description = f"移出容器 {widget.objectName()}"
    def execute(self):
        ly = self.container._content_layout
        ly.removeWidget(self.widget)
        cr = self.container.geometry()
        self.extract_pos = QPoint(cr.x() + cr.width() + 10, cr.y())
        self.widget.setParent(self.canvas)
        self.widget.move(self.extract_pos)
        self.widget.resize(self.widget.sizeHint())
        self.widget.show()
        self.canvas._install_filter_recursive(self.widget)
        self.canvas.widget_modified.emit()
    def undo(self):
        self.widget.setParent(self.container)
        self.container._content_layout.insertWidget(self.index_in_layout, self.widget)
        self.widget.show()
        self.container._content_layout.update()
        self.canvas.widget_modified.emit()


class InsertTemplateCmd(Command):
    def __init__(self, canvas, template_widgets, base_pos):
        self.canvas, self.template_widgets, self.base_pos = canvas, template_widgets, base_pos
        self.created_widgets = []
        self.description = "插入工业模板"
    def execute(self):
        self.created_widgets = []
        for tw in self.template_widgets:
            pos = QPoint(self.base_pos.x() + tw["x"], self.base_pos.y() + tw["y"])
            w = self.canvas._create_widget_internal(tw["type"], pos)
            if not w:
                continue
            w.resize(tw.get("w", 100), tw.get("h", 30))
            if "text" in tw and hasattr(w, "setText"):
                w.setText(tw["text"])
            if "styleSheet" in tw:
                w.setStyleSheet(tw["styleSheet"])
            if "tag" in tw:
                w.setProperty("_tag", tw["tag"])
            if "role" in tw:
                w.setProperty("role", tw["role"])
                w.style().unpolish(w)
                w.style().polish(w)
            if tw.get("anchor_left"):
                w.setProperty("_anchor_left", True)
            if tw.get("anchor_right"):
                w.setProperty("_anchor_right", True)
            if tw.get("anchor_top"):
                w.setProperty("_anchor_top", True)
            if tw.get("anchor_bottom"):
                w.setProperty("_anchor_bottom", True)
            self.created_widgets.append(w)
        if self.created_widgets:
            self.canvas._select(self.created_widgets[-1])
            self.canvas.widget_modified.emit()
    def undo(self):
        for w in reversed(self.created_widgets):
            self.canvas._remove_widget_internal(w)
        self.created_widgets = []
        self.canvas.widget_modified.emit()


class _ReparentIntoContainerCmd(Command):
    """将画布顶层控件移入容器"""
    def __init__(self, canvas, widget, container, canvas_index, layout_index):
        self.canvas = canvas
        self.widget = widget
        self.container = container
        self.canvas_index = canvas_index
        self.layout_index = layout_index
        self.description = f"移入容器 {widget.objectName()}"
    def execute(self):
        if self.widget in self.canvas._canvas_widgets:
            self.canvas._canvas_widgets.remove(self.widget)
        self.widget.setParent(self.container)
        ly = self.container._content_layout
        ly.insertWidget(min(self.layout_index, ly.count()), self.widget)
        self.widget.show()
        ly.update()
    def undo(self):
        ly = self.container._content_layout
        ly.removeWidget(self.widget)
        self.widget.setParent(self.canvas)
        self.canvas._canvas_widgets.insert(self.canvas_index, self.widget)
        self.widget.show()
        self.canvas._install_filter_recursive(self.widget)


class _ReparentBetweenContainersCmd(Command):
    """将控件从一个容器移到另一个容器"""
    def __init__(self, canvas, widget, old_container, new_container, old_idx, new_idx):
        self.canvas = canvas
        self.widget = widget
        self.old_container = old_container
        self.new_container = new_container
        self.old_idx = old_idx
        self.new_idx = new_idx
        self.description = f"容器间移动 {widget.objectName()}"
    def execute(self):
        old_ly = self.old_container._content_layout
        old_ly.removeWidget(self.widget)
        self.widget.setParent(self.new_container)
        new_ly = self.new_container._content_layout
        new_ly.insertWidget(min(self.new_idx, new_ly.count()), self.widget)
        self.widget.show()
        new_ly.update()
    def undo(self):
        new_ly = self.new_container._content_layout
        new_ly.removeWidget(self.widget)
        self.widget.setParent(self.old_container)
        old_ly = self.old_container._content_layout
        old_ly.insertWidget(self.old_idx, self.widget)
        self.widget.show()
        old_ly.update()


class HistoryManager:
    def __init__(self, max_size=100):
        self.undo_stack = []
        self.redo_stack = []
        self.max_size = max_size
    def push(self, cmd):
        cmd.execute()
        self.undo_stack.append(cmd)
        if len(self.undo_stack) > self.max_size:
            self.undo_stack.pop(0)
        self.redo_stack.clear()
    def undo(self):
        if self.undo_stack:
            cmd = self.undo_stack.pop()
            cmd.undo()
            self.redo_stack.append(cmd)
    def redo(self):
        if self.redo_stack:
            cmd = self.redo_stack.pop()
            cmd.execute()
            self.undo_stack.append(cmd)
    def can_undo(self):
        return bool(self.undo_stack)
    def can_redo(self):
        return bool(self.redo_stack)
