"""mini_designer_split — 工业GUI设计器（拆分版）

基于 mini_designer.py (v19) 按功能模块拆分，行为完全一致。

使用方式:
    python -m mini_designer_split.main
    python mini_designer_split/main.py
"""

from .app import DesignerMainWindow, main
from .canvas import DesignerCanvas
from .config import (
    DEFAULT_QSS, DARK_QSS, ACTIVE_QSS, DARK_MODE,
    INDUSTRIAL_TEMPLATES, CUSTOM_WIDGETS,
)
from .commands import (
    Command, HistoryManager,
    AddWidgetCmd, DeleteWidgetCmd, MoveWidgetCmd, ResizeWidgetCmd,
    PropertyChangeCmd, BatchPropertyChangeCmd, BatchAlignCmd,
    ReorderWidgetCmd, ExtractWidgetCmd, InsertTemplateCmd,
)
from .codegen import CodeGenerator
from .panels import (
    WidgetToolbox, WidgetTreePanel, PropertyEditor,
    DataSimulatorPanel, UndoHistoryPanel,
)
from .dialogs import (
    CustomWidgetLoader, ThemeEditorDialog,
    CallbackEditorDialog, SignalSlotDialog,
)

__all__ = [
    "DesignerMainWindow", "DesignerCanvas",
    "DEFAULT_QSS", "DARK_QSS", "ACTIVE_QSS", "DARK_MODE",
    "INDUSTRIAL_TEMPLATES", "CUSTOM_WIDGETS",
    "Command", "HistoryManager",
    "AddWidgetCmd", "DeleteWidgetCmd", "MoveWidgetCmd", "ResizeWidgetCmd",
    "PropertyChangeCmd", "BatchPropertyChangeCmd", "BatchAlignCmd",
    "ReorderWidgetCmd", "ExtractWidgetCmd", "InsertTemplateCmd",
    "CodeGenerator",
    "WidgetToolbox", "WidgetTreePanel", "PropertyEditor",
    "DataSimulatorPanel", "UndoHistoryPanel",
    "CustomWidgetLoader", "ThemeEditorDialog",
    "CallbackEditorDialog", "SignalSlotDialog",
    "main",
]
