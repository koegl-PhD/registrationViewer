import json
import os

from typing import Literal, TYPE_CHECKING

import slicer
import qt

from registrationViewerLib import tasks, utils, view_logic

if TYPE_CHECKING:
    from ..registrationViewer import registrationViewerWidget


def set_connections(self: "registrationViewerWidget") -> None:
    self.ui_sub_5.saveAnnotations.connect("clicked(bool)",
                                          lambda: on_save_annotations(self))
    self.ui_sub_5.clearAnnotations.connect("clicked(bool)",
                                           lambda: on_clear_annotations(self))

    self.ui_sub_5.addLymphnodeRoiFixed.connect("clicked(bool)",
                                               lambda: on_add_roi_lymphnode(self, 'fixed'))
    self.ui_sub_5.addLymphnodeRoiMoving.connect("clicked(bool)",
                                                lambda: on_add_roi_lymphnode(self, 'moving'))
    self.ui_sub_5.increasedLymphnodeCheckBox.toggled.connect(
        on_lymphnode_increased)

    self.ui_sub_5.addCarotisgabelPointFixed.connect("clicked(bool)",
                                                    lambda: on_add_annotation_point_fixed(self, 'carotisgabel'))
    self.ui_sub_5.addCarotisgabelPointMoving.connect("clicked(bool)",
                                                     lambda: on_add_annotation_point_moving(self, 'carotisgabel'))
    self.ui_sub_5.addAbgangavertebralisPointFixed.connect("clicked(bool)",
                                                          lambda: on_add_annotation_point_fixed(self, 'abgangavertebralis'))
    self.ui_sub_5.addAbgangavertebralisPointMoving.connect("clicked(bool)",
                                                           lambda: on_add_annotation_point_moving(self, 'abgangavertebralis'))

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
    temp = name_volume_fixed.split("~")
    name_patient = temp[0]

    # check if all annotations are present
    if self.annotation_fixed_roi_lymphnode is None:
        slicer.util.errorDisplay("Please add fixed lymphnode ROI")
        return
    if self.annotation_moving_roi_lymphnode is None:
        slicer.util.errorDisplay("Please add moving lymphnode ROI")
        return

    if self.annotation_fixed_points is None or self.annotation_fixed_points.GetNumberOfControlPoints() == 0:
        slicer.util.errorDisplay("Please add fixed annotation points")
        return

    if self.annotation_moving_points is None or self.annotation_moving_points.GetNumberOfControlPoints() == 0:
        slicer.util.errorDisplay("Please add fixed annotation points")
        return

    if not utils.has_control_point_with_name(self.annotation_fixed_points, f"point_carotisgabel_{name_volume_fixed}"):
        slicer.util.errorDisplay(
            "Please add carotisgabel point for fixed volume")
        return
    if not utils.has_control_point_with_name(self.annotation_moving_points, f"point_carotisgabel_{name_volume_moving}"):
        slicer.util.errorDisplay(
            "Please add carotisgabel point for moving volume")
        return

    if not utils.has_control_point_with_name(self.annotation_fixed_points, f"point_abgangavertebralis_{name_volume_fixed}"):
        slicer.util.errorDisplay(
            "Please add abgangavertebralis point for fixed volume")
        return
    if not utils.has_control_point_with_name(self.annotation_moving_points, f"point_abgangavertebralis_{name_volume_moving}"):
        slicer.util.errorDisplay(
            "Please add abgangavertebralis point for moving volume")
        return

    if self.annotation_moving_roi_lymphnode and self.annotation_bool_lymphnode_increased is False:
        if not utils.show_warning_popup(f"Did you check for increased lymphnode size?",
                                        "(Click OK to continue saving)"):
            return

    if self.annotation_fixed_roi_recurrence is None and self.ui_sub_5.recurrencePresentCheckBox.isChecked():
        utils.show_info_popup(
            f"You marked that there is a recurrence, but did not add a ROI for it.\nExiting saving.")
        return

    if self.annotation_fixed_roi_recurrence is None:
        if not utils.show_warning_popup(f"Did you check for recurrence?",
                                        "(Click OK to continue saving)"):
            return

    if not utils.show_warning_popup("Have you set the window, level and threshold?",
                                    "(Click OK to continue saving)"):
        return

    path_patient = self.annotations_save_path + name_patient
    if not os.path.exists(path_patient):
        os.makedirs(path_patient)

    slicer.util.saveNode(self.annotation_fixed_roi_lymphnode, path_patient +
                         f"/{self.annotation_fixed_roi_lymphnode.GetName()}.mrk.json")
    slicer.util.saveNode(self.annotation_moving_roi_lymphnode, path_patient +
                         f"/{self.annotation_moving_roi_lymphnode.GetName()}.mrk.json")
    with open(path_patient + f"/lymphnode_increased.txt", "w") as f:
        f.write(str(self.annotation_bool_lymphnode_increased))

    slicer.util.saveNode(self.annotation_fixed_points, path_patient +
                         f"/{self.annotation_fixed_points.GetName()}.mrk.json")
    slicer.util.saveNode(self.annotation_moving_points, path_patient +
                         f"/{self.annotation_fixed_points.GetName()}.mrk.json")

    with open(path_patient + f"/recurrence_exists.txt", "w") as f:
        f.write(str(self.annotation_fixed_roi_recurrence is not None))

    if self.annotation_fixed_roi_recurrence is not None:
        slicer.util.saveNode(self.annotation_fixed_roi_recurrence, path_patient +
                             f"/{self.annotation_fixed_roi_recurrence.GetName()}.mrk.json")

    disp_node_fixed = self.node_fixed.GetDisplayNode()
    w_l_t_fixed = {'window': disp_node_fixed.GetWindow(),
                   'level': disp_node_fixed.GetLevel(),
                   'threshold': [disp_node_fixed.GetLowerThreshold(), disp_node_fixed.GetUpperThreshold()]}
    with open(path_patient + f"/window_level_threshold_{self.node_fixed.GetName()}.json", "w") as f:
        json.dump(w_l_t_fixed, f)

    disp_node_moving = self.node_moving.GetDisplayNode()
    w_l_t_moving = {'window': disp_node_moving.GetWindow(),
                    'level': disp_node_moving.GetLevel(),
                    'threshold': [disp_node_moving.GetLowerThreshold(), disp_node_moving.GetUpperThreshold()]}
    with open(path_patient + f"/window_level_threshold_{self.node_moving.GetName()}.json", "w") as f:
        json.dump(w_l_t_moving, f)

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
        self.ui_sub_5.lymphnodeRoiFixedCheckbox.setChecked(False)

    if self.annotation_moving_roi_lymphnode is not None:
        slicer.mrmlScene.RemoveNode(self.annotation_moving_roi_lymphnode)
        self.annotation_moving_roi_lymphnode = None
        self.ui_sub_5.increasedLymphnodeCheckBox.setEnabled(False)
        self.ui_sub_5.increasedLymphnodeCheckBox.setChecked(False)
        self.ui_sub_5.lymphnodeRoiMovingCheckbox.setChecked(False)

    if self.annotation_fixed_points is not None:
        slicer.mrmlScene.RemoveNode(self.annotation_fixed_points)
        self.annotation_fixed_points = None
        self.ui_sub_5.carotisgabelPointFixedCheckbox.setChecked(False)
        self.ui_sub_5.abgangavertebralisPointFixedCheckbox.setChecked(
            False)

    if self.annotation_moving_points is not None:
        slicer.mrmlScene.RemoveNode(self.annotation_moving_points)
        self.annotation_moving_points = None
        self.ui_sub_5.carotisgabelPointMovingCheckbox.setChecked(False)
        self.ui_sub_5.abgangavertebralisPointMovingCheckbox.setChecked(
            False)

    if self.annotation_fixed_roi_recurrence is not None:
        slicer.mrmlScene.RemoveNode(self.annotation_fixed_roi_recurrence)
        self.annotation_fixed_roi_recurrence = None
        self.ui_sub_5.recurrencePresentCheckBox.setChecked(False)
        self.ui_sub_5.recurrenceRoiFixedCheckbox.setChecked(False)
        self.ui_sub_5.addRecurrenceRoiFixed.setEnabled(False)

    self.annotations_already_saved = False


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
                self.ui_sub_5.increasedLymphnodeCheckBox.setEnabled(False)
        else:
            return

    new_annotation = slicer.mrmlScene.AddNewNodeByClass(
        "vtkMRMLMarkupsROINode", name)

    view_logic.configure_roi(new_annotation, views)

    if image == 'fixed':
        self.annotation_fixed_roi_lymphnode = new_annotation
        self.ui_sub_5.lymphnodeRoiFixedCheckbox.setChecked(True)
    else:
        self.annotation_moving_roi_lymphnode = new_annotation
        self.ui_sub_5.increasedLymphnodeCheckBox.setEnabled(True)
        self.ui_sub_5.lymphnodeRoiMovingCheckbox.setChecked(True)


def on_lymphnode_increased(self: "registrationViewerWidget") -> None:
    self.annotation_bool_lymphnode_increased = not self.annotation_bool_lymphnode_increased


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
        point_name: Literal['carotisgabel', 'abgangavertebralis']
) -> None:

    add_point_list(self)

    volume_name = self.node_fixed.GetName()

    name = "point_" + point_name + '_' + volume_name

    if utils.has_control_point_with_name(self.annotation_fixed_points, name):
        if utils.show_warning_popup(f"Point {point_name.capitalize()} already exists",
                                    "Do you want to overwrite it?"):
            utils.remove_control_point_by_name(self.annotation_fixed_points,
                                               name)
        else:
            return

    pos = [view_logic.get_view_offset(view) for view in self.views_first_row]  # nopep8

    self.annotation_fixed_points.AddControlPointWorld([-pos[2], pos[1], pos[0]],
                                                      name)

    if point_name == 'carotisgabel':
        self.ui_sub_5.carotisgabelPointFixedCheckbox.setChecked(True)
    else:
        self.ui_sub_5.abgangavertebralisPointFixedCheckbox.setChecked(True)

    utils.show_node_only_in_views(self.annotation_fixed_points,
                                  self.views_first_row)


def on_add_annotation_point_moving(
        self: "registrationViewerWidget",
        point_name: Literal['carotisgabel', 'abgangavertebralis']
) -> None:

    add_point_list(self)

    volume_name = self.node_moving.GetName()

    name = "point_" + point_name + '_' + volume_name

    if utils.has_control_point_with_name(self.annotation_moving_points, name):
        if utils.show_warning_popup(f"Point {point_name.capitalize()} already exists",
                                    "Do you want to overwrite it?"):
            utils.remove_control_point_by_name(self.annotation_moving_points,
                                               name)
        else:
            return

    pos = [view_logic.get_view_offset(view) for view in self.views_second_row]  # nopep8

    self.annotation_moving_points.AddControlPointWorld([-pos[2], pos[1], pos[0]],
                                                       name)

    if point_name == 'carotisgabel':
        self.ui_sub_5.carotisgabelPointMovingCheckbox.setChecked(True)
    else:
        self.ui_sub_5.abgangavertebralisPointMovingCheckbox.setChecked(
            True)

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
