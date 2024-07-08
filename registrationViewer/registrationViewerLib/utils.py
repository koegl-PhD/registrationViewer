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


def on_mouse_moved_place_corsshair(self, observer, eventid):  # pylint: disable=unused-argument

    if self.cursor_view not in ["Red", "Green", "Yellow"]:
        return

    initial_position = [0, 0, 0]
    self.cursor_node.GetCursorPositionRAS(initial_position)

    # in normal views we should follow the cursor (that's why group 1)
    slicer.modules.markups.logic().JumpSlicesToLocation(initial_position[0],
                                                        initial_position[1],
                                                        initial_position[2],
                                                        False,
                                                        1)

    # now we set the position of our corsshair and then transform it to the new position
    self.my_crosshair_node_plus.SetNthControlPointPositionWorld(
        0, initial_position[0], initial_position[1], initial_position[2])

    # now transform the crosshair to the new position
    if self.use_transform:
        self.my_crosshair_node_plus.ApplyTransform(
            self.node_transformation.GetTransformToParent())

    new_position = [0, 0, 0]
    self.my_crosshair_node_plus.GetNthControlPointPositionWorld(0,
                                                                new_position)

    if self.reverse_transformation_direction:
        # the new_position should be moved in the opposite direction
        # for some reason the displacement is applied in the opposite direction
        new_position = reverse_transformation_direction(initial_position,
                                                        new_position)

    # make it visible
    self.my_crosshair_node_plus.GetDisplayNode().SetVisibility(True)

    # in plus views we should follow the transformed cursor (that's why group 2)
    slicer.modules.markups.logic().JumpSlicesToLocation(new_position[0],
                                                        new_position[1],
                                                        new_position[2],
                                                        False,
                                                        2)

    # set plus crosshair to the new position
    self.my_crosshair_node_plus.SetNthControlPointPositionWorld(
        0, new_position[0], new_position[1], new_position[2])

    handle_normal_crosshairs(self, initial_position)


def handle_normal_crosshairs(self, initial_position):
    # set normal crosshair to the new position

    if self.cursor_view == "Red":
        self.my_crosshair_node_red.GetDisplayNode().SetVisibility(False)
        self.my_crosshair_node_green.GetDisplayNode().SetVisibility(True)
        self.my_crosshair_node_yellow.GetDisplayNode().SetVisibility(True)

    elif self.cursor_view == "Green":
        self.my_crosshair_node_red.GetDisplayNode().SetVisibility(True)
        self.my_crosshair_node_green.GetDisplayNode().SetVisibility(False)
        self.my_crosshair_node_yellow.GetDisplayNode().SetVisibility(True)

    elif self.cursor_view == "Yellow":
        self.my_crosshair_node_red.GetDisplayNode().SetVisibility(True)
        self.my_crosshair_node_green.GetDisplayNode().SetVisibility(True)
        self.my_crosshair_node_yellow.GetDisplayNode().SetVisibility(False)

    self.my_crosshair_node_red.SetNthControlPointPositionWorld(
        0, initial_position[0], initial_position[1], initial_position[2])
    self.my_crosshair_node_green.SetNthControlPointPositionWorld(
        0, initial_position[0], initial_position[1], initial_position[2])
    self.my_crosshair_node_yellow.SetNthControlPointPositionWorld(
        0, initial_position[0], initial_position[1], initial_position[2])

    c = slicer.util.getNode("*Crosshair*")

    c.AddObserver(slicer.vtkMRMLCrosshairNode.CursorPositionModifiedEvent,
                  lambda callee, event: print(c.GetCursorPositionXYZ([0]*3).GetName()))


def create_crosshair(views: list[str]):

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
