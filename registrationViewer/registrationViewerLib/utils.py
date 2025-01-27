from typing import Tuple, Callable, List

import qt
import slicer
import vtk


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
    if invert:
        node_target.ApplyTransform(node_transform.GetTransformFromParent())
    else:
        node_target.ApplyTransform(node_transform.GetTransformToParent())


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

    if not node:
        return

    displayNode = node.GetDisplayNode()

    if not displayNode:
        return

    displayNode.AutoWindowLevelOff()
    displayNode.SetWindow(window)
    displayNode.SetLevel(level)

    displayNode.ApplyThresholdOn()
    displayNode.SetThreshold(threshold[0], threshold[1])
