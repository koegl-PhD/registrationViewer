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


def place_my_crosshair_at(crosshair_node, node_transformation, position: tuple[float, float, float], use_transform=True, centered: bool = True, view_group: int = 1) -> None:
    """
    Place the crosshair at the given position. Position is in RAS coordinates.
    """

    # in normal views we should follow the cursor (that's why group 1)
    slicer.modules.markups.logic().JumpSlicesToLocation(position[0],
                                                        position[1],
                                                        position[2],
                                                        False,
                                                        1)

    # now we set the position of our corsshair and then transform it to the new position
    crosshair_node.SetNthControlPointPositionWorld(
        0, position[0], position[1], position[2])

    # now transform the crosshair to the new position
    if use_transform:
        crosshair_node.ApplyTransform(
            node_transformation.GetTransformToParent())
    new_position = [0, 0, 0]
    crosshair_node.GetNthControlPointPositionWorld(0, new_position)

    position_difference = np.array(new_position) - np.array(position)

    # the new_position should be moved in the opposite direction
    # for some reason the displacement is applied in the opposite direction
    new_position = np.array(new_position) - 2*position_difference

    # make it visible
    crosshair_node.GetDisplayNode().SetVisibility(True)

    # in plus views we should follow the transformed cursor (that's why group 2)
    slicer.modules.markups.logic().JumpSlicesToLocation(new_position[0],
                                                        new_position[1],
                                                        new_position[2],
                                                        False,
                                                        2)

    # set crosshair to the new position
    crosshair_node.SetNthControlPointPositionWorld(
        0, new_position[0], new_position[1], new_position[2])


def on_mouse_moved_place_corsshair(self, observer, eventid):

    ras = [0, 0, 0]
    self.cursor_node.GetCursorPositionRAS(ras)

    # print(use_transform)

    place_my_crosshair_at(self.my_crosshair_node,
                          self.node_transformation,
                          position=(ras[0], ras[1], ras[2]),
                          use_transform=self.use_transform,
                          centered=False)


def create_crosshair(self):
    self.my_crosshair_node = slicer.mrmlScene.AddNewNodeByClass(
        "vtkMRMLMarkupsFiducialNode")
    self.my_crosshair_node.SetName("")

    self.my_crosshair_node.AddControlPoint(0, 0, 0, "")
    self.my_crosshair_node.SetNthControlPointLabel(0, "")
    self.my_crosshair_node.GetDisplayNode().SetGlyphScale(1)

    sliceNodeRed_plus = slicer.app.layoutManager().sliceWidget("Red+").mrmlSliceNode()
    sliceNodeGreen_plus = slicer.app.layoutManager().sliceWidget("Green+").mrmlSliceNode()
    sliceNodeYellow_plus = slicer.app.layoutManager(
    ).sliceWidget("Yellow+").mrmlSliceNode()

    self.my_crosshair_node.GetDisplayNode().SetViewNodeIDs(
        [sliceNodeRed_plus.GetID(), sliceNodeGreen_plus.GetID(), sliceNodeYellow_plus.GetID()])


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
