from dataclasses import dataclass, field
import json
import logging
import os
import random

from typing import List, Optional, Tuple, TYPE_CHECKING

import slicer

from registrationViewerLib import tasks, utils, tasks_ui_logic
from registrationViewerLib.custom_logging import log, LogType


if TYPE_CHECKING:
    from ..registrationViewer import registrationViewerWidget


@dataclass
class StudyData:
    path: str
    data: dict = field(init=False)

    case_task_transformation_map: dict[str,
                                       List[Tuple[str, str, str]]] = field(init=False)

    def __post_init__(self):
        with open(self.path, "r") as f:
            self.data = json.load(f)

        self.__dict__.update(self.data)

        self._create_case_task_transformation_map(randomise=False)

    def save(self, json_path=None):
        if json_path is None:
            json_path = self.path

        with open(json_path, "w") as f:
            json.dump(self.data, f, indent=4)

    def patient_list(self, rad_id: str) -> List[Tuple[utils.TransformType, str]]:

        participant = self.participants.get(rad_id, None)
        if participant is None:
            raise ValueError(f"Rad id {rad_id} not found in data")

        return participant["patients"]

    def number_of_tasks(self, rad_id: str) -> int:
        participant = self.participants.get(rad_id, None)
        if participant is None:
            raise ValueError(f"Rad id {rad_id} not found in data")

        return len(self.case_task_transformation_map[rad_id])

    def _create_case_task_transformation_map(self, randomise: bool) -> None:
        """
        Create a mapping of task to transformation for the random case.
        This is used to create the random case in the study.
        """

        random.seed(42)

        self.case_task_transformation_map = {}

        for rad_id, rad_content in self.participants.items():

            temp_rad_map = []

            for patient in rad_content["patients"]:

                for transform in utils.TransformType:

                    for task in tasks.TASK_ORDER.values():

                        # if task != tasks.Task.RECURRENCE:
                        #     continue

                        if patient == "YPEbc0OFC8I" and transform != utils.TransformType.NONE:
                            continue

                        if patient == "yIt7Z7VHXU0" and transform != utils.TransformType.NONLINEAR:
                            continue

                        temp_rad_map.append(
                            (patient, task.value, transform.value))

            if randomise:
                random.shuffle(temp_rad_map)

            self.case_task_transformation_map[rad_id] = temp_rad_map


def load_all_study_data(self: "registrationViewerWidget") -> None:

    log(logging.INFO, LogType.INTERNAL, "Start loading study data")

    fullscreen_block = utils.show_fullscreen_block("", "")

    utils.set_up_progress_window("Loading data...")

    end_percentage = load_study_volumes(self)

    load_ground_truth_annotations(self, end_percentage)

    slicer.progressWindow.close()

    fullscreen_block.close()

    log(logging.INFO, LogType.INTERNAL, "Finished loading study data")


def load_study_volumes(self: "registrationViewerWidget") -> int:

    size = len(self.study_data_master.patient_list(
        self.current_radiologist_id))

    percentage_patient = 0
    for patient_name in self.study_data_master.patient_list(self.current_radiologist_id):

        print(patient_name)

        path_case = f"{self.study_data_master.path_study_input_cases}{patient_name}"

        path_volume_fixed, path_volume_moving, \
            _, _, \
            path_transform_fixed, path_transform_moving, \
            path_deformation = utils.get_paths_to_load(path_case)

        utils.update_progress_window(
            (percentage_patient * 90) / (size), f"Loading data...")
        percentage_patient += 0.2
        node_volume_fixed = slicer.util.loadVolume(path_volume_fixed,
                                                   {'show': False})
        name_volume_fixed = os.path.basename(
            path_volume_fixed).replace(".nii.gz", "")
        node_volume_fixed.SetName(name_volume_fixed)

        utils.update_progress_window(
            (percentage_patient * 90) / (size), f"Loading data...")
        percentage_patient += 0.2
        node_volume_moving = slicer.util.loadVolume(path_volume_moving,
                                                    {'show': False})
        name_volume_moving = os.path.basename(
            path_volume_moving).replace(".nii.gz", "")
        node_volume_moving.SetName(name_volume_moving)

        utils.update_progress_window(
            (percentage_patient * 90) / (size), f"Loading data...")
        percentage_patient += 0.05
        node_transform_fixed = slicer.util.loadTransform(path_transform_fixed,
                                                         {'show': False})[1]
        name_transform_fixed = os.path.basename(
            path_transform_fixed).replace(".h5", "")
        node_transform_fixed.SetName(name_transform_fixed)

        utils.update_progress_window(
            (percentage_patient * 90) / (size), f"Loading data...")
        percentage_patient += 0.05
        node_transform_moving = slicer.util.loadTransform(path_transform_moving,
                                                          {'show': False})[1]
        name_transform_moving = os.path.basename(
            path_transform_moving).replace(".h5", "")
        node_transform_moving.SetName(name_transform_moving)

        utils.update_progress_window(
            (percentage_patient * 90) / (size), f"Loading data...")
        percentage_patient += 0.5
        if path_deformation is None:
            node_deformation = slicer.mrmlScene.AddNewNodeByClass(
                "vtkMRMLLinearTransformNode")
        else:
            # node_deformation = slicer.mrmlScene.AddNewNodeByClass(
            # "vtkMRMLLinearTransformNode")
            node_deformation = slicer.util.loadTransform(path_deformation,
                                                         {'show': False})[1]

        if patient_name not in self.study_loaded_data:
            self.study_loaded_data[patient_name] = {}
        self.study_loaded_data[patient_name]["fixed"] = node_volume_fixed
        self.study_loaded_data[patient_name]["moving"] = node_volume_moving
        self.study_loaded_data[patient_name]["transform_fixed"] = node_transform_fixed
        self.study_loaded_data[patient_name]["transform_moving"] = node_transform_moving
        self.study_loaded_data[patient_name]["deformation"] = node_deformation

        utils.hide_all_volumes_from_views(
            self.views_first_row + self.views_second_row)

    return percentage_patient


def load_ground_truth_annotations(self: "registrationViewerWidget", start_percentage: int) -> None:

    size = len(self.study_data_master.patient_list(
        self.current_radiologist_id))

    percentage_patient = start_percentage

    for patient_name in self.study_data_master.patient_list(self.current_radiologist_id):

        volume_moving_name = self.study_loaded_data[patient_name]["moving"].GetName(
        )
        study_moving_name = volume_moving_name.split('~')[1]

        path_annotations = os.path.join(self.study_data_master.path_study_input_cases,
                                        patient_name,
                                        "preprocessed",
                                        study_moving_name,
                                        "annotations")

        path_points = os.path.join(path_annotations,
                                   f"points_{volume_moving_name}.mrk.json")
        utils.update_progress_window(
            (percentage_patient * 90) / (size))
        percentage_patient += 0.05
        points_node = slicer.util.loadMarkups(path_points)

        points_node.SetName(os.path.basename(
            path_points).replace(".mrk.json", ""))
        points_node_name = points_node.GetName()

        path_lymphnode = os.path.join(path_annotations,
                                      f"roi_lymphnode_{volume_moving_name}.mrk.json")
        utils.update_progress_window(
            (percentage_patient * 90) / (size))
        percentage_patient += 0.05
        lymphnode = slicer.util.loadMarkups(path_lymphnode)
        lymphnode.SetName('l')
        lymphnode.LockedOn()

        lymphnode.GetDisplayNode().SetInteractionHandleScale(0)
        lymphnode.GetDisplayNode().SetFillVisibility(False)
        lymphnode.GetDisplayNode().SetSelectedColor(utils.Colors.RED.value)
        lymphnode.GetDisplayNode().SetVisibility(False)
        utils.show_node_only_in_views(lymphnode,
                                      self.views_second_row)

        with open(os.path.join(path_annotations, "lymphnode_info.txt"), "r") as f:
            self.study_gt_lymphnode_description[patient_name] = f.read().split(
                "Description:")[-1].strip()

        with open(os.path.join(path_annotations, "recurrence.txt")) as f:
            self.study_gt_recurrence_description[patient_name] = f.read()

        for task_name in tasks.TASK_ORDER.values():
            if task_name == tasks.Task.LYMPH_NODE:
                # it is not a point, but a ROI so we skip
                self.study_node_groundtruth_points[patient_name][task_name] = lymphnode
                continue
            if task_name == tasks.Task.RECURRENCE:
                # we don't need to show it so continue
                continue

            current_point_name = points_node_name.replace(
                'points', f"point_{task_name.value}")
            current_point_idx = utils.get_control_point_idx_by_name(points_node,
                                                                    current_point_name)
            if current_point_idx == -1:
                slicer.util.errorDisplay(
                    f"Point {current_point_name} not found")
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
            new_point.SetDisplayVisibility(False)
            new_point.GetDisplayNode().SetSelectedColor(utils.Colors.BLUE.value)
            new_point.GetDisplayNode().SetGlyphScale(1.0)

            if patient_name not in self.study_node_groundtruth_points:
                self.study_node_groundtruth_points[patient_name] = {}

            self.study_node_groundtruth_points[patient_name][task_name] = new_point

        slicer.mrmlScene.RemoveNode(points_node)

    slicer.progressWindow.close()


def save_annotations(self: "registrationViewerWidget",
                     task_type: tasks.Task,
                     serialise_to_log: Optional[bool] = False,
                     final_save: bool = False) -> None:

    if self.current_combination_idx < 0:
        return

    path_patient = f"{self.study_data_master.path_study_output}{self.current_radiologist_id}/{self.current_patient_name}/{self.current_patient_transform_type.value}"  # nopep8

    if not os.path.exists(path_patient):
        os.makedirs(path_patient)

    additional_info = None

    if task_type == tasks.Task.LYMPH_NODE:
        additional_info = {"path": path_patient + "/lymphnode_size.txt",
                           "content": self.study_lymphnode_size}
    elif task_type == tasks.Task.RECURRENCE:
        additional_info = {"path": path_patient + "/recurrence_present.txt",
                           "content": str(self.study_recurrence_present)}

    tasks_ui_logic.save_point(path_patient,
                              task_type,
                              self.study_node_annotation,
                              additional_info=additional_info,
                              serialise_to_log=serialise_to_log,
                              final_save=final_save)


def clear_current_user_annotation(self: "registrationViewerWidget") -> None:

    if self.study_node_annotation is not None:
        slicer.mrmlScene.RemoveNode(self.study_node_annotation)
        self.study_node_annotation = None


def clear_annotations(self: "registrationViewerWidget") -> None:
    if self.current_combination_idx <= 0:
        return

    # remove user annotations
    for task, point in self.study_node_annotation.items():
        if point is not None:
            slicer.mrmlScene.RemoveNode(point)
            self.study_node_annotation = None
    # remove ground truth annotations
    for task, point in self.study_node_groundtruth_points[self.current_patient_name].items():
        if point is not None:
            slicer.mrmlScene.RemoveNode(point)
            self.study_node_groundtruth_points[self.current_patient_name][task] = None

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
