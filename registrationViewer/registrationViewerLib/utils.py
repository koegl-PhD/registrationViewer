from enum import Enum
import glob
import json
import os
from typing import TYPE_CHECKING
import tempfile

from typing import Dict, Union, Tuple, Callable, List

import qt
import slicer
import vtk

from registrationViewerLib.tasks import Task


if TYPE_CHECKING:
    from ..registrationViewer import registrationViewerWidget


class TransformType(Enum):
    NONE = "none"
    LINEAR = "linear"
    NONLINEAR = "nonlinear"


def center_on_point(point: slicer.vtkMRMLMarkupsFiducialNode) -> None:
    # jump to the location of the current point

    position = [0, 0, 0]
    point.GetNthControlPointPositionWorld(0, position)

    slicer.modules.markups.logic().JumpSlicesToLocation(position[0],
                                                        position[1],
                                                        position[2],
                                                        False,
                                                        1)


def get_paths_to_load(path_case_folder: str):
    path_experiment = os.path.dirname(
        os.path.dirname(path_case_folder))

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
        path_case_folder, 'raw', studies[1], '*_seg.nii.gz'))[0]
    path_seg_moving = glob.glob(os.path.join(
        path_case_folder, 'raw', studies[0], '*_seg.nii.gz'))[0]

    name_fixed = os.path.basename(
        path_volume_fixed).replace(".nii.gz", "")
    name_moving = os.path.basename(
        path_volume_moving).replace(".nii.gz", "")

    path_transform_fixed = glob.glob(os.path.join(
        path_case_folder, 'preprocessed', studies[1], '*.h5'))[0]
    path_transform_moving = glob.glob(os.path.join(
        path_case_folder, 'preprocessed', studies[0], '*.h5'))[0]

    paths_deformations = sorted(glob.glob(os.path.join(
        path_experiment, 'SerielleCTs_nii_forHumans_registrations', 'BSplineNiftyReg', '*', 'deformations', '*.nii.gz')))
    path_deformation = [
        x for x in paths_deformations if name_fixed in x and name_moving in x]

    if len(path_deformation) != 1:
        raise Exception(
            f"Expected 1 deformation file, found {len(path_deformation)}")

    path_deformation = path_deformation[0]

    if not os.path.exists(path_volume_fixed):
        print(path_volume_fixed)
        raise Exception(f"Volume fixed path does not exist: {path_volume_fixed}")  # nopep8
    if not os.path.exists(path_volume_moving):
        print(path_volume_moving)
        raise Exception(f"Volume moving path does not exist: {path_volume_moving}")  # nopep8
    if not os.path.exists(path_seg_fixed):
        print(path_seg_fixed)
        raise Exception(
            f"Segmentation fixed path does not exist: {path_seg_fixed}")
    if not os.path.exists(path_seg_moving):
        print(path_seg_moving)
        raise Exception(
            f"Segmentation moving path does not exist: {path_seg_moving}")
    if not os.path.exists(path_transform_fixed):
        print(path_transform_fixed)
        raise Exception(f"Transform fixed path does not exist: {path_transform_fixed}")  # nopep8
    if not os.path.exists(path_transform_moving):
        print(path_transform_moving)
        raise Exception(f"Transform moving path does not exist: {path_transform_moving}")  # nopep8
    if not os.path.exists(path_deformation):
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


def update_progress_window(progress: int, message: str) -> bool:
    if slicer.progressWindow.wasCanceled:
        slicer.progressWindow.close()
        return False

    slicer.progressWindow.setLabelText(message)
    slicer.progressWindow.setValue(progress)

    return True


def hide_all_points_except(
    task: Task,
    points: Dict[Task, Union[None, slicer.vtkMRMLMarkupsFiducialNode]]
) -> None:

    for current_task, point in points.items():
        if point is not None and current_task != task:
            point.SetDisplayVisibility(False)
        if point is not None and current_task == task:
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


def set_ui_simplification(simple: bool) -> None:
    """
    Simplifies the UI by hiding the toolbar, module panel etc.
    """

    value = not simple

    slicer.util.setMenuBarsVisible(value)

    slicer.util.setToolbarsVisible(value)

    # hide help section
    slicer.util.setModuleHelpSectionVisible(value)

    # hide the module panel
    slicer.util.setModulePanelTitleVisible(value)

    # hide data probe
    slicer.util.setDataProbeVisible(value)

    # hi ebar at the botto of the window
    slicer.util.setStatusBarVisible(value)

    slicer.util.setViewControllersVisible(value)

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


def show_warning_popup(content: str,
                       question: str):
    msgBox = qt.QMessageBox()
    msgBox.setIcon(qt.QMessageBox.Warning)
    msgBox.setText(content)
    msgBox.setInformativeText(question)
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


def show_info_popup(content: str, title: str = "Information") -> None:
    msgBox = qt.QMessageBox()
    msgBox.setIcon(qt.QMessageBox.Information)
    msgBox.setWindowTitle(title)
    msgBox.setText(content)
    msgBox.setStandardButtons(qt.QMessageBox.Ok)  # Only "OK" button
    msgBox.exec_()


def has_control_point_with_name(node_fiducial: slicer.vtkMRMLMarkupsFiducialNode,
                                name: str) -> bool:

    for i in range(node_fiducial.GetNumberOfControlPoints()):
        if node_fiducial.GetNthControlPointLabel(i) == name:
            return True

    return False


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
