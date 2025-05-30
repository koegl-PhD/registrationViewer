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

        self.dummy_patient_name = "0e5fp8GltvE"

        self._create_case_task_transformation_map(randomise=True)

    def save(self, json_path=None):
        if json_path is None:
            json_path = self.path

        with open(json_path, "w") as f:
            json.dump(self.data, f, indent=4)

    def patient_list(self, rad_id: str) -> List[str]:

        participant = self.participants.get(rad_id, None)
        if participant is None:
            raise ValueError(f"Rad id {rad_id} not found in data")

        return participant["patients"]["negative"].copy() + participant["patients"]["positive"].copy()

    def patient_names_and_paths(self, rad_id: str) -> List[Tuple[str, str]]:
        participant = self.participants.get(rad_id, None)
        if participant is None:
            raise ValueError(f"Rad id {rad_id} not found in data")

        names_and_paths = []

        for present, patients in participant["patients"].items():

            for patient_name in patients:
                p = self.data[f"path_study_input_cases_{present}"]
                names_and_paths.append(
                    (patient_name, f"{p}{patient_name}"))

        return names_and_paths

    def number_of_tasks(self, rad_id: str) -> int:
        participant = self.participants.get(rad_id, None)
        if participant is None:
            raise ValueError(f"Rad id {rad_id} not found in data")

        return len(self.case_task_transformation_map[rad_id])

    def show_training_cases(self, rad_id: str) -> bool:
        """
        Returns whether we should show training cases.
        """

        participant = self.participants.get(rad_id, None)
        if participant is None:
            raise ValueError(f"Rad id {rad_id} not found in data")

        return participant["config"]["show_training_cases"]

    def get_training_case_names(self, rad_id: str) -> List[str]:
        """
        Returns the names of the cases used for training
        """

        if not self.show_training_cases(rad_id):
            return []

        participant = self.participants.get(rad_id, None)
        if participant is None:
            raise ValueError(f"Rad id {rad_id} not found in data")

        # list all folders
        path = self.path_study_training_cases

        if not os.path.exists(path):
            raise FileNotFoundError(
                f"Path {path} does not exist. Please check the study configuration.")

        training_cases = sorted([f for f in os.listdir(
            path) if os.path.isdir(os.path.join(path, f))])

        return training_cases

    def _create_case_task_transformation_map(self, randomise: bool) -> None:
        """
        Create a mapping of task to transformation for the random case.
        This is used to create the random case in the study.
        """

        random.seed(42)

        self.case_task_transformation_map = {}

        for rad_id, rad_content in self.participants.items():

            temp_rad_map = []

            for present in ["positive", "negative"]:

                for patient in rad_content["patients"][present]:

                    for transform in utils.TransformType:

                        for task in tasks.TASK_ORDER.values():

                            if patient == self.dummy_patient_name:
                                continue

                            temp_rad_map.append(
                                (patient, task.value, transform.value))

            if randomise:
                temp_rad_map = utils.shuffle_without_consecutive_ab(
                    temp_rad_map)

            start_and_end_task = []
            for task in tasks.TASK_ORDER.values():
                start_and_end_task.append(
                    (self.dummy_patient_name, task.value, utils.TransformType.NONLINEAR.value))
            random.shuffle(start_and_end_task)

            temp_rad_map = start_and_end_task + temp_rad_map + start_and_end_task

            test_names = self.get_training_case_names(rad_id)
            test_comb_1 = (test_names[0], tasks.Task.TEST_RIGID.value,
                           utils.TransformType.LINEAR.value)
            test_comb_2 = (test_names[1], tasks.Task.TEST_ROTATION.value,
                           utils.TransformType.LINEAR.value)
            test_comb_3 = (test_names[2], tasks.Task.TEST_NONLINEAR.value,
                           utils.TransformType.NONLINEAR.value)

            temp_rad_map.insert(0, test_comb_1)
            temp_rad_map.insert(1, test_comb_2)
            temp_rad_map.insert(2, test_comb_3)

            self.case_task_transformation_map[rad_id] = temp_rad_map

            for a in self.case_task_transformation_map[rad_id]:
                print(a)

            participant = self.participants.get(rad_id, None)
            participant["patients"]["positive"].insert(
                0, self.dummy_patient_name)

    def number_of_patients(self, rad_id: str) -> int:
        """
        Returns the number of patients in the study.
        """

        participant = self.participants.get(rad_id, None)
        if participant is None:
            raise ValueError(f"Rad id {rad_id} not found in data")

        return len(participant["patients"]["positive"]) + \
            len(participant["patients"]["negative"])


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

    percentage_patient = 0

    names_and_paths = self.study_data_master.patient_names_and_paths(
        self.current_radiologist_id)
    size = len(names_and_paths)

    if self.study_data_master.show_training_cases(self.current_radiologist_id):

        training_list = self.study_data_master.get_training_case_names(
            self.current_radiologist_id)
        names_and_paths += [(patient_name, f"{self.study_data_master.path_study_training_cases}{patient_name}")
                            for patient_name in training_list]

        size = len(names_and_paths)

    for patient_name, path_case in names_and_paths:

        path_volume_fixed, path_volume_moving, _, _, \
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
        if path_transform_fixed is None:
            node_transform_fixed = slicer.mrmlScene.AddNewNodeByClass(
                "vtkMRMLLinearTransformNode")
            name_transform_fixed = "Fixed_t"
        else:
            node_transform_fixed = slicer.util.loadTransform(path_transform_fixed,
                                                             {'show': False})[1]
            name_transform_fixed = os.path.basename(
                path_transform_fixed).replace(".h5", "")
        node_transform_fixed.SetName(name_transform_fixed)

        utils.update_progress_window(
            (percentage_patient * 90) / (size), f"Loading data...")
        percentage_patient += 0.05
        if path_transform_moving is None:
            node_transform_moving = slicer.mrmlScene.AddNewNodeByClass(
                "vtkMRMLLinearTransformNode")
            name_transform_moving = "Moving_t"
        else:
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

    size = self.study_data_master.number_of_patients(
        self.current_radiologist_id)

    percentage_patient = start_percentage

    for patient_name, patient_path in self.study_data_master.patient_names_and_paths(self.current_radiologist_id):

        volume_moving_name = self.study_loaded_data[patient_name]["moving"].GetName(
        )

        study_moving_name = volume_moving_name.split('~')[1]

        path_annotations = os.path.join(patient_path,
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

        try:
            with open(os.path.join(path_annotations, "recurrence.txt")) as f:
                self.study_gt_recurrence_description[patient_name] = f.read()
        except FileNotFoundError:
            self.study_gt_recurrence_description[patient_name] = "No recurrence information available"
            print(
                f"Recurrence file not found for patient {patient_name}. Using default description.")

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
            current_position = points_node.GetNthControlPointPosition(
                current_point_idx)
            new_point = utils.create_gt_point(current_point_name,
                                              current_position,
                                              self.views_second_row)

            if patient_name not in self.study_node_groundtruth_points:
                self.study_node_groundtruth_points[patient_name] = {}

            self.study_node_groundtruth_points[patient_name][task_name] = new_point

        slicer.mrmlScene.RemoveNode(points_node)

    # add dummy test points
    test_patient_names = self.study_data_master.get_training_case_names(
        self.current_radiologist_id)

    self.study_node_groundtruth_points[test_patient_names[0]] = {tasks.Task.TEST_RIGID: utils.create_gt_point(tasks.Task.TEST_RIGID.value,
                                                                                                              (0, 0, 0),
                                                                                                              [])}
    self.study_node_groundtruth_points[test_patient_names[1]] = {tasks.Task.TEST_ROTATION: utils.create_gt_point(tasks.Task.TEST_ROTATION.value,
                                                                                                                 (0, 0, 0),
                                                                                                                 [])}
    self.study_node_groundtruth_points[test_patient_names[2]] = {tasks.Task.TEST_NONLINEAR: utils.create_gt_point(tasks.Task.TEST_NONLINEAR.value,
                                                                                                                  (0, 0, 0),
                                                                                                                  [])}

    slicer.progressWindow.close()


def save_annotations(self: "registrationViewerWidget",
                     task_type: tasks.Task,
                     serialise_to_log: Optional[bool] = False,
                     final_save: bool = False) -> None:

    if self.current_combination_idx < 0:
        return

    if self.current_patient_name == self.study_data_master.dummy_patient_name:
        current_patient_name = self.current_patient_name + \
            f"_{self.dummy_patient_step}"
    else:
        current_patient_name = self.current_patient_name

    path_patient = f"{self.study_data_master.path_study_output}{self.current_radiologist_id}/{current_patient_name}/{self.current_patient_transform_type.value}"  # nopep8

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

    utils.set_checkbox_with_signal_block(self, False)
    self.ui_sub_6.study_dropdown.setCurrentText('Size same')


def hide_organiser_ui_elements(self: "registrationViewerWidget") -> None:

    self.ui_sub_2.studyCollapsibleButton.setHidden(True)
    self.ui_sub_3.inputsCollapsibleButton.setHidden(True)
    self.ui_sub_4.controlsCollapsibleButton.setHidden(True)
    self.ui_sub_5.annotationsCollapsibleButton.setHidden(True)
    self.loadingCollapsible.setHidden(True)


def show_organiser_ui_elements(self: "registrationViewerWidget") -> None:

    self.ui_sub_2.studyCollapsibleButton.setHidden(False)
    self.ui_sub_3.inputsCollapsibleButton.setHidden(False)
    self.ui_sub_4.controlsCollapsibleButton.setHidden(False)
    self.ui_sub_5.annotationsCollapsibleButton.setHidden(False)
    self.loadingCollapsible.setHidden(False)
