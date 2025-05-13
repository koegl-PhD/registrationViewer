from collections import defaultdict
from dataclasses import dataclass, field
import json
import os
from typing import List, Optional, Tuple, TYPE_CHECKING

from typing import List, Tuple

import qt
import slicer

from registrationViewerLib import tasks, utils, tasks_ui_logic

path = r"registrationViewer/Resources/example_study/data_master.json"


if TYPE_CHECKING:
    from ..registrationViewer import registrationViewerWidget


@dataclass
class StudyData:
    path: str
    data: dict = field(init=False)
    patient_to_rads: dict = field(init=False, default_factory=dict)

    def __post_init__(self):
        with open(self.path, "r") as f:
            self.data = json.load(f)

        self.__dict__.update(self.data)

    def save(self, json_path=None):
        if json_path is None:
            json_path = self.path

        with open(json_path, "w") as f:
            json.dump(self.data, f, indent=4)

    def patient_list(self, rad_id: str) -> List[Tuple[utils.TransformType, str]]:

        participant = self.participants.get(rad_id, None)
        if participant is None:
            raise ValueError(f"Rad id {rad_id} not found in data")

        result = []

        for comb in participant["patient_transform_combinations"]:
            result.append((utils.TransformType(comb[0]), comb[1]))

        return result


def load_study_volumes(self: "registrationViewerWidget",
                       path_case: str) -> None:

    slicer.progressWindow = slicer.util.createProgressDialog()
    slicer.progressWindow.show()
    slicer.progressWindow.activateWindow()
    slicer.progressWindow.setValue(0)
    slicer.progressWindow.setLabelText(
        f"Loading data...")
    slicer.app.processEvents()

    path_volume_fixed, path_volume_moving, \
        _, _, \
        path_transform_fixed, path_transform_moving, \
        path_deformation = utils.get_paths_to_load(path_case)

    utils.update_progress_window(0, f"Loading data...")
    node_volume_fixed = slicer.util.loadVolume(path_volume_fixed,
                                               {'show': False})
    name_volume_fixed = os.path.basename(
        path_volume_fixed).replace(".nii.gz", "")
    node_volume_fixed.SetName(name_volume_fixed)

    utils.update_progress_window(10, f"Loading data...")
    node_volume_moving = slicer.util.loadVolume(path_volume_moving,
                                                {'show': False})
    name_volume_moving = os.path.basename(
        path_volume_moving).replace(".nii.gz", "")
    node_volume_moving.SetName(name_volume_moving)

    utils.update_progress_window(40, f"Loading data...")
    self.node_transform_fixed = slicer.util.loadTransform(path_transform_fixed,
                                                          {'show': False})[1]
    name_transform_fixed = os.path.basename(
        path_transform_fixed).replace(".h5", "")
    self.node_transform_fixed.SetName(name_transform_fixed)

    utils.update_progress_window(50, f"Loading data...")
    self.node_transform_moving = slicer.util.loadTransform(path_transform_moving,
                                                           {'show': False})[1]
    name_transform_moving = os.path.basename(
        path_transform_moving).replace(".h5", "")
    self.node_transform_moving.SetName(name_transform_moving)

    utils.update_progress_window(60, f"Loading data...")
    node_deformation = slicer.util.loadTransform(path_deformation,
                                                 {'show': False})[1]

    if path_deformation is None:
        node_deformation = slicer.mrmlScene.AddNewNodeByClass(
            "vtkMRMLLinearTransformNode")
    else:
        node_deformation = slicer.util.loadTransform(path_deformation,
                                                     {'show': False})[1]

    utils.update_progress_window(100, f"Loading data...")

    self.ui_sub_3.inputSelector_fixed.setCurrentNode(
        node_volume_fixed)
    self.ui_sub_3.inputSelector_moving.setCurrentNode(
        node_volume_moving)
    self.ui_sub_3.inputSelector_transformation.setCurrentNode(
        node_deformation)

    slicer.progressWindow.close()


def load_ground_truth_annotations(self: "registrationViewerWidget",
                                  patient_name: str,
                                  volume_name: str):
    slicer.progressWindow = slicer.util.createProgressDialog()
    slicer.progressWindow.show()
    slicer.progressWindow.activateWindow()
    slicer.progressWindow.setValue(50)
    slicer.progressWindow.setLabelText(
        f"Loading ground truth annotations...")
    slicer.app.processEvents()

    study_name = volume_name.split('~')[1]

    path_annotations = os.path.join(self.study_data_master.path_study_input_cases,
                                    patient_name,
                                    "preprocessed",
                                    study_name,
                                    "annotations")
    path_points = os.path.join(path_annotations,
                               f"points_{volume_name}.mrk.json")
    points_node = slicer.util.loadMarkups(path_points)
    points_node.SetName(os.path.basename(path_points).replace(".mrk.json", ""))
    points_node_name = points_node.GetName()

    path_lymphnode = os.path.join(path_annotations,
                                  f"roi_lymphnode_{volume_name}.mrk.json")
    lymphnode = slicer.util.loadMarkups(path_lymphnode)
    lymphnode.SetName('l')
    lymphnode.LockedOn()
    utils.show_node_only_in_views(lymphnode,
                                  self.views_second_row)
    lymphnode.GetDisplayNode().SetInteractionHandleScale(0)
    lymphnode.GetDisplayNode().SetFillVisibility(False)
    lymphnode.GetDisplayNode().SetSelectedColor(utils.Colors.RED.value)

    with open(os.path.join(path_annotations, "lymphnode_info.txt"), "r") as f:
        self.study_gt_lymphnode_description = f.read().split(
            "Description:")[-1].strip()

    with open(os.path.join(path_annotations, "recurrence.txt")) as f:
        self.study_gt_recurrence_description = f.read()

    for task_name in tasks.TASK_ORDER.values():
        if task_name == tasks.Task.LYMPH_NODE:
            # it is not a point, but a ROI so we skip
            self.study_node_groundtruth_points[task_name] = lymphnode
            continue
        if task_name == tasks.Task.RECURRENCE:
            # we don't need to show it so continue
            continue

        current_point_name = points_node_name.replace(
            'points', f"point_{task_name.value}")
        current_point_idx = utils.get_control_point_idx_by_name(points_node,
                                                                current_point_name)
        if current_point_idx == -1:
            slicer.util.errorDisplay(f"Point {current_point_name} not found")
            continue

        # create new point with new name and position from current index
        new_point = slicer.mrmlScene.AddNewNodeByClass(
            "vtkMRMLMarkupsFiducialNode")
        current_position = points_node.GetNthControlPointPosition(
            current_point_idx)
        new_point.AddControlPoint(current_position, 'p')

        new_point.LockedOn()

        new_point.SetName(current_point_name)

        utils.show_node_only_in_views(new_point,
                                      self.views_second_row)
        new_point.GetDisplayNode().SetSelectedColor(utils.Colors.BLUE.value)
        new_point.GetDisplayNode().SetGlyphScale(1.0)

        self.study_node_groundtruth_points[task_name] = new_point

    slicer.mrmlScene.RemoveNode(points_node)

    slicer.progressWindow.close()


def save_annotations(self: "registrationViewerWidget",
                     specific_task: Optional[tasks.Task] = None,
                     serialise_to_log: Optional[bool] = False,
                     final_save: bool = False) -> None:

    if self.current_task_idx < 0:
        return

    path_patient = f"{self.study_data_master.path_study_output}{self.current_radiologist_id}/{self.current_patient_name}"  # nopep8
    if not os.path.exists(path_patient):
        os.makedirs(path_patient)

    for task in tasks.TASK_ORDER.values():
        if specific_task is None or specific_task == task:

            additional_info = None

            if task == tasks.Task.LYMPH_NODE:
                additional_info = {"path": path_patient + "/lymphnode_size.txt",
                                   "content": self.study_lymphnode_size}
            elif task == tasks.Task.RECURRENCE:
                additional_info = {"path": path_patient + "/recurrence_present.txt",
                                   "content": str(self.study_recurrence_present)}

            tasks_ui_logic.save_point(self,
                                      path_patient,
                                      task,
                                      self.study_node_points,
                                      additional_info=additional_info,
                                      serialise_to_log=serialise_to_log,
                                      final_save=final_save)


def clear_annotations(self: "registrationViewerWidget") -> None:
    if self.current_task_idx <= 0:
        return

    # remove user annotations
    for task, point in self.study_node_points.items():
        if point is not None:
            slicer.mrmlScene.RemoveNode(point)
            self.study_node_points[task] = None
    # remove ground truth annotations
    for task, point in self.study_node_groundtruth_points.items():
        if point is not None:
            slicer.mrmlScene.RemoveNode(point)
            self.study_node_groundtruth_points[task] = None

    self.study_lymphnode_size = "Size same"
    self.study_recurrence_present = False

    self.ui_sub_6.study_checkbox.blockSignals(True)
    self.ui_sub_6.study_checkbox.setChecked(False)
    self.ui_sub_6.study_checkbox.blockSignals(False)
    self.ui_sub_6.study_dropdown.setCurrentText('Size same')


def hide_module_parts_for_user_study(self: "registrationViewerWidget") -> None:
    self.ui_sub_1.simple_ui_button.setHidden(False)
    self.ui_sub_2.studyCollapsibleButton.setHidden(True)
    self.ui_sub_3.inputsCollapsibleButton.setHidden(True)
    self.ui_sub_4.controlsCollapsibleButton.setHidden(True)
    self.ui_sub_5.annotationsCollapsibleButton.setHidden(True)
    self.loadingCollapsible.setHidden(True)

    self.ui_sub_6.current_case_label.setVisible(False)
    self.ui_sub_6.Form_user_study.setHidden(False)
    self.ui_sub_6.study_center_on_user_point_button.setVisible(False)
    self.ui_sub_6.study_center_on_gt_point_button.setVisible(False)


def show_module_parts_for_user_study(self: "registrationViewerWidget") -> None:
    self.ui_sub_2.studyCollapsibleButton.setHidden(False)
    self.ui_sub_3.inputsCollapsibleButton.setHidden(False)
    self.ui_sub_4.controlsCollapsibleButton.setHidden(False)
    self.ui_sub_5.annotationsCollapsibleButton.setHidden(False)
    self.loadingCollapsible.setHidden(False)

    self.ui_sub_6.Form_user_study.setHidden(True)
