from typing import List, Literal

import slicer

from registrationViewerLib import view_logic, utils


class Crosshairs():

    """
    Class to handle crosshairs for each view
    """
    # Class constants for view names
    VIEWS_1 = ["Red", "Green", "Yellow"]
    VIEWS_2 = ["Red+", "Green+", "Yellow+"]
    VIEWS = VIEWS_1 + VIEWS_2

    def __init__(self,
                 node_cursor: slicer.vtkMRMLCrosshairNode,
                 node_transform_nonlinear: slicer.vtkMRMLGridTransformNode,
                 use_transform: bool,
                 ) -> None:

        self.node_cursor = node_cursor
        self.node_transform_nonlinear = node_transform_nonlinear
        self.use_transform = use_transform

        self.reverse_transf_direction = False

        self.create_crosshairs_and_folder()

    def create_crosshairs_and_folder(self) -> None:

        self.crosshair_nodes = {
            view: self.create_crosshair(view) for view in self.VIEWS
        }

        # create a folder to put the crosshairs in
        self.sh_node = slicer.mrmlScene.GetSubjectHierarchyNode()
        self.crosshair_folder_id = self.sh_node.CreateFolderItem(
            self.sh_node.GetSceneItemID(), "crosshairs")

        for crosshair_node in self.crosshair_nodes.values():
            self.sh_node.SetItemParent(self.sh_node.GetItemByDataNode(
                crosshair_node), self.crosshair_folder_id)

        # collapse folder
        self.sh_node.SetItemExpanded(self.crosshair_folder_id, False)

    def delete_crosshairs_and_folder(self) -> None:
        """
        Delete the crosshairs and the folder.
        """

        for node in self.crosshair_nodes.values():
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

        crosshair_node.LockedOn()

        crosshair_node.GetDisplayNode().SetViewNodeIDs([
            slicer.app.layoutManager().sliceWidget(view).mrmlSliceNode().GetID()
        ])

        return crosshair_node

    def place_crosshair_with_transformation(
        self,
        views: List[str],
        crosshair_nodes: list[slicer.vtkMRMLMarkupsFiducialNode],
        reverse_transf_direction: bool
    ) -> None:
        """
        Places the crosshair in the current view and transforms it to the new position.
        """

        initial_position: list[float] = [0., 0., 0.]
        self.node_cursor.GetCursorPositionRAS(initial_position)

        # now we set the position of our crosshair and then transform it to the new position
        self.set_crosshair_nodes_to_position(crosshair_nodes,
                                             initial_position)

        # now transform the crosshair to the new position
        if self.use_transform:
            self.transform_crosshair_nodes(crosshair_nodes,
                                           not reverse_transf_direction)

        new_position: list[float] = [0., 0., 0.]
        crosshair_nodes[0].GetNthControlPointPositionWorld(0,
                                                           new_position)

        for view in views:
            view_logic.set_offset_to_ras(new_position, view)

        self.set_crosshair_visibility()

        self.set_crosshair_nodes_to_position(crosshair_nodes,
                                             new_position)

    def place_crosshair_without_transformation(
        self,
        views: List[str],
        crosshair_nodes: list[slicer.vtkMRMLMarkupsFiducialNode],
    ) -> None:

        initial_position: list[float] = [0., 0., 0.]
        self.node_cursor.GetCursorPositionRAS(initial_position)

        self.set_crosshair_visibility()

        self.set_crosshair_nodes_to_position(crosshair_nodes,
                                             initial_position)

        # only jump the *other* slice views in this group; leave the active view’s slice unchanged
        for view in views:
            if view == utils.get_cursor_view_name():
                continue

            view_logic.set_offset_to_ras(initial_position, view)

    def on_mouse_moved_place_crosshair(self, observer, eventid) -> None:  # pylint: disable=unused-argument
        """
        When the mouse moves in a view, the crosshair should follow the cursor.

        """
        current_view = utils.get_cursor_view_name()

        if current_view in self.VIEWS_1:
            self.place_crosshair_without_transformation(views=self.VIEWS_1,
                                                        crosshair_nodes=self.crosshairs_1)
            self.place_crosshair_with_transformation(views=self.VIEWS_2,
                                                     crosshair_nodes=self.crosshairs_2,
                                                     reverse_transf_direction=self.reverse_transf_direction)

        elif current_view in self.VIEWS_2:
            self.place_crosshair_with_transformation(views=self.VIEWS_1,
                                                     crosshair_nodes=self.crosshairs_1,
                                                     reverse_transf_direction=not self.reverse_transf_direction)
            self.place_crosshair_without_transformation(views=self.VIEWS_2,
                                                        crosshair_nodes=self.crosshairs_2)

    def transform_crosshair_nodes(self,
                                  crosshair_nodes: list[slicer.vtkMRMLMarkupsFiducialNode],
                                  invert: bool) -> None:
        """
        Transform every crosshair from the list of nodes with the current transformation.
        """

        if not self.node_transform_nonlinear:
            print("No transformation available")
            return

        for node in crosshair_nodes:
            transform = (self.node_transform_nonlinear.GetTransformFromParent()
                         if invert
                         else self.node_transform_nonlinear.GetTransformToParent())
            node.ApplyTransform(transform)

    def _set_node_visibility(self, node: slicer.vtkMRMLMarkupsFiducialNode, visibility: bool) -> None:
        """Helper method to set visibility of a crosshair node."""
        display_node = node.GetDisplayNode()
        if display_node is not None:
            display_node.SetVisibility(visibility)

    @staticmethod
    def set_crosshair_nodes_to_position(crosshair_nodes: list[slicer.vtkMRMLMarkupsFiducialNode],
                                        position: list[float]) -> None:
        """
        Set every crosshair from the list of nodes to the given position.
        """

        for node in crosshair_nodes:
            node.SetNthControlPointPositionWorld(0, *position)

    def set_crosshair_visibility_in_views(self, views: list[str], visibility: bool) -> None:
        """
        Hide the crosshair in the given views.
        """

        for view in views:
            if view in self.crosshair_nodes:
                self._set_node_visibility(
                    self.crosshair_nodes[view], visibility)

    def set_crosshair_visibility(self) -> None:
        """
        Turns off the crosshair in the current view
        """

        for node in self.crosshair_nodes.values():
            self._set_node_visibility(node, True)

        current_view = utils.get_cursor_view_name()
        if current_view in self.crosshair_nodes:
            self._set_node_visibility(
                self.crosshair_nodes[current_view], False)

    @property
    def crosshairs_1(self) -> list[slicer.vtkMRMLMarkupsFiducialNode]:

        return [self.crosshair_nodes[view] for view in self.VIEWS_1]

    @property
    def crosshairs_2(self) -> list[slicer.vtkMRMLMarkupsFiducialNode]:

        return [self.crosshair_nodes[view] for view in self.VIEWS_2]
