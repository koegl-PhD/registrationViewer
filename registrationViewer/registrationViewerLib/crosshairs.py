import slicer

import numpy as np


class Crosshairs():

    """
    Class to handle crosshairs for each view
    """

    def __init__(self,
                 cursor_node,
                 use_transform) -> None:

        assert cursor_node is not None, "Cursor node is None"
        assert use_transform is not None, "Use transform is None"

        self.cursor_node = cursor_node
        self.use_transform = use_transform

        self.node_transformation = None
        self.cursor_view: str = ""
        self.reverse_transf_direction: bool = False

        # create crosshairs for each view
        self.crosshair_node_red = self.create_crosshair(
            views=["Red"])
        self.crosshair_node_green = self.create_crosshair(
            views=["Green"])
        self.crosshair_node_yellow = self.create_crosshair(
            views=["Yellow"])

        self.crosshair_node_red_plus = self.create_crosshair(
            views=["Red+"])
        self.crosshair_node_green_plus = self.create_crosshair(
            views=["Green+"])
        self.crosshair_node_yellow_plus = self.create_crosshair(
            views=["Yellow+"])

        # create a folder to put the crosshairs in
        self.sh_node = slicer.mrmlScene.GetSubjectHierarchyNode()
        self.crosshair_folder_id = self.sh_node.CreateFolderItem(
            self.sh_node.GetSceneItemID(), "crosshairs")

        self.sh_node.SetItemParent(self.sh_node.GetItemByDataNode(
            self.crosshair_node_red), self.crosshair_folder_id)
        self.sh_node.SetItemParent(self.sh_node.GetItemByDataNode(
            self.crosshair_node_green), self.crosshair_folder_id)
        self.sh_node.SetItemParent(self.sh_node.GetItemByDataNode(
            self.crosshair_node_yellow), self.crosshair_folder_id)

        self.sh_node.SetItemParent(self.sh_node.GetItemByDataNode(
            self.crosshair_node_red_plus), self.crosshair_folder_id)
        self.sh_node.SetItemParent(self.sh_node.GetItemByDataNode(
            self.crosshair_node_green_plus), self.crosshair_folder_id)
        self.sh_node.SetItemParent(self.sh_node.GetItemByDataNode(
            self.crosshair_node_yellow_plus), self.crosshair_folder_id)

        # collapse folder
        self.sh_node.SetItemExpanded(self.crosshair_folder_id, False)

    def delete_crosshairs_and_folder(self) -> None:
        """
        Delete the crosshairs and the folder.
        """

        slicer.mrmlScene.RemoveNode(self.crosshair_node_red)
        slicer.mrmlScene.RemoveNode(self.crosshair_node_green)
        slicer.mrmlScene.RemoveNode(self.crosshair_node_yellow)

        slicer.mrmlScene.RemoveNode(self.crosshair_node_red_plus)
        slicer.mrmlScene.RemoveNode(self.crosshair_node_green_plus)
        slicer.mrmlScene.RemoveNode(self.crosshair_node_yellow_plus)

        self.sh_node.RemoveItem(self.crosshair_folder_id)

    @staticmethod
    def create_crosshair(views: list[str]) -> slicer.vtkMRMLMarkupsFiducialNode:
        """
        Create a crosshair in the given views.
        """

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

    @staticmethod
    def reverse_transformation_direction(position, new_position):
        """
        Reverse the transformation direction.
        """

        position_difference = np.array(new_position) - np.array(position)
        new_position = np.array(new_position) - 2*position_difference

        return new_position

    def place_crosshair(self,
                        untransformed_view_group: int,
                        transformed_view_group: int,
                        untransformed_corsshair_nodes: list[slicer.vtkMRMLMarkupsFiducialNode],
                        tranformed_crosshair_nodes: list[slicer.vtkMRMLMarkupsFiducialNode],
                        reverse_transf_direction: bool
                        ) -> None:
        """
        Places the crosshair in the current view and transforms it to the new position.
        """

        initial_position: list[float] = [0., 0., 0.]
        self.cursor_node.GetCursorPositionRAS(initial_position)

        # in plus views we should follow the cursor (that's why group 2)
        slicer.modules.markups.logic().JumpSlicesToLocation(initial_position[0],
                                                            initial_position[1],
                                                            initial_position[2],
                                                            False,
                                                            untransformed_view_group)

        # now we set the position of our crosshair and then transform it to the new position
        self.set_crosshair_nodes_to_position(tranformed_crosshair_nodes,
                                             initial_position)

        # now transform the crosshair to the new position
        if self.use_transform:
            self.transform_crosshair_nodes(tranformed_crosshair_nodes)

        new_position: list[float] = [0., 0., 0.]
        tranformed_crosshair_nodes[0].GetNthControlPointPositionWorld(0,
                                                                      new_position)

        if not reverse_transf_direction:
            # the new_position should be moved in the opposite direction
            # for some reason the displacement is applied in the opposite direction
            new_position = self.reverse_transformation_direction(initial_position,
                                                                 new_position)

        # in plus views we should follow the transformed cursor (that's why group 2)
        slicer.modules.markups.logic().JumpSlicesToLocation(new_position[0],
                                                            new_position[1],
                                                            new_position[2],
                                                            False,
                                                            transformed_view_group)

        self.set_crosshair_visibility()

        self.set_crosshair_nodes_to_position(tranformed_crosshair_nodes,
                                             new_position)

        self.set_crosshair_nodes_to_position(untransformed_corsshair_nodes,
                                             initial_position)

    def on_mouse_moved_place_crosshair(self, observer, eventid) -> None:  # pylint: disable=unused-argument
        """
        When the mouse moves in a view, the crosshair should follow the cursor.

        """

        if self.cursor_view in ["Red", "Green", "Yellow"]:
            self.place_crosshair(untransformed_view_group=1,
                                 transformed_view_group=2,
                                 untransformed_corsshair_nodes=[self.crosshair_node_red,
                                                                self.crosshair_node_green,
                                                                self.crosshair_node_yellow],
                                 tranformed_crosshair_nodes=[self.crosshair_node_red_plus,
                                                             self.crosshair_node_green_plus,
                                                             self.crosshair_node_yellow_plus],
                                 reverse_transf_direction=self.reverse_transf_direction)
        elif self.cursor_view in ["Red+", "Green+", "Yellow+"]:
            self.place_crosshair(untransformed_view_group=2,
                                 transformed_view_group=1,
                                 untransformed_corsshair_nodes=[self.crosshair_node_red_plus,
                                                                self.crosshair_node_green_plus,
                                                                self.crosshair_node_yellow_plus],
                                 tranformed_crosshair_nodes=[self.crosshair_node_red,
                                                             self.crosshair_node_green,
                                                             self.crosshair_node_yellow],
                                 reverse_transf_direction=not self.reverse_transf_direction)

    def transform_crosshair_nodes(self, crosshair_nodes: list[slicer.vtkMRMLMarkupsFiducialNode]) -> None:
        """
        Transform every crosshair from the list of nodes with the current transformation.
        """

        for node in crosshair_nodes:
            if self.node_transformation:
                node.ApplyTransform(
                    self.node_transformation.GetTransformToParent())

    @staticmethod
    def set_crosshair_nodes_to_position(crosshair_nodes: list[slicer.vtkMRMLMarkupsFiducialNode],
                                        position: list[float]) -> None:
        """
        Set every crosshair from the list of nodes to the given position.
        """

        for node in crosshair_nodes:
            node.SetNthControlPointPositionWorld(
                0, position[0], position[1], position[2])

    def set_crosshair_visibility(self) -> None:
        """
        Turns off the crosshair in the current view
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
