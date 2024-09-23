from typing import List

import numpy as np

import slicer


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

        self.views_1 = ["Red1", "Green1", "Yellow1"]
        self.views_2 = ["Red2", "Green2", "Yellow2"]
        self.views_3 = ["Red3", "Green3", "Yellow3"]
        self.views = self.views_1 + self.views_2 + self.views_3

        self.create_crosshairs_and_folder()

    def create_crosshairs_and_folder(self) -> None:

        self.crosshair_nodes = {
            view: self.create_crosshair(view) for view in self.views
        }

        # create a folder to put the crosshairs in
        self.sh_node = slicer.mrmlScene.GetSubjectHierarchyNode()
        self.crosshair_folder_id = self.sh_node.CreateFolderItem(
            self.sh_node.GetSceneItemID(), "crosshairs")

        for _, crosshair_node in self.crosshair_nodes.items():
            self.sh_node.SetItemParent(self.sh_node.GetItemByDataNode(
                crosshair_node), self.crosshair_folder_id)

        # collapse folder
        self.sh_node.SetItemExpanded(self.crosshair_folder_id, False)

    def delete_crosshairs_and_folder(self) -> None:
        """
        Delete the crosshairs and the folder.
        """

        for _, node in self.crosshair_nodes.items():
            slicer.mrmlScene.RemoveNode(node)

        self.sh_node.RemoveItem(self.crosshair_folder_id)

    @staticmethod
    def create_crosshair(view: str) -> slicer.vtkMRMLMarkupsFiducialNode:
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
            view).mrmlSliceNode().GetID()]

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

    def place_crosshair_with_transformation(self,
                                            view_group: int,
                                            crosshair_nodes: list[slicer.vtkMRMLMarkupsFiducialNode],
                                            reverse_transf_direction: bool
                                            ) -> None:
        """
        Places the crosshair in the current view and transforms it to the new position.
        """

        initial_position: list[float] = [0., 0., 0.]
        self.cursor_node.GetCursorPositionRAS(initial_position)

        # now we set the position of our crosshair and then transform it to the new position
        self.set_crosshair_nodes_to_position(crosshair_nodes,
                                             initial_position)

        # now transform the crosshair to the new position
        if self.use_transform:
            self.transform_crosshair_nodes(crosshair_nodes)

        new_position: list[float] = [0., 0., 0.]
        crosshair_nodes[0].GetNthControlPointPositionWorld(0,
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
                                                            view_group)

        self.set_crosshair_visibility()

        self.set_crosshair_nodes_to_position(crosshair_nodes,
                                             new_position)

    def place_crosshair_without_transformation(self,
                                               view_group: int,
                                               crosshair_nodes: list[slicer.vtkMRMLMarkupsFiducialNode]) -> None:

        initial_position: list[float] = [0., 0., 0.]
        self.cursor_node.GetCursorPositionRAS(initial_position)

        # in plus views we should follow the cursor (that's why group 2)
        slicer.modules.markups.logic().JumpSlicesToLocation(initial_position[0],
                                                            initial_position[1],
                                                            initial_position[2],
                                                            False,
                                                            view_group)

        self.set_crosshair_visibility()

        self.set_crosshair_nodes_to_position(crosshair_nodes,
                                             initial_position)

    def on_mouse_moved_place_crosshair(self, observer, eventid) -> None:  # pylint: disable=unused-argument
        """
        When the mouse moves in a view, the crosshair should follow the cursor.

        """

        if self.cursor_view in self.views_1:
            self.place_crosshair_without_transformation(view_group=1,
                                                        crosshair_nodes=self.crosshairs_1)
            self.place_crosshair_with_transformation(view_group=2,
                                                     crosshair_nodes=self.crosshairs_2,
                                                     reverse_transf_direction=self.reverse_transf_direction)
            self.place_crosshair_without_transformation(view_group=3,
                                                        crosshair_nodes=self.crosshairs_3)

        elif self.cursor_view in self.views_2:
            self.place_crosshair_with_transformation(view_group=1,
                                                     crosshair_nodes=self.crosshairs_1,
                                                     reverse_transf_direction=not self.reverse_transf_direction)
            self.place_crosshair_without_transformation(view_group=2,
                                                        crosshair_nodes=self.crosshairs_2)
            self.place_crosshair_with_transformation(view_group=3,
                                                     crosshair_nodes=self.crosshairs_3,
                                                     reverse_transf_direction=not self.reverse_transf_direction)

        elif self.cursor_view in self.views_3:
            self.place_crosshair_without_transformation(view_group=1,
                                                        crosshair_nodes=self.crosshairs_1)
            self.place_crosshair_with_transformation(view_group=2,
                                                     crosshair_nodes=self.crosshairs_2,
                                                     reverse_transf_direction=self.reverse_transf_direction)
            self.place_crosshair_without_transformation(view_group=3,
                                                        crosshair_nodes=self.crosshairs_3)

    def transform_crosshair_nodes(self, crosshair_nodes: list[slicer.vtkMRMLMarkupsFiducialNode]) -> None:
        """
        Transform every crosshair from the list of nodes with the current transformation.
        """

        for node in crosshair_nodes:
            if self.node_transformation:
                node.ApplyTransform(
                    self.node_transformation.GetTransformToParent())

    @ staticmethod
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

        for _, node in self.crosshair_nodes.items():
            display_node = node.GetDisplayNode()
            if display_node is not None:
                display_node.SetVisibility(True)

        if self.cursor_view in self.crosshair_nodes:
            display_node = self.crosshair_nodes[self.cursor_view].GetDisplayNode(
            )
            if display_node is not None:
                display_node.SetVisibility(False)

    @ property
    def crosshairs_1(self) -> list[slicer.vtkMRMLMarkupsFiducialNode]:

        return [self.crosshair_nodes[view] for view in self.views_1]

    @ property
    def crosshairs_2(self) -> list[slicer.vtkMRMLMarkupsFiducialNode]:

        return [self.crosshair_nodes[view] for view in self.views_2]

    @ property
    def crosshairs_3(self) -> list[slicer.vtkMRMLMarkupsFiducialNode]:

        return [self.crosshair_nodes[view] for view in self.views_3]
