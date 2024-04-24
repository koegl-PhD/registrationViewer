from typing import Tuple, Callable

import qt
import slicer

def create_shortcuts(*shortcuts: Tuple[str, Callable]) -> None:
    """
    Creates and initializes shortcuts for the main window.
    """
        
    for (shortcutKey, callback) in shortcuts:
        shortcut = qt.QShortcut(slicer.util.mainWindow())
        shortcut.setKey(qt.QKeySequence(shortcutKey))
        shortcut.connect('activated()', callback)
