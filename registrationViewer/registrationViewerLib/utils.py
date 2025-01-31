from typing import Tuple, Callable, List

import qt
import slicer
import vtk


def update_progress_window(progress: int, message: str) -> bool:
    if slicer.progressWindow.wasCanceled:
        slicer.progressWindow.close()
        return False

    slicer.progressWindow.setLabelText(message)
    slicer.progressWindow.setValue(progress)

    return True


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
    slicer.util.setPythonConsoleVisible(value)


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
    self.ui.inputSelector_fixed.setCurrentNode(node_volume_fixed)
    self.ui.inputSelector_moving.setCurrentNode(node_volume_moving)
    self.ui.inputSelector_transformation.setCurrentNode(node_transformation)


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
