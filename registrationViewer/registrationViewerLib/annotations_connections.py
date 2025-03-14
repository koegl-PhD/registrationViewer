import vtk
import json
import os
from pathlib import Path

from typing import Literal, TYPE_CHECKING, List

import slicer
import qt

from registrationViewerLib import tasks, utils, view_logic

if TYPE_CHECKING:
    from ..registrationViewer import registrationViewerWidget


def set_connections(self: "registrationViewerWidget") -> None:

    self.ui_sub_5.set_slice_idx_fixed_button.connect("clicked(bool)",
                                                     lambda: on_jumpt_to_slice_idx_fixed(self))

    self.ui_sub_5.set_slice_idx_moving_button.connect("clicked(bool)",
                                                      lambda: on_jumpt_to_slice_idx_moving(self))

    self.ui_sub_5.saveAnnotations.connect("clicked(bool)",
                                          lambda: on_save_annotations(self))
    self.ui_sub_5.clearAnnotations.connect("clicked(bool)",
                                           lambda: on_clear_annotations(self))

    self.ui_sub_5.addLymphnodeRoiFixed.connect("clicked(bool)",
                                               lambda: on_add_roi_lymphnode(self, 'fixed'))
    self.ui_sub_5.addLymphnodeRoiMoving.connect("clicked(bool)",
                                                lambda: on_add_roi_lymphnode(self, 'moving'))

    self.ui_sub_5.lymphnode_dropdown.currentIndexChanged.connect(
        lambda: on_lymphnode_size(self))

    self.ui_sub_5.add_a_vertebralis_r_PointFixed.connect("clicked(bool)",
                                                         lambda: on_add_annotation_point_fixed(self, tasks.Task.A_VERTEBRALIS_R))
    self.ui_sub_5.add_a_vertebralis_r_PointMoving.connect("clicked(bool)",
                                                          lambda: on_add_annotation_point_moving(self, tasks.Task.A_VERTEBRALIS_R))

    self.ui_sub_5.add_a_vertebralis_l_PointFixed.connect("clicked(bool)",
                                                         lambda: on_add_annotation_point_fixed(self, tasks.Task.A_VERTEBRALIS_L))
    self.ui_sub_5.add_a_vertebralis_l_PointMoving.connect("clicked(bool)",
                                                          lambda: on_add_annotation_point_moving(self, tasks.Task.A_VERTEBRALIS_L))

    self.ui_sub_5.add_a_carotisexterna_r_PointFixed.connect("clicked(bool)",
                                                            lambda: on_add_annotation_point_fixed(self, tasks.Task.A_CAROTISEXTERNA_R))
    self.ui_sub_5.add_a_carotisexterna_r_PointMoving.connect("clicked(bool)",
                                                             lambda: on_add_annotation_point_moving(self, tasks.Task.A_CAROTISEXTERNA_R))

    self.ui_sub_5.add_a_carotisexterna_l_PointFixed.connect("clicked(bool)",
                                                            lambda: on_add_annotation_point_fixed(self, tasks.Task.A_CAROTISEXTERNA_L))
    self.ui_sub_5.add_a_carotisexterna_l_PointMoving.connect("clicked(bool)",
                                                             lambda: on_add_annotation_point_moving(self, tasks.Task.A_CAROTISEXTERNA_L))

    self.ui_sub_5.recurrencePresentCheckBox.toggled.connect(
        lambda: on_recurrence_present(self))
    self.ui_sub_5.addRecurrenceRoiFixed.connect("clicked(bool)",
                                                lambda: on_add_roi_recurrence(self))

    self.ui_sub_5.hideAnnotations.connect("clicked(bool)",
                                          lambda: on_set_annotations_visibility(self, False))
    self.ui_sub_5.showAnnotations.connect("clicked(bool)",
                                          lambda: on_set_annotations_visibility(self, True))


def on_save_annotations(self: "registrationViewerWidget") -> None:

    if self.annotations_already_saved:
        if not utils.show_warning_popup("Annotations already saved",
                                        "Do you want to overwrite them?"):
            return

    # example name volume: XPqt2AtrAMc~2_followup_LleziZ9eAbs~201_hals_pv_08_i6_b_idose_6
    name_volume_fixed = str(self.node_fixed.GetName())
    name_volume_moving = str(self.node_moving.GetName())

    # check if all annotations are present
    if self.annotation_fixed_roi_lymphnode is None:
        if not utils.show_warning_popup("You didn't add lymph node in fixed.",
                                        "(Click OK to continue saving)"):
            return
    if self.annotation_moving_roi_lymphnode is None:
        if not utils.show_warning_popup("You didn't add lymph node in moving.",
                                        "(Click OK to continue saving)"):
            return

    point_name = "point_" + tasks.Task.A_VERTEBRALIS_R.value + '_' + name_volume_fixed
    if not utils.has_control_point_with_name(self.annotation_fixed_points, point_name):
        if not utils.show_warning_popup("You didn't add A. vertebralis right point for fixed volume.",
                                        "(Click OK to continue saving)"):
            return

    point_name = "point_" + tasks.Task.A_VERTEBRALIS_R.value + '_' + name_volume_moving
    if not utils.has_control_point_with_name(self.annotation_moving_points, point_name):
        if not utils.show_warning_popup("You didn't add A. vertebralis right point for moving volume.",
                                        "(Click OK to continue saving)"):
            return

    point_name = "point_" + tasks.Task.A_VERTEBRALIS_L.value + '_' + name_volume_fixed
    if not utils.has_control_point_with_name(self.annotation_fixed_points, point_name):
        if not utils.show_warning_popup("You didn't add A. vertebralis left point for fixed volume.",
                                        "(Click OK to continue saving)"):
            return

    point_name = "point_" + tasks.Task.A_VERTEBRALIS_L.value + '_' + name_volume_moving
    if not utils.has_control_point_with_name(self.annotation_moving_points, point_name):
        if not utils.show_warning_popup("You didn't add A. vertebralis left point for moving volume.",
                                        "(Click OK to continue saving)"):
            return

    point_name = "point_" + tasks.Task.A_CAROTISEXTERNA_R.value + '_' + name_volume_fixed
    if not utils.has_control_point_with_name(self.annotation_fixed_points, point_name):
        if not utils.show_warning_popup("You didn't add A. carotis externa right point for fixed volume.",
                                        "(Click OK to continue saving)"):
            print("not continuing")
            return

    point_name = "point_" + tasks.Task.A_CAROTISEXTERNA_R.value + '_' + name_volume_moving
    if not utils.has_control_point_with_name(self.annotation_moving_points, point_name):
        if not utils.show_warning_popup("You didn't add A. carotis externa right point for moving volume.",
                                        "(Click OK to continue saving)"):
            return

    point_name = "point_" + tasks.Task.A_CAROTISEXTERNA_L.value + '_' + name_volume_fixed
    if not utils.has_control_point_with_name(self.annotation_fixed_points, point_name):
        if not utils.show_warning_popup("You didn't add A. carotis externa left point for fixed volume.",
                                        "(Click OK to continue saving)"):
            return

    point_name = "point_" + tasks.Task.A_CAROTISEXTERNA_L.value + '_' + name_volume_moving
    if not utils.has_control_point_with_name(self.annotation_moving_points, point_name):
        if not utils.show_warning_popup("You didn't add A. carotis externa left point for moving volume.",
                                        "(Click OK to continue saving)"):
            return

    if self.annotation_fixed_roi_lymphnode and self.annotation_lymphnode_size == "Size same":
        if not utils.show_warning_popup("Did you check for lymphnode size change?",
                                        "(Click OK to continue saving)"):
            return

    if self.annotation_fixed_roi_recurrence is None and self.ui_sub_5.recurrencePresentCheckBox.isChecked():
        utils.show_info_popup(
            "You marked that there is a recurrence, but did not add a ROI for it.\nExiting saving.")
        return

    if self.annotation_fixed_roi_recurrence is None:
        if not utils.show_warning_popup("Did you check for recurrence?",
                                        "(Click OK to continue saving)"):
            return

    name_study_fixed = self.node_fixed.GetName().split('~')[1]
    name_study_moving = self.node_moving.GetName().split('~')[1]

    path_fixed: Path = Path(self.current_loaded_case_path) / \
        "preprocessed" / name_study_fixed / "annotations"
    path_moving: Path = Path(self.current_loaded_case_path) / \
        "preprocessed" / name_study_moving / "annotations"

    if not os.path.exists(path_fixed):
        os.makedirs(path_fixed)
    if not os.path.exists(path_moving):
        os.makedirs(path_moving)

    print(f"{path_fixed=}")
    print(f"{path_moving=}")

    slicer.util.saveNode(self.annotation_fixed_roi_lymphnode, path_fixed.as_posix(
    ) + f"/{self.annotation_fixed_roi_lymphnode.GetName()}.mrk.json")
    slicer.util.saveNode(self.annotation_moving_roi_lymphnode, path_moving.as_posix(
    ) + f"/{self.annotation_moving_roi_lymphnode.GetName()}.mrk.json")
    with open(path_fixed.as_posix() + "/lymphnode_size_change.txt", "w") as f:
        f.write(str(self.annotation_lymphnode_size))

    slicer.util.saveNode(self.annotation_fixed_points, path_fixed.as_posix(
    ) + f"/{self.annotation_fixed_points.GetName()}.mrk.json")
    slicer.util.saveNode(self.annotation_moving_points, path_moving.as_posix(
    ) + f"/{self.annotation_fixed_points.GetName()}.mrk.json")

    with open(path_fixed.as_posix() + "/recurrence_exists.txt", "w") as f:
        f.write(str(self.annotation_fixed_roi_recurrence is not None))

    if self.annotation_fixed_roi_recurrence is not None:
        slicer.util.saveNode(self.annotation_fixed_roi_recurrence, path_fixed.as_posix(
        ) + f"/{self.annotation_fixed_roi_recurrence.GetName()}.mrk.json")

    self.annotations_already_saved = True

    # show message with Ok only that saving is done
    utils.show_info_popup("Annotations saved")


def on_clear_annotations(self: "registrationViewerWidget") -> None:
    if not self.annotations_already_saved:
        if not utils.show_warning_popup("Annotations not saved yet.",
                                        "Do you want to clear them?"):
            return
    else:
        if not utils.show_warning_popup("Annotations already saved.",
                                        "Do you want to clear them?"):
            return

    if self.annotation_fixed_roi_lymphnode is not None:
        slicer.mrmlScene.RemoveNode(self.annotation_fixed_roi_lymphnode)
        self.annotation_fixed_roi_lymphnode = None

    if self.annotation_moving_roi_lymphnode is not None:
        slicer.mrmlScene.RemoveNode(self.annotation_moving_roi_lymphnode)
        self.annotation_moving_roi_lymphnode = None

    if self.annotation_fixed_points is not None:
        slicer.mrmlScene.RemoveNode(self.annotation_fixed_points)
        self.annotation_fixed_points = None

    if self.annotation_moving_points is not None:
        slicer.mrmlScene.RemoveNode(self.annotation_moving_points)
        self.annotation_moving_points = None

    if self.annotation_fixed_roi_recurrence is not None:
        slicer.mrmlScene.RemoveNode(self.annotation_fixed_roi_recurrence)
        self.annotation_fixed_roi_recurrence = None

    self.annotations_already_saved = False

    # set all checkboxes to false
    self.ui_sub_5.lymphnodeRoiFixedCheckbox.setChecked(False)
    self.ui_sub_5.lymphnodeRoiMovingCheckbox.setChecked(False)

    self.ui_sub_5.a_vertebralis_r_PointFixedCheckbox.setChecked(False)
    self.ui_sub_5.a_vertebralis_r_PointMovingCheckbox.setChecked(False)
    self.ui_sub_5.a_vertebralis_l_PointFixedCheckbox.setChecked(False)
    self.ui_sub_5.a_vertebralis_l_PointMovingCheckbox.setChecked(False)
    self.ui_sub_5.a_carotisexterna_r_PointFixedCheckbox.setChecked(False)
    self.ui_sub_5.a_carotisexterna_r_PointMovingCheckbox.setChecked(False)
    self.ui_sub_5.a_carotisexterna_l_PointFixedCheckbox.setChecked(False)
    self.ui_sub_5.a_carotisexterna_l_PointMovingCheckbox.setChecked(False)

    self.ui_sub_5.recurrenceRoiFixedCheckbox.setChecked(False)
    self.ui_sub_5.recurrencePresentCheckBox.setChecked(False)


def on_add_roi_lymphnode(self: "registrationViewerWidget",
                         image: Literal['fixed', 'moving']) -> None:

    if image not in ['fixed', 'moving']:
        raise ValueError("image must be either 'fixed' or 'moving'")

    if image == 'fixed':
        volume_name = self.node_fixed.GetName()
        views = self.views_first_row
        node_annotation = self.annotation_fixed_roi_lymphnode
    else:
        volume_name = self.node_moving.GetName()
        views = self.views_second_row
        node_annotation = self.annotation_moving_roi_lymphnode

    name = str("roi_lymphnode_" + volume_name)

    if node_annotation is not None:
        if utils.show_warning_popup(f"ROI {name.capitalize()} already exists",
                                    "Do you want to overwrite it?"):
            slicer.mrmlScene.RemoveNode(
                node_annotation)
            if image == 'moving':
                self.ui_sub_5.lymphnode_dropdown.setEnabled(False)
        else:
            return

    new_annotation = slicer.mrmlScene.AddNewNodeByClass(
        "vtkMRMLMarkupsROINode", name)

    view_logic.configure_roi(new_annotation, views)

    if image == 'fixed':
        self.annotation_fixed_roi_lymphnode = new_annotation
        self.ui_sub_5.lymphnodeRoiFixedCheckbox.setChecked(True)
        self.ui_sub_5.lymphnode_dropdown.setEnabled(True)
    else:
        self.annotation_moving_roi_lymphnode = new_annotation
        self.ui_sub_5.lymphnodeRoiMovingCheckbox.setChecked(True)


def on_lymphnode_size(self: "registrationViewerWidget") -> None:

    if self.ui_sub_5.lymphnode_dropdown.currentText == "Size increased":
        self.annotation_lymphnode_size = "Size increased"
    elif self.ui_sub_5.lymphnode_dropdown.currentText == "Size decreased":
        self.annotation_lymphnode_size = "Size decreased"
    elif self.ui_sub_5.lymphnode_dropdown.currentText == "Size same":
        self.annotation_lymphnode_size = "Size same"
    else:
        raise ValueError("Unknown lymphnode size")


def add_point_list(self: "registrationViewerWidget") -> None:
    if self.annotation_fixed_points is None:

        self.annotation_fixed_points = slicer.mrmlScene.AddNewNodeByClass(
            "vtkMRMLMarkupsFiducialNode", f"points_{self.node_fixed.GetName()}")

        self.annotation_fixed_points.GetDisplayNode().SetGlyphScale(1)
        self.annotation_fixed_points.GetDisplayNode().SetTextScale(2)

    if self.annotation_moving_points is None:
        self.annotation_moving_points = slicer.mrmlScene.AddNewNodeByClass(
            "vtkMRMLMarkupsFiducialNode", f"points_{self.node_moving.GetName()}")

        self.annotation_moving_points.GetDisplayNode().SetGlyphScale(1)
        self.annotation_moving_points.GetDisplayNode().SetTextScale(2)


def on_add_annotation_point_fixed(
        self: "registrationViewerWidget",
        point_type: tasks.Task
) -> None:

    add_point_list(self)

    volume_name = self.node_fixed.GetName()

    name = "point_" + point_type.value + '_' + volume_name

    if utils.has_control_point_with_name(self.annotation_fixed_points, name):
        if utils.show_warning_popup(f"Point {point_type.value.capitalize()} already exists",
                                    "Do you want to overwrite it?"):
            utils.remove_control_point_by_name(self.annotation_fixed_points,
                                               name)
        else:
            return

    pos = [view_logic.get_view_offset(view) for view in self.views_first_row]  # nopep8

    self.annotation_fixed_points.AddControlPointWorld([-pos[2], pos[1], pos[0]],
                                                      name)

    if point_type == tasks.Task.A_VERTEBRALIS_R:
        self.ui_sub_5.a_vertebralis_r_PointFixedCheckbox.setChecked(True)
    elif point_type == tasks.Task.A_VERTEBRALIS_L:
        self.ui_sub_5.a_vertebralis_l_PointFixedCheckbox.setChecked(True)
    elif point_type == tasks.Task.A_CAROTISEXTERNA_R:
        self.ui_sub_5.a_carotisexterna_r_PointFixedCheckbox.setChecked(True)
    else:
        self.ui_sub_5.a_carotisexterna_l_PointFixedCheckbox.setChecked(True)

    utils.show_node_only_in_views(self.annotation_fixed_points,
                                  self.views_first_row)


def on_add_annotation_point_moving(
        self: "registrationViewerWidget",
        point_type: tasks.Task
) -> None:

    add_point_list(self)

    volume_name = self.node_moving.GetName()

    name = "point_" + point_type.value + '_' + volume_name

    if utils.has_control_point_with_name(self.annotation_moving_points, name):
        if utils.show_warning_popup(f"Point {point_type.value.capitalize()} already exists",
                                    "Do you want to overwrite it?"):
            utils.remove_control_point_by_name(self.annotation_moving_points,
                                               name)
        else:
            return

    pos = [view_logic.get_view_offset(view) for view in self.views_second_row]  # nopep8

    self.annotation_moving_points.AddControlPointWorld([-pos[2], pos[1], pos[0]],
                                                       name)

    if point_type == tasks.Task.A_VERTEBRALIS_R:
        self.ui_sub_5.a_vertebralis_r_PointMovingCheckbox.setChecked(True)
    elif point_type == tasks.Task.A_VERTEBRALIS_L:
        self.ui_sub_5.a_vertebralis_l_PointMovingCheckbox.setChecked(True)
    elif point_type == tasks.Task.A_CAROTISEXTERNA_R:
        self.ui_sub_5.a_carotisexterna_r_PointMovingCheckbox.setChecked(True)
    else:
        self.ui_sub_5.a_carotisexterna_l_PointMovingCheckbox.setChecked(True)

    utils.show_node_only_in_views(self.annotation_moving_points,
                                  self.views_second_row)


def on_recurrence_present(self: "registrationViewerWidget") -> None:

    if self.ui_sub_5.recurrencePresentCheckBox.isChecked():
        self.ui_sub_5.addRecurrenceRoiFixed.setEnabled(True)
        return

    # trying to uncheck - only allow with warning
    if self.ui_sub_5.recurrencePresentCheckBox.isChecked() is False:
        if self.annotation_fixed_roi_recurrence is None:
            self.ui_sub_5.addRecurrenceRoiFixed.setEnabled(False)
        else:
            if utils.show_warning_popup(f"You alreday created a ROI for the recurrence.",
                                        "Do you want to remove it?"):
                slicer.mrmlScene.RemoveNode(
                    self.annotation_fixed_roi_recurrence)
                self.annotation_fixed_roi_recurrence = None
                self.ui_sub_5.addRecurrenceRoiFixed.setEnabled(False)
            else:
                self.ui_sub_5.recurrencePresentCheckBox.setChecked(True)
                self.ui_sub_5.addRecurrenceRoiFixed.setEnabled(True)


def on_add_roi_recurrence(self: "registrationViewerWidget") -> None:

    name = str("roi_recurrence_" + self.node_moving.GetName())

    if self.annotation_fixed_roi_recurrence is not None:
        if utils.show_warning_popup(f"ROI {name.capitalize()} already exists",
                                    "Do you want to overwrite it?"):
            slicer.mrmlScene.RemoveNode(
                self.annotation_fixed_roi_recurrence)
        else:
            return

    self.annotation_fixed_roi_recurrence = slicer.mrmlScene.AddNewNodeByClass(
        "vtkMRMLMarkupsROINode", name)

    view_logic.configure_roi(
        self.annotation_fixed_roi_recurrence, self.views_first_row)

    self.ui_sub_5.recurrenceRoiFixedCheckbox.setChecked(True)


def on_set_annotations_visibility(self: "registrationViewerWidget",
                                  visibility: bool) -> None:

    for annotation in [self.annotation_fixed_roi_lymphnode,
                       self.annotation_moving_roi_lymphnode,
                       self.annotation_fixed_points,
                       self.annotation_moving_points,
                       self.annotation_fixed_roi_recurrence]:
        if annotation is not None:
            annotation.GetDisplayNode().SetVisibility(visibility)


def on_jumpt_to_slice_idx_fixed(self: "registrationViewerWidget") -> None:

    jumpt_to_slice_idx(self.node_fixed,
                       int(self.ui_sub_5.slice_idx_fixed_TextEdit.toPlainText()),
                       self.views_first_row)


def on_jumpt_to_slice_idx_moving(self: "registrationViewerWidget") -> None:
    jumpt_to_slice_idx(self.node_moving,
                       int(self.ui_sub_5.slice_idx_moving_TextEdit.toPlainText()),
                       self.views_second_row)


def jumpt_to_slice_idx(volume_node, slice_idx, views: List[str]):

    # Ensure that the volume has image data.
    imageData = volume_node.GetImageData()
    if not imageData:
        raise ValueError(
            "The provided volume node does not contain image data.")

    # Get the dimensions of the volume (I, J, K)
    dims = imageData.GetDimensions()  # (nx, ny, nz)

    # Use the center of the slice in I and J directions.
    centerI = dims[0] / 2.0
    centerJ = dims[1] / 2.0

    # Clamp the provided slice index to a valid range.
    K = max(0, min(slice_idx, dims[2] - 1))

    # Create a homogeneous voxel coordinate [I, J, K, 1]
    voxelCoord = [centerI, centerJ, K, 1]

    # Get the IJK-to-RAS transformation matrix from the volume node.
    ijkToRAS = vtk.vtkMatrix4x4()
    volume_node.GetIJKToRASMatrix(ijkToRAS)

    # Transform the voxel coordinate to RAS.
    rasCoord = [0, 0, 0, 0]
    for i in range(4):
        rasCoord[i] = (ijkToRAS.GetElement(i, 0) * voxelCoord[0] +
                       ijkToRAS.GetElement(i, 1) * voxelCoord[1] +
                       ijkToRAS.GetElement(i, 2) * voxelCoord[2] +
                       ijkToRAS.GetElement(i, 3) * voxelCoord[3])

    position = rasCoord[:3]

    layoutManager = slicer.app.layoutManager()

    for view in views:
        sliceWidget = layoutManager.sliceWidget(view)
        if not sliceWidget:
            continue

        sliceLogic = sliceWidget.sliceLogic()
        sliceNode = sliceLogic.GetSliceNode()

        # Get the SliceToRAS matrix for the current slice view.
        sliceToRAS = sliceNode.GetSliceToRAS()

        # Typically, the third column of the SliceToRAS matrix is the slice normal.
        normal = [sliceToRAS.GetElement(0, 2),
                  sliceToRAS.GetElement(1, 2),
                  sliceToRAS.GetElement(2, 2)]

        # Compute the offset as the dot product of the slice normal with the target RAS position.
        offset = normal[0]*position[0] + normal[1] * \
            position[1] + normal[2]*position[2]

        # Set the computed offset for this view.
        view_logic.set_view_offset(view, offset)

    return position
