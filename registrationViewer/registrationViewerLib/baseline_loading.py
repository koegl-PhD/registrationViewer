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

    # Add path selector at the top
    pathLayout = qt.QHBoxLayout()
    pathLabel = qt.QLabel("Data directory:")
    pathLayout.addWidget(pathLabel)
    self.pathLineEdit = ctk.ctkPathLineEdit()
    self.pathLineEdit.setCurrentPath("/data/LungCT_preprocessed_new")
    pathLayout.addWidget(self.pathLineEdit)
    collapsibleLayout.addLayout(pathLayout)

    # Add control panel
    controlsLayout = qt.QHBoxLayout()

    # Add indices input
    indicesLabel = qt.QLabel("Indices:")
    self.indicesInput = qt.QLineEdit()
    self.indicesInput.setToolTip(
        "Enter comma-separated indices (e.g., 0,3,4).\nEmpty input means all")
    controlsLayout.addWidget(indicesLabel)
    controlsLayout.addWidget(self.indicesInput)

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
            load_data_from_dropped_folder(
                paths[0],  # Use first dropped folder
                self.moduleWidget.pathLineEdit.currentPath,
                self.moduleWidget.indicesInput.text.strip()
            )


def load_data_from_dropped_folder(dropped_folder_path: str,
                                  original_data_path: str,
                                  indices_text: str) -> None:
    """
    Load data from the specified directory structure
    """
    try:
        # First count how many groups we have
        deformationsPath = os.path.join(dropped_folder_path, "deformations")
        deformation_files = [f for f in os.listdir(deformationsPath)
                             if f.endswith(('.nii.gz'))]

        # srot the files
        deformation_files.sort()

        total_groups = len(deformation_files)

        # Determine which groups to load
        if indices_text == "":
            groups_to_load = list(range(total_groups))

        else:
            # Parse indices from text input
            try:
                indices: List[int] = [int(idx.strip())
                                      for idx in indices_text.split(',')]
                groups_to_load: List[int] = [
                    i for i in indices if 0 <= i < total_groups]

            except ValueError:
                slicer.util.errorDisplay(
                    "Invalid indices format. Please use comma-separated numbers.")
                return

        # Load the selected groups
        for i in groups_to_load:
            # Load displacement field
            filepath = os.path.join(deformationsPath, deformation_files[i])
            logging.info(f"Loading displacement field: {filepath}")
            slicer.util.loadTransform(filepath)

            # Get base name for matching deformed files
            base_name = deformation_files[i].replace(
                '_deformation_', '_deformed_')
            deformedPath = os.path.join(dropped_folder_path, "deformed")

            # Load volume
            volume_name = base_name
            volume_path = os.path.join(deformedPath, volume_name)
            if os.path.exists(volume_path):
                logging.info(f"Loading volume: {volume_path}")
                slicer.util.loadVolume(volume_path)

            # Load segmentation
            seg_name = base_name.replace('.nii.gz', '_seg.nii.gz')
            seg_path = os.path.join(deformedPath, seg_name)
            if os.path.exists(seg_path):
                logging.info(f"Loading segmentation: {seg_path}")
                slicer.util.loadSegmentation(seg_path)

            load_orignal_data(volume_name,
                              original_data_path)

        utils.collapse_all_segmentations()

    except Exception as e:
        logging.error(f"Error loading data: {str(e)}")
        slicer.util.errorDisplay(f"Error loading data: {str(e)}")


def load_orignal_data(file_name: str, data_path: str) -> None:
    file_name = file_name.replace('.nii.gz', '')
    moving_name, fixed_name = file_name.split('_deformed_to_')

    if data_path == "":
        return

    # find all files recrusively in data_path
    for file in glob.glob(data_path + f"/*/{moving_name}.nii.gz", recursive=True):
        if any([x in file.lower() for x in ['mask', 'seg', 'label']]):
            slicer.util.loadSegmentation(file)
        else:
            slicer.util.loadVolume(file)

    for file in glob.glob(data_path + f"/*/{fixed_name}.nii.gz", recursive=True):
        if any([x in file.lower() for x in ['mask', 'seg', 'label']]):
            slicer.util.loadSegmentation(file)
        else:
            slicer.util.loadVolume(file)
