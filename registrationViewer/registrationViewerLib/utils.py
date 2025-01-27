from typing import Tuple, Callable, List

import qt
import slicer
import vtk


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


def clone(node, name=""):
    if name == "":
        name = node.GetName() + "_Clone"
    clonedNode = slicer.mrmlScene.AddNewNodeByClass(node.GetClassName(), name)
    clonedNode.CopyContent(node)
    return clonedNode


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
                                       node_transform: slicer.vtkMRMLTransformNode, ) -> None:
    """
    Applies the given transform to the target node and hardens it.

    @param node_target: The target node.
    @param node_transform: The transform node.
    """

    node_target.SetAndObserveTransformNodeID(node_transform.GetID())

    node_target.HardenTransform()


def resample_node_to_reference_node(node_input: slicer.vtkMRMLScalarVolumeNode,
                                    node_reference: slicer.vtkMRMLScalarVolumeNode) -> None:
    params = {}

    params["inputVolume"] = node_input
    params["outputVolume"] = node_input
    params["referenceVolume"] = node_reference
    params["interpolationType"] = "linear"

    slicer.cli.runSync(
        slicer.modules.resamplescalarvectordwivolume, None, params)


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
