"""mini_designer_split/dialogs/__init__.py"""
from .widget_loader import CustomWidgetLoader
from .theme_editor import ThemeEditorDialog
from .callback_editor import CallbackEditorDialog
from .signal_slot import SignalSlotDialog

__all__ = [
    "CustomWidgetLoader",
    "ThemeEditorDialog",
    "CallbackEditorDialog",
    "SignalSlotDialog",
]
