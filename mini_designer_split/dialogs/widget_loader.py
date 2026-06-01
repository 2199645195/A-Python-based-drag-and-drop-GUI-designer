"""mini_designer_split/dialogs/widget_loader.py — 自定义控件加载器"""

import os
import importlib
import inspect
import sys

from PySide6.QtWidgets import QWidget, QFrame, QGroupBox


class CustomWidgetLoader:
    """动态加载自定义控件文件"""

    @staticmethod
    def load_from_file(filepath):
        """从 .py 文件加载 QWidget 子类"""
        results = []
        filepath = os.path.abspath(filepath)
        if not os.path.isfile(filepath):
            print(f"[CustomWidgetLoader] 文件不存在: {filepath}")
            return results
        dirname = os.path.dirname(filepath)
        basename = os.path.basename(filepath)
        modname = os.path.splitext(basename)[0]
        if dirname not in sys.path:
            sys.path.insert(0, dirname)
        try:
            spec = importlib.util.spec_from_file_location(modname, filepath)
            if not spec or not spec.loader:
                return results
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            for attr_name in dir(mod):
                obj = getattr(mod, attr_name)
                if (inspect.isclass(obj) and issubclass(obj, QWidget)
                        and obj is not QWidget
                        and obj is not QFrame
                        and obj is not QGroupBox
                        and not attr_name.startswith("_")
                        and obj.__module__ == mod.__name__):
                    display = getattr(obj, '_display_name', None) or attr_name
                    results.append((display, obj, {}, filepath))
        except Exception as e:
            print(f"[CustomWidgetLoader] 加载失败 {filepath}: {e}")
        return results

    @staticmethod
    def register_widgets(filepaths):
        from ..config import CUSTOM_WIDGETS
        CUSTOM_WIDGETS.clear()
        for fp in filepaths:
            CUSTOM_WIDGETS.extend(CustomWidgetLoader.load_from_file(fp))
        return len(CUSTOM_WIDGETS)
