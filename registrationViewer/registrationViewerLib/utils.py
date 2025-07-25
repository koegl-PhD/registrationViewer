from collections import defaultdict
from enum import Enum
import glob
import json
import logging
import os
import random
import tempfile
import traceback
from typing import TYPE_CHECKING

from typing import Dict, Tuple, Callable, List, Optional

import qt
import slicer
from slicer import qMRMLSliceWidget
import vtk

from registrationViewerLib import texts


if TYPE_CHECKING:
    from ..registrationViewer import registrationViewerWidget


class TransformType(Enum):
    NONE = "none"
    LINEAR = "linear"
    NONLINEAR = "nonlinear"


class Colors(Enum):
    BLUE = (111/255, 184/255, 210/255)
    GREEN = (47/255, 202/255, 36/255)
    YELLOW = (244/255, 214/255, 49/255)
    RED = (1.0, 0, 0)


def update_progress_window(progress: Optional[int] = None, message: Optional[str] = None) -> bool:
    if slicer.progressWindow.wasCanceled:
        slicer.progressWindow.close()
        return False

    if progress is not None:
        slicer.progressWindow.setValue(progress)

    if message is not None:
        slicer.progressWindow.setLabelText(message)

    return True


def create_shortcuts(*shortcuts: Tuple[str, Callable]) -> None:
    """
    Creates and initializes shortcuts for the main window.
    """

    for (shortcutKey, callback) in shortcuts:
        shortcut = qt.QShortcut(slicer.util.mainWindow())
        shortcut.setKey(qt.QKeySequence(shortcutKey))
        shortcut.connect('activated()', callback)


def set_window_level_and_threshold(node: slicer.vtkMRMLScalarVolumeNode,
                                   window: float,
                                   level: float,
                                   threshold: Tuple[float, float]) -> None:

    set_window_level(node, window, level)
    set_threshold(node, threshold)


def set_window_level(node: slicer.vtkMRMLScalarVolumeNode,
                     window: float,
                     level: float) -> None:

    if not node:
        return

    displayNode = node.GetDisplayNode()

    if not displayNode:
        return

    displayNode.AutoWindowLevelOff()
    displayNode.SetWindow(window)
    displayNode.SetLevel(level)


def set_threshold(node: slicer.vtkMRMLScalarVolumeNode,
                  threshold: Tuple[float, float]) -> None:

    if not node:
        return

    displayNode = node.GetDisplayNode()

    if not displayNode:
        return

    displayNode.ApplyThresholdOn()
    displayNode.SetThreshold(threshold[0], threshold[1])


def set_orthogonal_views(views: List[str]) -> None:
    """
    This has to be used when a volume has a non-standard rientation
    """

    for view in views:
        try:
            slice_node = slicer.app.layoutManager().sliceWidget(
                view).sliceLogic().GetSliceNode()

            if "Red" in view:
                slice_node.SetOrientation('Axial')
            elif "Green" in view:
                slice_node.SetOrientation('Coronal')
            elif "Yellow" in view:
                slice_node.SetOrientation('Sagittal')
            else:
                raise ValueError(f"Unknown view: {view}")

        except Exception as e:
            error_details = traceback.format_exc()
            log(logging.ERROR, LogType.INTERNAL,
                f"Could not set orthogonal view for {view}: {str(e)}\n{error_details}")


def get_cursor_view_name() -> str:
    """
    Get the name of the view where the cursor is currently located.
    """
    node_crosshair = slicer.util.getNode("Crosshair")

    if node_crosshair is None:
        return ""

    position = node_crosshair.GetCursorPositionXYZ([0]*3)

    if position is not None:
        return position.GetName()

    return ""
