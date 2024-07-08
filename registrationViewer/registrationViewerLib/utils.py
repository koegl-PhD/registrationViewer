from typing import Tuple, Callable

import qt
import slicer

import numpy as np


def create_shortcuts(*shortcuts: Tuple[str, Callable]) -> None:
    """
    Creates and initializes shortcuts for the main window.
    """

    for (shortcutKey, callback) in shortcuts:
        shortcut = qt.QShortcut(slicer.util.mainWindow())
        shortcut.setKey(qt.QKeySequence(shortcutKey))
        shortcut.connect('activated()', callback)


def reverse_transformation_direction(position, new_position):
    """
    Reverse the transformation direction.
    """

    position_difference = np.array(new_position) - np.array(position)
    new_position = np.array(new_position) - 2*position_difference

    return new_position


def on_mouse_moved_place_corsshair(self, observer, eventid) -> None:  # pylint: disable=unused-argument
    """
    When the mouse moves in a view, the crosshair should follow the cursor.

    """

    if self.cursor_view not in ["Red", "Green", "Yellow"]:
        return

    initial_position: list[float] = [0., 0., 0.]
    self.cursor_node.GetCursorPositionRAS(initial_position)

    # in normal views we should follow the cursor (that's why group 1)
    slicer.modules.markups.logic().JumpSlicesToLocation(initial_position[0],
                                                        initial_position[1],
                                                        initial_position[2],
                                                        False,
                                                        1)

    # now we set the position of our corsshair and then transform it to the new position
    set_crosshair_nodes_to_position([self.crosshair_node_red_plus,
                                     self.crosshair_node_green_plus,
                                     self.crosshair_node_yellow_plus],
                                    initial_position)

    # now transform the crosshair to the new position
    if self.use_transform:
        transform_crosshair_nodes(self,
                                  [self.crosshair_node_red_plus,
                                   self.crosshair_node_green_plus,
                                   self.crosshair_node_yellow_plus])

    new_position: list[float] = [0., 0., 0.]
    self.crosshair_node_red_plus.GetNthControlPointPositionWorld(0,
                                                                 new_position)

    if self.reverse_transformation_direction:
        # the new_position should be moved in the opposite direction
        # for some reason the displacement is applied in the opposite direction
        new_position = reverse_transformation_direction(initial_position,
                                                        new_position)

    # in plus views we should follow the transformed cursor (that's why group 2)
    slicer.modules.markups.logic().JumpSlicesToLocation(new_position[0],
                                                        new_position[1],
                                                        new_position[2],
                                                        False,
                                                        2)

    set_crosshair_visibility(self)

    set_crosshair_nodes_to_position([self.crosshair_node_red,
                                     self.crosshair_node_green,
                                     self.crosshair_node_yellow],
                                    initial_position)

    set_crosshair_nodes_to_position([self.crosshair_node_red_plus,
                                     self.crosshair_node_green_plus,
                                     self.crosshair_node_yellow_plus],
                                    new_position)


def transform_crosshair_nodes(self, crosshair_nodes: list[slicer.vtkMRMLMarkupsFiducialNode]) -> None:
    """
    Transform every crosshair from the list of nodes with the current transformation.
    """

    for node in crosshair_nodes:
        node.ApplyTransform(self.node_transformation.GetTransformToParent())


def set_crosshair_nodes_to_position(crosshair_nodes: list[slicer.vtkMRMLMarkupsFiducialNode], position: list[float]) -> None:
    """
    Set every crosshair from the list of nodes to the given position.
    """

    for node in crosshair_nodes:
        node.SetNthControlPointPositionWorld(
            0, position[0], position[1], position[2])


def set_crosshair_visibility(self) -> None:
    """
    Turns off the corsshair in the current view
    """

    self.crosshair_node_red.GetDisplayNode().SetVisibility(True)
    self.crosshair_node_green.GetDisplayNode().SetVisibility(True)
    self.crosshair_node_yellow.GetDisplayNode().SetVisibility(True)
    self.crosshair_node_red_plus.GetDisplayNode().SetVisibility(True)
    self.crosshair_node_green_plus.GetDisplayNode().SetVisibility(True)
    self.crosshair_node_yellow_plus.GetDisplayNode().SetVisibility(True)

    if self.cursor_view == "Red":
        self.crosshair_node_red.GetDisplayNode().SetVisibility(False)

    elif self.cursor_view == "Green":
        self.crosshair_node_green.GetDisplayNode().SetVisibility(False)

    elif self.cursor_view == "Yellow":
        self.crosshair_node_yellow.GetDisplayNode().SetVisibility(False)

    elif self.cursor_view == "Red+":
        self.crosshair_node_red_plus.GetDisplayNode().SetVisibility(False)

    elif self.cursor_view == "Green+":
        self.crosshair_node_green_plus.GetDisplayNode().SetVisibility(False)

    elif self.cursor_view == "Yellow+":
        self.crosshair_node_yellow_plus.GetDisplayNode().SetVisibility(False)


def create_crosshair(views: list[str]) -> slicer.vtkMRMLMarkupsFiducialNode:

    crosshair_node = slicer.mrmlScene.AddNewNodeByClass(
        "vtkMRMLMarkupsFiducialNode")
    crosshair_node.SetName("")

    crosshair_node.AddControlPoint(0, 0, 0, "")
    crosshair_node.SetNthControlPointLabel(0, "")
    crosshair_node.GetDisplayNode().SetGlyphScale(1)

    slice_node_IDs = [slicer.app.layoutManager().sliceWidget(
        view).mrmlSliceNode().GetID() for view in views]

    crosshair_node.GetDisplayNode().SetViewNodeIDs(
        slice_node_IDs)

    return crosshair_node


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
