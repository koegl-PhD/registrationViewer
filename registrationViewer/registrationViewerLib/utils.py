from enum import Enum
import glob
import json
import logging
import os
import tempfile
import traceback
from typing import TYPE_CHECKING

from typing import Dict, Tuple, Callable, List, Optional

import qt
import slicer
from slicer import qMRMLSliceWidget
import vtk

from registrationViewerLib import texts
from registrationViewerLib.custom_logging import log, LogType


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


class ArrowKeyFilter(qt.QObject):
    def __init__(self) -> None:
        """Initialize key press tracking."""

        super().__init__()
        self._pressed: dict[int, bool] = {}

    def eventFilter(self, obj: qt.QObject, event: qt.QEvent) -> bool:
        """Log 'left'/'right' once per physical key press."""

        if event.type() == qt.QEvent.KeyPress:

            key: int = event.key()

            if key in (qt.Qt.Key_Left, qt.Qt.Key_Right) and not self._pressed.get(key, False):

                direction = "left" if key == qt.Qt.Key_Left else "right"
                log(logging.INFO, LogType.U_BUTTON,
                    f"Key_Arrow ~ {get_active_slice_view()} ~ {direction}")

                self._pressed[key] = True

        elif event.type() == qt.QEvent.KeyRelease:

            key: int = event.key()

            if key in (qt.Qt.Key_Left, qt.Qt.Key_Right):
                self._pressed[key] = False

        return False


def center_on_point(point: slicer.vtkMRMLMarkupsFiducialNode,
                    view_group: Optional[int] = None) -> None:

    if point is None:
        return

    position = [0, 0, 0]
    point.GetNthControlPointPositionWorld(0, position)

    view = view_group if view_group is not None else 1

    slicer.modules.markups.logic().JumpSlicesToLocation(position[0],
                                                        position[1],
                                                        position[2],
                                                        False,
                                                        view)


def get_paths_to_load(path_case_folder: str):
    path_nii = os.path.dirname(path_case_folder)
    name_nii_folder = os.path.basename(path_nii)
    path_experiment = os.path.dirname(path_nii)

    studies = sorted([f for f in os.listdir(os.path.join(path_case_folder, 'raw'))
                      if os.path.isdir(os.path.join(path_case_folder, 'raw', f))])

    path_volume_fixed = [
        file for file in glob.glob(os.path.join(path_case_folder, 'raw', studies[1], '*.nii.gz'))
        if not file.endswith('_seg.nii.gz')
    ][0]

    path_volume_moving = [
        file for file in glob.glob(os.path.join(path_case_folder, 'raw', studies[0], '*.nii.gz'))
        if not file.endswith('_seg.nii.gz')
    ][0]

    path_seg_fixed = glob.glob(os.path.join(
        path_case_folder, 'raw', studies[1], '*_seg.nii.gz'))
    path_seg_fixed = None if len(path_seg_fixed) == 0 else path_seg_fixed[0]
    path_seg_moving = glob.glob(os.path.join(
        path_case_folder, 'raw', studies[0], '*_seg.nii.gz'))
    path_seg_moving = None if len(path_seg_moving) == 0 else path_seg_moving[0]

    name_fixed = os.path.basename(
        path_volume_fixed).replace(".nii.gz", "")
    name_moving = os.path.basename(
        path_volume_moving).replace(".nii.gz", "")

    path_transform_fixed = glob.glob(os.path.join(
        path_case_folder, 'preprocessed', studies[1], '*.h5'))
    path_transform_fixed = None if len(
        path_transform_fixed) == 0 else path_transform_fixed[0]
    path_transform_moving = glob.glob(os.path.join(
        path_case_folder, 'preprocessed', studies[0], '*.h5'))
    path_transform_moving = None if len(
        path_transform_moving) == 0 else path_transform_moving[0]

    path_niftyreg = os.path.join(
        path_experiment, f"{name_nii_folder}_registrations", 'BSplineNiftyReg')

    paths_deformations = sorted(glob.glob(os.path.join(
        path_niftyreg, '*', 'deformations', '*.nii.gz')))
    path_deformation = [
        x for x in paths_deformations if name_fixed in x and name_moving in x]

    if len(path_deformation) != 1:
        path_deformation = None
        print("No deformation found")
    else:
        path_deformation = path_deformation[0]

    if not os.path.exists(path_volume_fixed):
        print(path_volume_fixed)
        raise Exception(f"Volume fixed path does not exist: {path_volume_fixed}")  # nopep8
    if not os.path.exists(path_volume_moving):
        print(path_volume_moving)
        raise Exception(f"Volume moving path does not exist: {path_volume_moving}")  # nopep8
    if path_seg_fixed and not os.path.exists(path_seg_fixed):
        print(path_seg_fixed)
        raise Exception(
            f"Segmentation fixed path does not exist: {path_seg_fixed}")
    if path_seg_moving and not os.path.exists(path_seg_moving):
        print(path_seg_moving)
        raise Exception(
            f"Segmentation moving path does not exist: {path_seg_moving}")
    if path_transform_fixed and not os.path.exists(path_transform_fixed):
        print(path_transform_fixed)
        raise Exception(f"Transform fixed path does not exist: {path_transform_fixed}")  # nopep8
    if path_transform_moving and not os.path.exists(path_transform_moving):
        print(path_transform_moving)
        raise Exception(f"Transform moving path does not exist: {path_transform_moving}")  # nopep8
    if path_deformation and not os.path.exists(path_deformation):
        print(path_deformation)
        raise Exception(f"Deformation path does not exist: {path_deformation}")  # nopep8

    return path_volume_fixed, path_volume_moving, \
        path_seg_fixed, path_seg_moving, \
        path_transform_fixed, path_transform_moving, \
        path_deformation


def show_progressbar(ui, idx: int, initial: int, maximum: int):

    progress_bar = getattr(ui, f"progress_bar_{idx}")

    progress_bar.setVisible(True)
    progress_bar.setValue(initial)
    progress_bar.setMaximum(maximum)

    getattr(ui, f"progress_label_{idx}").setVisible(True)

    return progress_bar


def set_up_progress_window(label: str, initial_value: int = 0) -> None:

    slicer.progressWindow = slicer.util.createProgressDialog()
    slicer.progressWindow.show()
    slicer.progressWindow.activateWindow()
    slicer.progressWindow.setValue(initial_value)
    slicer.progressWindow.setLabelText(label)
    slicer.app.processEvents()


def update_progress_window(progress: Optional[int] = None, message: Optional[str] = None) -> bool:
    if slicer.progressWindow.wasCanceled:
        slicer.progressWindow.close()
        return False

    if progress is not None:
        slicer.progressWindow.setValue(progress)

    if message is not None:
        slicer.progressWindow.setLabelText(message)

    return True


def hide_all_points_except_current_point(self: "registrationViewerWidget") -> None:

    for patient_name, patient_points in self.study_node_groundtruth_points.items():

        # for not current patient hide all
        if patient_name != self.current_patient_name:
            for current_task, point in patient_points.items():
                if point is not None:
                    point.SetDisplayVisibility(False)

        # for current patient hide all except current task
        else:
            for current_task, point in patient_points.items():
                if point is not None and current_task != self.current_task:
                    point.SetDisplayVisibility(False)
                if point is not None and current_task == self.current_task:
                    point.SetDisplayVisibility(True)


def normalize_intensity(data):

    return (data - data.min()) / (data.max() - data.min())


def apply_black_to_white_lookup_table(volume_node):
    import vtk
    import numpy as np

    # Create a vtkLookupTable for custom colors
    lookup_table = vtk.vtkLookupTable()
    lookup_table.SetNumberOfTableValues(256)  # 256 colors
    lookup_table.SetRange(-1.0, 1.0)
    lookup_table.Build()

    # Populate the lookup table with logarithmic scaling
    for i in range(256):
        value = i / 255.0
        intensity = abs(value - 0.5) * 2
        lookup_table.SetTableValue(i,
                                   intensity,
                                   intensity,
                                   intensity,
                                   1.0)

    # Create a vtkMRMLColorTableNode and set the lookup table
    color_table_node = slicer.mrmlScene.AddNewNodeByClass(
        "vtkMRMLColorTableNode", "BlackToWhiteColorTable")
    color_table_node.SetAndObserveLookupTable(lookup_table)

    # Get the display node for the volume
    display_node = volume_node.GetDisplayNode()
    if not display_node:
        display_node = slicer.mrmlScene.AddNewNodeByClass(
            "vtkMRMLScalarVolumeDisplayNode")
        volume_node.SetAndObserveDisplayNodeID(display_node.GetID())

    # Assign the color table to the display node
    display_node.SetAndObserveColorNodeID(color_table_node.GetID())


def set_ui_simplification(self: "registrationViewerWidget") -> None:
    """
    Simplifies the UI by hiding the toolbar, module panel etc.
    """

    value = not self.ui_is_simple

    # slicer.util.setMenuBarsVisible(value)

    # slicer.util.setToolbarsVisible(value)

    # hide help section
    slicer.util.setModuleHelpSectionVisible(value)

    # hide the module panel
    slicer.util.setModulePanelTitleVisible(value)

    # hide data probe
    slicer.util.setDataProbeVisible(value)

    # hi ebar at the botto of the window
    slicer.util.setStatusBarVisible(value)

    # dont't uncomment
    # slicer.util.setViewControllersVisible(value)
    layoutManager = slicer.app.layoutManager()
    for view in self.views_all:
        slice_view = slicer.app.layoutManager().sliceWidget(view).sliceView()
        controller = layoutManager.sliceWidget(view).sliceController()

        controller.fitToWindowToolButton().setVisible(value)
        controller.pinButton().setVisible(value)
        controller.setShowMaximizeViewButton(value)

        controller.setMinimumHeight(25)

        if value is False:
            color = "white"
        else:
            color = "black"
        for child in controller.findChildren(qt.QWidget):
            if isinstance(child, (qt.QLabel, qt.QPushButton, qt.QComboBox, qt.QToolButton)):
                child.setStyleSheet(f"color: {color};")

        slider = controller.sliceOffsetSlider()
        slider.setStyleSheet("""
            QSlider::groove:horizontal {
                background: lightgray;
                height: 4px;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: rgb(12, 148, 194);  /* filled part (left of handle) */
                height: 4px;
                border-radius: 3px;
            }
            QSlider::add-page:horizontal {
                background: lightgray;  /* unfilled part (right of handle) */
                height: 4px;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: white;
                border: 1px solid lightgray;
                width: 7px;
                height: 12px;
                margin: -3px 0;
                border-radius: 2px;
            }
            """)

        slice_view.cornerAnnotation().SetMaximumFontSize(0)

    slice_view.forceRender()
    slicer.app.processEvents()

    slicer.modules.registrationviewer.widgetRepresentation(
    ).self().reloadCollapsibleButton.visible = value

    # hide python console
    # slicer.util.setPythonConsoleVisible(value)


def print_affine_matrix(transformNode):
    """
    Prints the affine matrix of a vtkMRMLLinearTransformNode.

    Args:
        transformNode (vtkMRMLLinearTransformNode): The transform node whose matrix is to be printed.
    """
    if not transformNode.IsA("vtkMRMLLinearTransformNode"):
        print("Error: The provided node is not a vtkMRMLLinearTransformNode.")
        return

    # Retrieve the transformation matrix
    matrix = vtk.vtkMatrix4x4()
    transformNode.GetMatrixTransformToParent(matrix)

    # Print the matrix in a readable format
    print("Affine matrix:")
    for row in range(4):
        print("  ", [matrix.GetElement(row, col) for col in range(4)])


def create_shortcuts(*shortcuts: Tuple[str, Callable]) -> None:
    """
    Creates and initializes shortcuts for the main window.
    """

    for (shortcutKey, callback) in shortcuts:
        shortcut = qt.QShortcut(slicer.util.mainWindow())
        shortcut.setKey(qt.QKeySequence(shortcutKey))
        shortcut.connect('activated()', callback)


def temp_load_data(self):
    node_volume_fixed = slicer.util.loadVolume(
        self.resourcePath("Data/lung/fixed.nii.gz"))
    node_volume_moving = slicer.util.loadVolume(
        self.resourcePath("Data/lung/moving.nii.gz"))
    node_transformation = slicer.util.loadTransform(
        self.resourcePath("Data/lung/moving_deformation_to_fixed.nii.gz"))

    node_volume_fixed.SetName('volume_fixed')
    node_volume_moving.SetName('volume_moving')
    node_transformation.SetName('displacement_field')

    # add to the scene
    slicer.mrmlScene.AddNode(node_volume_fixed)
    slicer.mrmlScene.AddNode(node_volume_moving)
    slicer.mrmlScene.AddNode(node_transformation)

    # set the nodes
    self.ui_sub_3.inputSelector_fixed.setCurrentNode(node_volume_fixed)
    self.ui_sub_3.inputSelector_moving.setCurrentNode(node_volume_moving)
    self.ui_sub_3.inputSelector_transformation.setCurrentNode(
        node_transformation)


def apply_and_harden_transform_to_node(node_target: slicer.vtkMRMLNode,
                                       node_transform: slicer.vtkMRMLTransformNode,
                                       invert: bool = False) -> None:
    """
    Applies the given transform to the target node and hardens it.

    @param node_target: The target node.
    @param node_transform: The transform node.
    """

    if not node_transform or not node_target:
        return

    if invert:
        node_target.ApplyTransform(node_transform.GetTransformFromParent())
    else:
        node_target.ApplyTransform(node_transform.GetTransformToParent())


def normalize_node(node: slicer.vtkMRMLScalarVolumeNode) -> slicer.vtkMRMLScalarVolumeNode:

    array = slicer.util.arrayFromVolume(node)
    array = normalize_intensity(array)

    slicer.util.updateVolumeFromArray(node, array)

    return node


def resample_node_to_reference_node(node_input: slicer.vtkMRMLScalarVolumeNode,
                                    node_reference: slicer.vtkMRMLScalarVolumeNode) -> None:

    params = {
        "inputVolume": node_input,
        "outputVolume": node_input,
        "referenceVolume": node_reference,
        "interpolationType": "linear"
    }

    slicer.cli.runSync(slicer.modules.resamplescalarvectordwivolume,
                       None,
                       params,
                       update_display=False)


def collapse_all_segmentations() -> None:

    subjectHierarchyNode = slicer.mrmlScene.GetSubjectHierarchyNode()

    if subjectHierarchyNode:
        itemIDs = vtk.vtkIdList()
        subjectHierarchyNode.GetItemChildren(
            subjectHierarchyNode.GetSceneItemID(), itemIDs, True)

        for i in range(itemIDs.GetNumberOfIds()):
            itemID = itemIDs.GetId(i)
            node = subjectHierarchyNode.GetItemDataNode(itemID)
            if node and node.IsA("vtkMRMLSegmentationNode"):
                subjectHierarchyNode.SetItemExpanded(itemID, False)
                # turn off visibility
                node.SetDisplayVisibility(False)


def set_all_segmentation_visibility(visibility: bool) -> None:
    subjectHierarchyNode = slicer.mrmlScene.GetSubjectHierarchyNode()

    if subjectHierarchyNode:
        itemIDs = vtk.vtkIdList()
        subjectHierarchyNode.GetItemChildren(
            subjectHierarchyNode.GetSceneItemID(), itemIDs, True)

        for i in range(itemIDs.GetNumberOfIds()):
            itemID = itemIDs.GetId(i)
            node = subjectHierarchyNode.GetItemDataNode(itemID)
            if node and node.IsA("vtkMRMLSegmentationNode"):
                node.SetDisplayVisibility(visibility)


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


def show_warning_popup(title: str,
                       content: str):
    msgBox = qt.QMessageBox()
    msgBox.setIcon(qt.QMessageBox.Warning)
    msgBox.setWindowTitle(title)
    msgBox.setText(content)
    msgBox.setStandardButtons(qt.QMessageBox.Ok | qt.QMessageBox.Cancel)
    msgBox.setDefaultButton(qt.QMessageBox.Cancel)

    response = msgBox.exec_()

    if response == qt.QMessageBox.Ok:
        return True
    else:
        return False


def show_question_popup(content: str) -> bool:
    msgBox = qt.QMessageBox()
    msgBox.setIcon(qt.QMessageBox.Question)
    msgBox.setText(content)
    msgBox.setStandardButtons(qt.QMessageBox.Yes | qt.QMessageBox.No)
    msgBox.setDefaultButton(qt.QMessageBox.No)

    response = msgBox.exec_()

    if response == qt.QMessageBox.Yes:
        return True
    else:
        return False


def show_info_popup(title: str, content: str) -> None:
    msgBox = qt.QMessageBox()
    msgBox.setIcon(qt.QMessageBox.Information)
    msgBox.setWindowTitle(title)
    msgBox.setText(content)
    msgBox.setStandardButtons(qt.QMessageBox.Ok)  # Only "OK" button
    msgBox.exec_()


def show_fullscreen_popup_with_callback(
    title: str,
    content: str,
    center_text: bool = False,
    text_size: int = 24,
    on_ok: Callable[[], None] = lambda: None
) -> bool:
    dialog = qt.QDialog(slicer.util.mainWindow())
    dialog.setWindowTitle(title)
    dialog.setModal(True)
    layout = qt.QVBoxLayout(dialog)

    label = qt.QLabel(content)
    label.setWordWrap(True)
    if center_text:
        label.setAlignment(qt.Qt.AlignCenter)  # or AlignHCenter | AlignTop
    label.setStyleSheet(f"font-size: {text_size}px; padding: 30px;")
    layout.addWidget(label)

    button_box = qt.QDialogButtonBox(qt.QDialogButtonBox.Ok)
    button_box.button(qt.QDialogButtonBox.Ok).setStyleSheet(
        "font-size: 20px; padding: 10px 30px;")
    layout.addWidget(button_box)

    def accept():
        on_ok()
        dialog.accept()

    button_box.accepted.connect(accept)

    dialog.setWindowState(qt.Qt.WindowFullScreen)
    return dialog.exec_() == qt.QDialog.Accepted


def show_fullscreen_block(
    title: str,
    content: str,
    center_text: bool = False,
    text_size: int = 24
) -> qt.QDialog:
    """
    Show a non-blocking fullscreen popup and return its dialog for external closing.

    To close, call .close() on the returned object
    """
    dialog = qt.QDialog(slicer.util.mainWindow())
    dialog.setWindowTitle(title)
    dialog.setModal(False)
    layout = qt.QVBoxLayout(dialog)

    label = qt.QLabel(content)
    label.setWordWrap(True)
    if center_text:
        label.setAlignment(qt.Qt.AlignCenter)
    label.setStyleSheet(f"font-size: {text_size}px; padding: 30px;")
    layout.addWidget(label)

    dialog.setWindowState(qt.Qt.WindowFullScreen)
    dialog.show()

    return dialog


def show_fullscreen_popup_with_image(
        image_path: str,
        title: str,
        center_image: bool = True,
        on_ok: Callable[[], None] = lambda: None
) -> None:
    """Show a message box with an image instead of text."""
    dialog = qt.QDialog(slicer.util.mainWindow())
    dialog.setWindowTitle(title)
    dialog.setModal(True)
    layout = qt.QVBoxLayout(dialog)

    # Image
    label = qt.QLabel()
    pixmap = qt.QPixmap(image_path)

    screen_geometry = qt.QApplication.desktop().availableGeometry()
    max_width = screen_geometry.width() * 0.6
    max_height = screen_geometry.height() * 0.6

    scaled_pixmap = pixmap.scaled(
        max_width, max_height, qt.Qt.KeepAspectRatio, qt.Qt.SmoothTransformation)
    label.setPixmap(scaled_pixmap)

    if center_image:
        label.setAlignment(qt.Qt.AlignCenter)

    layout.addWidget(label)

    # OK Button
    button_box = qt.QDialogButtonBox(qt.QDialogButtonBox.Ok)
    button_box.button(qt.QDialogButtonBox.Ok).setStyleSheet(
        "font-size: 24px; padding: 12px 24px;")
    layout.addWidget(button_box)

    def handle_accept():
        on_ok()
        dialog.accept()

    button_box.accepted.connect(handle_accept)

    dialog.setWindowState(qt.Qt.WindowFullScreen)
    return dialog.exec_() == qt.QDialog.Accepted


def has_control_point_with_name(node_fiducial: slicer.vtkMRMLMarkupsFiducialNode,
                                name: str) -> bool:

    if node_fiducial is None:
        return False

    for i in range(node_fiducial.GetNumberOfControlPoints()):
        if node_fiducial.GetNthControlPointLabel(i) == name:
            return True

    return False


def get_control_point_idx_by_name(node_fiducial: slicer.vtkMRMLMarkupsFiducialNode,
                                  name: str) -> int:

    for i in range(node_fiducial.GetNumberOfControlPoints()):
        if node_fiducial.GetNthControlPointLabel(i) == name:
            return i

    return -1


def remove_control_point_by_name(node_fiducial: slicer.vtkMRMLMarkupsFiducialNode,
                                 name: str) -> None:

    for i in range(node_fiducial.GetNumberOfControlPoints()):
        if node_fiducial.GetNthControlPointLabel(i) == name:
            node_fiducial.RemoveNthControlPoint(i)
            return


def show_node_only_in_views(node, views: List[str]) -> None:

    if node is None:
        return

    disp_node = node.GetDisplayNode()
    if not disp_node:
        return

    disp_node.RemoveAllViewNodeIDs()

    for view in views:
        slice_node = slicer.app.layoutManager().sliceWidget(view).mrmlSliceNode()
        disp_node.AddViewNodeID(slice_node.GetID())


def get_range_of_values(node: slicer.vtkMRMLScalarVolumeNode) -> Tuple[float, float]:
    array = slicer.util.arrayFromVolume(node)
    return array.min(), array.max()


def serialise_markup(node: slicer.vtkMRMLMarkupsFiducialNode) -> Dict[str, Tuple[float, ...]]:

    with tempfile.NamedTemporaryFile(mode='w', suffix=".mrk.json") as file:
        slicer.util.saveNode(node, file.name)
        file.flush()

        with open(file.name, "r") as f:
            data = json.load(f)

    position = data["markups"][0]["controlPoints"][0]["position"]
    orientation = data["markups"][0]["controlPoints"][0]["orientation"]

    return {"position": position, "orientation": orientation}


def de_serialise_markup(data: Dict[str, Tuple[float, ...]]) -> slicer.vtkMRMLMarkupsFiducialNode:

    full_json = {
        "@schema": "https://raw.githubusercontent.com/slicer/slicer/master/Modules/Loadable/Markups/Resources/Schema/markups-schema-v1.0.3.json#",
        "markups": [
            {
                "type": "Fiducial",
                "coordinateSystem": "LPS",
                "coordinateUnits": "mm",
                "locked": False,
                "fixedNumberOfControlPoints": False,
                "labelFormat": "%N-%d",
                "lastUsedControlPointNumber": 1,
                "controlPoints": [
                    {
                        "id": "1",
                        "label": "p",
                        "description": "",
                        "associatedNodeID": "",
                        "position": [0, 0, 0],
                        "orientation": [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0],
                        "positionStatus": "defined"
                    }
                ]
            }
        ]
    }
    position = data["position"]
    orientation = data["orientation"]

    position = [float(a) for a in position]
    orientation = [float(a) for a in orientation]

    full_json["markups"][0]["controlPoints"][0]["position"] = position
    full_json["markups"][0]["controlPoints"][0]["orientation"] = orientation

    # create temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix=".mrk.json") as file:
        json.dump(full_json, file, indent=4)
        file.flush()  # Ensure data is written
        slicer.app.processEvents()  # Sync file system
        node = slicer.util.loadMarkups(file.name)

    return node


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


def hide_all_volumes_from_views(views: List[str]) -> None:
    lm = slicer.app.layoutManager()

    for name in views:
        try:
            slice_node = lm.sliceWidget(
                name).sliceLogic().GetSliceCompositeNode()

            slice_node.SetBackgroundVolumeID(None)
            slice_node.SetForegroundVolumeID(None)
        except:
            pass


def set_up_synchronisation(self: "registrationViewerWidget") -> None:
    """
    Set up synchronisation between the views based on the current transform type
    """
    self.ui_sub_6.synchronise_views_general.setVisible(True)

    if self.current_patient_transform_type == TransformType.NONE:
        self.unsynchronise_views()
        self.ui_sub_6.synchronise_views_general.setText(
            texts.Buttons.TRANFORMATION_NOT_AVAILABLE)
        self.ui_sub_6.synchronise_views_general.setEnabled(False)

    elif self.current_patient_transform_type == TransformType.LINEAR:
        self.use_only_linear_transform = True

        if self.crosshair:
            self.crosshair.use_only_linear_transform = True

        self.study_current_transform_type = TransformType.LINEAR
        self.ui_sub_6.synchronise_views_general.setEnabled(True)
        self.ui_sub_6.synchronise_views_general.setText(
            texts.Buttons.TURN_TRANSFORMATION_ON)

    elif self.current_patient_transform_type == TransformType.NONLINEAR:
        self.use_only_linear_transform = False

        if self.crosshair:
            self.crosshair.use_only_linear_transform = False

        self.study_current_transform_type = TransformType.NONLINEAR
        self.ui_sub_6.synchronise_views_general.setEnabled(True)
        self.ui_sub_6.synchronise_views_general.setText(
            texts.Buttons.TURN_TRANSFORMATION_ON)

    else:
        print(f"{self.current_patient_name=}")
        raise ValueError(f"Unknown transformation type {self.current_patient_name}")  # nopep8


def set_up_data_nodes(self: "registrationViewerWidget") -> None:

    self.node_transform_fixed = self.study_loaded_data[self.current_patient_name]["transform_fixed"]
    self.node_transform_moving = self.study_loaded_data[self.current_patient_name]["transform_moving"]
    self.ui_sub_3.inputSelector_fixed.setCurrentNode(
        self.study_loaded_data[self.current_patient_name]["fixed"])
    self.ui_sub_3.inputSelector_moving.setCurrentNode(
        self.study_loaded_data[self.current_patient_name]["moving"])
    self.ui_sub_3.inputSelector_transformation.setCurrentNode(
        self.study_loaded_data[self.current_patient_name]["deformation"])


def set_button_texts(self: "registrationViewerWidget") -> None:

    self.ui_sub_6.study_center_on_user_point_button.setText(
        texts.Buttons.CENTER_ON_USER_POINT)

    self.ui_sub_6.study_center_on_gt_point_button.setText(
        texts.Buttons.CENTER_ON_GROUND_TRUTH_POINT
    )

    self.ui_sub_6.study_next_task_button.setText(
        texts.Buttons.NEXT_TASK_BUTTON
    )

    self.ui_sub_6.study_add_point_button.setText(
        texts.Buttons.ADD_POINT_BUTTON
    )

    self.ui_sub_6.study_dropdown.setItemText(
        0, texts.Buttons.DROPDOWN_UNCHANGED)

    self.ui_sub_6.study_dropdown.setItemText(
        1, texts.Buttons.DROPDOWN_INCREASED)

    self.ui_sub_6.study_dropdown.setItemText(
        2, texts.Buttons.DROPDOWN_DECREASED)

    self.ui_sub_6.start_study_by_user_button.setText(
        texts.Buttons.START_STUDY
    )

    self.ui_sub_6.current_rad_name.setText(
        self.current_radiologist_name
    )

    self.ui_sub_6.progress_label_2.setText(texts.Contents.CURRENT_TASK)


def get_active_slice_view() -> str:
    """
    Return the name of the slice view that currently has focus.
    """

    widget = slicer.app.focusWidget()
    while widget:
        if isinstance(widget, qMRMLSliceWidget):
            return widget.mrmlSliceNode().GetLayoutName()
        widget = widget.parent()

    return "Unknown"


def set_buttons_for_test_cases(self: "registrationViewerWidget") -> None:

    self.ui_sub_6.synchronise_views_general.setVisible(False)

    self.ui_sub_6.study_center_on_user_point_button.setVisible(False)
    self.ui_sub_6.study_center_on_gt_point_button.setVisible(False)

    self.ui_sub_6.study_add_point_button.setVisible(False)

    self.ui_sub_6.progress_label_2.setText(texts.Contents.TEST_CURRENT_TASK)


def reset_buttons_after_test_cases(self: "registrationViewerWidget") -> None:

    self.ui_sub_6.progress_label_2.setText(texts.Contents.CURRENT_TASK)
