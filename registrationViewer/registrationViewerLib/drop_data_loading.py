import os
import glob
import logging

from typing import List

import ctk
import qt
import slicer
from slicer.ScriptedLoadableModule import *

import registrationViewerLib.utils as utils


def create_loading_ui(self) -> None:
    configCollapsible = ctk.ctkCollapsibleButton()
    configCollapsible.setMaximumWidth(500)  # Set maximum height to 400
    configCollapsible.text = "Load patient data"
    self.loadingCollapsible = configCollapsible
    self.layout.addWidget(configCollapsible)
    # configCollapsible.collapsed = True

    # Create collapsible layout
    collapsibleLayout = qt.QVBoxLayout(configCollapsible)

    # Add control panel
    controlsLayout = qt.QHBoxLayout()

    # Add stretch to push everything to the left
    controlsLayout.addStretch()

    # Add controls layout to collapsible layout
    controlWidget = qt.QWidget()
    controlWidget.setLayout(controlsLayout)
    collapsibleLayout.addWidget(controlWidget)

    # Add drop zone
    self.dropWidget = DropWidget(self)
    collapsibleLayout.addWidget(self.dropWidget)

    # Add final stretch to the collapsible layout
    collapsibleLayout.addStretch(1)


class DropWidget(qt.QFrame):
    def __init__(self, parent=None) -> None:
        # Get the widget's layout widget as the parent
        if parent is not None:
            parent_widget = parent.parent
        else:
            parent_widget = None
        qt.QFrame.__init__(self, parent_widget)

        self.setAcceptDrops(True)
        self.setStyleSheet(
            "QFrame { border: 2px dashed #999; border-radius: 5px; }")
        self.setMinimumHeight(100)

        # Create layout
        layout = qt.QVBoxLayout(self)
        label = qt.QLabel("Drop folder here")
        label.setAlignment(qt.Qt.AlignCenter)
        layout.addWidget(label)

        # Store reference to parent widget for accessing configuration
        self.moduleWidget = parent

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.accept()
            self.setStyleSheet(
                "QFrame { border: 2px dashed #44A; border-radius: 5px; background: #EEF; }")
        else:
            event.ignore()

    def dragLeaveEvent(self, _event) -> None:
        self.setStyleSheet(
            "QFrame { border: 2px dashed #999; border-radius: 5px; }")

    def dropEvent(self, event) -> None:
        self.setStyleSheet(
            "QFrame { border: 2px dashed #999; border-radius: 5px; }")
        paths = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.isdir(path):
                paths.append(path)

        if paths and self.moduleWidget:
            self.load_data_from_dropped_folder(
                paths[0],  # Use first dropped folder
            )

    def load_data_from_dropped_folder(self, dropped_folder_path: str) -> None:
        """
        Load data from the specified directory structure
        """

        try:
            slicer.progressWindow = slicer.util.createProgressDialog()
            slicer.progressWindow.show()
            slicer.progressWindow.activateWindow()
            slicer.progressWindow.setValue(0)
            slicer.progressWindow.setLabelText(
                f"Loading data...")
            slicer.app.processEvents()

            path_volume_fixed, path_volume_moving, \
                path_seg_fixed, path_seg_moving, \
                path_transform_fixed, path_transform_moving, \
                path_deformation = utils.get_paths_to_load(dropped_folder_path)

            if utils.update_progress_window(0, f"Loading fixed volume..."):
                node_volume_fixed = slicer.util.loadVolume(path_volume_fixed)
            else:
                return

            if utils.update_progress_window(10, f"Loading moving volume..."):
                node_volume_moving = slicer.util.loadVolume(path_volume_moving)
            else:
                return

            if utils.update_progress_window(20, f"Loading fixed segmentation..."):
                self.moduleWidget.node_seg_fixed = slicer.util.loadSegmentation(
                    path_seg_fixed)
            else:
                return

            if utils.update_progress_window(30, f"Loading moving segmentation..."):
                self.moduleWidget.node_seg_moving = slicer.util.loadSegmentation(
                    path_seg_moving)
            else:
                return

            if utils.update_progress_window(40, f"Loading fixed transform..."):
                self.moduleWidget.node_transform_fixed = slicer.util.loadTransform(
                    path_transform_fixed)
            else:
                return

            if utils.update_progress_window(50, f"Loading moving transform..."):
                self.moduleWidget.node_transform_moving = slicer.util.loadTransform(
                    path_transform_moving)
            else:
                return

            if utils.update_progress_window(60, f"Loading deformation..."):
                node_deformation = slicer.util.loadTransform(path_deformation)
            else:
                slicer.progressWindow.close()
                return

            self.moduleWidget.ui_sub_3.inputSelector_fixed.setCurrentNode(
                node_volume_fixed)
            self.moduleWidget.ui_sub_3.inputSelector_moving.setCurrentNode(
                node_volume_moving)
            self.moduleWidget.ui_sub_3.inputSelector_transformation.setCurrentNode(
                node_deformation)

            # set visibility of segmentation nodes
            utils.show_node_only_in_views(self.moduleWidget.node_seg_fixed,
                                          ['Red1', 'Green1', 'Yellow1'])
            utils.show_node_only_in_views(self.moduleWidget.node_seg_moving,
                                          ['Red2', 'Green2', 'Yellow2'])

            slicer.progressWindow.close()

        except Exception as e:
            slicer.progressWindow.close()
            logging.error(f"Error loading data: {str(e)}")
            slicer.util.errorDisplay(f"Error loading data: {str(e)}")
