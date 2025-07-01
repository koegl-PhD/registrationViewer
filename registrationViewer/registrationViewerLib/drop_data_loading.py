import logging
import os
import traceback

from typing import TYPE_CHECKING

import ctk
import qt
import slicer
from slicer.ScriptedLoadableModule import *

import registrationViewerLib.utils as utils

if TYPE_CHECKING:
    from ..registrationViewer import registrationViewerWidget


def create_loading_ui(self: "registrationViewerWidget") -> None:
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
    def __init__(self, parent: "registrationViewerWidget") -> None:
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

            self.moduleWidget.current_loaded_case_path = paths[0]

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

            path_registrations = "/home/koeglf/data/preprocess_again/SerielleCTs_nii_forHumans_registrations"

            path_volume_fixed, path_volume_moving, \
                path_seg_fixed, path_seg_moving, \
                path_transform_fixed, path_transform_moving, \
                path_deformation = utils.get_paths_to_load(
                    dropped_folder_path, path_registrations)

            if utils.update_progress_window(0, f"Loading fixed volume..."):
                node_volume_fixed = slicer.util.loadVolume(path_volume_fixed)
                name_volume_fixed = os.path.basename(
                    path_volume_fixed).replace(".nii.gz", "")
                node_volume_fixed.SetName(name_volume_fixed)
            else:
                return

            if utils.update_progress_window(10, f"Loading moving volume..."):
                node_volume_moving = slicer.util.loadVolume(path_volume_moving)
                name_volume_moving = os.path.basename(
                    path_volume_moving).replace(".nii.gz", "")
                node_volume_moving.SetName(name_volume_moving)
            else:
                return

            if utils.update_progress_window(20, f"Loading fixed segmentation..."):
                if path_seg_fixed:
                    self.moduleWidget.node_seg_fixed = slicer.util.loadSegmentation(
                        path_seg_fixed)
                    name_seg_fixed = os.path.basename(
                        path_seg_fixed).replace(".nii.gz", "")
                    self.moduleWidget.node_seg_fixed.SetName(name_seg_fixed)
            else:
                return

            if utils.update_progress_window(30, f"Loading moving segmentation..."):
                if path_seg_moving:
                    self.moduleWidget.node_seg_moving = slicer.util.loadSegmentation(
                        path_seg_moving)
                    name_seg_moving = os.path.basename(
                        path_seg_moving).replace(".nii.gz", "")
                    self.moduleWidget.node_seg_moving.SetName(name_seg_moving)
            else:
                return

            if utils.update_progress_window(40, f"Loading fixed transform..."):
                if path_transform_fixed is None:
                    self.moduleWidget.node_transform_fixed = slicer.mrmlScene.AddNewNodeByClass(
                        "vtkMRMLLinearTransformNode")
                    print(f"No fixed transform found")
                else:
                    self.moduleWidget.node_transform_fixed = slicer.util.loadTransform(
                        path_transform_fixed)
                    name_transform_fixed = os.path.basename(
                        path_transform_fixed).replace(".nii.gz", "")
                    self.moduleWidget.node_transform_fixed.SetName(
                        name_transform_fixed)
            else:
                return

            if utils.update_progress_window(50, f"Loading moving transform..."):
                if path_transform_moving is None:
                    self.moduleWidget.node_transform_moving = slicer.mrmlScene.AddNewNodeByClass(
                        "vtkMRMLLinearTransformNode")
                    print(f"No moving transform found")
                else:
                    self.moduleWidget.node_transform_moving = slicer.util.loadTransform(
                        path_transform_moving)
                    name_transform_moving = os.path.basename(
                        path_transform_moving).replace(".h5", "")
                    self.moduleWidget.node_transform_moving.SetName(
                        name_transform_moving)
            else:
                return

            if utils.update_progress_window(60, f"Loading deformation..."):
                if path_deformation is None:
                    node_deformation = slicer.mrmlScene.AddNewNodeByClass(
                        "vtkMRMLLinearTransformNode")
                    print(f"No deformation found")
                else:
                    node_deformation = slicer.util.loadTransform(
                        path_deformation)
                    name_deformation = os.path.basename(
                        path_deformation).replace(".nii.gz", "")
                    node_deformation.SetName(name_deformation)
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

            utils.set_orthogonal_views(
                self.moduleWidget.views_first_row + self.moduleWidget.views_second_row)

            slicer.progressWindow.close()

        except Exception as e:
            error_details = traceback.format_exc()
            slicer.progressWindow.close()
            logging.error(f"Error loading data: {str(e)}/n{error_details}")
            slicer.util.errorDisplay(
                f"Error loading data: {str(e)}/n{error_details}")
