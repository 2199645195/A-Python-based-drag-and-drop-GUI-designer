"""mini_designer_split/panels/__init__.py"""
from .toolbox import WidgetToolbox
from .widget_tree import WidgetTreePanel
from .properties import PropertyEditor
from .simulator import DataSimulatorPanel
from .undo_history import UndoHistoryPanel

__all__ = [
    "WidgetToolbox",
    "WidgetTreePanel",
    "PropertyEditor",
    "DataSimulatorPanel",
    "UndoHistoryPanel",
]
