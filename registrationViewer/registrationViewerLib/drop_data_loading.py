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
    configCollapsible.text = "Folder Structure Configuration"
    self.layout.addWidget(configCollapsible)

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

        utils.collapse_all_segmentations()

    def load_data_from_dropped_folder(self, dropped_folder_path: str) -> None:
        """
        Load data from the specified directory structure
        """

        try:
            dropped_folder_path = "/home/koeglf/data/registrationStudy/SerielleCTs_nii_forHumans/0e5fp8GltvE/"

            path_experiment = os.path.join(
                "/", *dropped_folder_path.split("/")[:-3])

            studies = [f for f in os.listdir(os.path.join(dropped_folder_path, 'raw'))
                       if os.path.isdir(os.path.join(dropped_folder_path, 'raw', f))]

            path_volume_fixed = glob.glob(os.path.join(
                dropped_folder_path, 'raw', studies[1], '*.nii.gz'))[0]
            path_volume_moving = glob.glob(os.path.join(
                dropped_folder_path, 'raw', studies[0], '*.nii.gz'))[0]

            name_fixed = os.path.basename(
                path_volume_fixed).replace(".nii.gz", "")
            name_moving = os.path.basename(
                path_volume_moving).replace(".nii.gz", "")

            path_transform_fixed = glob.glob(os.path.join(
                dropped_folder_path, 'preprocessed', studies[1], '*.h5'))[0]
            path_transform_moving = glob.glob(os.path.join(
                dropped_folder_path, 'preprocessed', studies[0], '*.h5'))[0]

            paths_deformations = sorted(glob.glob(os.path.join(
                path_experiment, 'SerielleCTs_nii_forHumans_registrations', 'BSplineNiftyReg', '*', 'deformations', '*.nii.gz')))

            path_deformation = [
                x for x in paths_deformations if name_fixed in x and name_moving in x]

            assert len(path_deformation) == 1

            path_deformation = path_deformation[0]

            if not os.path.exists(path_volume_fixed):
                raise Exception(f"Volume fixed path does not exist: {path_volume_fixed}")  # nopep8
            if not os.path.exists(path_volume_moving):
                raise Exception(f"Volume moving path does not exist: {path_volume_moving}")  # nopep8
            if not os.path.exists(path_transform_fixed):
                raise Exception(f"Transform fixed path does not exist: {path_transform_fixed}")  # nopep8
            if not os.path.exists(path_transform_moving):
                raise Exception(f"Transform moving path does not exist: {path_transform_moving}")  # nopep8
            if not os.path.exists(path_deformation):
                raise Exception(f"Deformation path does not exist: {path_deformation}")  # nopep8

            node_volume_fixed = slicer.util.loadVolume(
                path_volume_fixed)
            node_volume_moving = slicer.util.loadVolume(
                path_volume_moving)
            node_transform_fixed = slicer.util.loadTransform(
                path_transform_fixed)
            node_transform_moving = slicer.util.loadTransform(
                path_transform_moving)
            node_deformation = slicer.util.loadTransform(
                path_deformation)

            # apply transforms to volumes
            utils.apply_and_harden_transform_to_node(
                node_volume_fixed, node_transform_fixed)
            slicer.mrmlScene.RemoveNode(node_transform_fixed)

            utils.apply_and_harden_transform_to_node(
                node_volume_moving, node_transform_moving)
            slicer.mrmlScene.RemoveNode(node_transform_moving)

            self.moduleWidget.ui.inputSelector_fixed.setCurrentNode(
                node_volume_fixed)
            self.moduleWidget.ui.inputSelector_moving.setCurrentNode(
                node_volume_moving)

            self.moduleWidget.ui.inputSelector_transformation.setCurrentNode(
                node_deformation)

        except Exception as e:
            logging.error(f"Error loading data: {str(e)}")
            slicer.util.errorDisplay(f"Error loading data: {str(e)}")
