from dataclasses import dataclass, field
import json
import logging
import os
import random

from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

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
                                       List[Tuple[Tuple[str, str], str, str]]] = field(init=False)

    chunked_patients: Dict[int, List[List[Tuple[str, utils.TransformType, str]]]] = field(
        default_factory=dict)

    split: dict[int, dict[int, Tuple[str, utils.TransformType]]
                ] = field(default_factory=dict)

    number_of_training_patients: int = field(init=False)
    number_of_simple_training_patients: int = field(init=False)
    number_of_full_training_patients: int = field(init=False)

    number_of_training_tasks: int = field(init=False)
    number_of_simple_training_tasks: int = field(init=False)
    number_of_full_training_tasks: int = field(init=False)

    def __post_init__(self):
        with open(self.path, "r") as f:
            self.data = json.load(f)

        self.__dict__.update(self.data)

        random.seed(1)

        self._create_data_split()

        self._divide_patients_into_chunks()

        self._create_case_task_transformation_map()

    def save(self, json_path=None):
        if json_path is None:
            json_path = self.path

        with open(json_path, "w") as f:
            json.dump(self.data, f, indent=4)

    def _create_data_split(self) -> None:

        patients_positive = self.data["patients"]["positive"]
        patients_negative = self.data["patients"]["negative"]

        split_g1 = {patients_positive[i]: ("positive", utils.TransformType.NONE)
                    for i in range(0, 6)}
        split_g1.update({patients_negative[i]: ("negative", utils.TransformType.NONE)
                        for i in range(0, 6)})
        split_g1.update({patients_positive[i]: ("positive", utils.TransformType.LINEAR)
                        for i in range(6, 12)})
        split_g1.update({patients_negative[i]: ("negative", utils.TransformType.LINEAR)
                        for i in range(6, 12)})
        split_g1.update({patients_positive[i]: ("positive", utils.TransformType.NONLINEAR)
                        for i in range(12, 18)})
        split_g1.update({patients_negative[i]: ("negative", utils.TransformType.NONLINEAR)
                        for i in range(12, 18)})

        split_g2 = {patients_positive[i]: ("positive", utils.TransformType.LINEAR)
                    for i in range(0, 6)}
        split_g2.update({patients_negative[i]: ("negative", utils.TransformType.LINEAR)
                        for i in range(0, 6)})
        split_g2.update({patients_positive[i]: ("positive", utils.TransformType.NONLINEAR)
                        for i in range(6, 12)})
        split_g2.update({patients_negative[i]: ("negative", utils.TransformType.NONLINEAR)
                        for i in range(6, 12)})
        split_g2.update({patients_positive[i]: ("positive", utils.TransformType.NONE)
                        for i in range(12, 18)})
        split_g2.update({patients_negative[i]: ("negative", utils.TransformType.NONE)
                        for i in range(12, 18)})

        split_g3 = {patients_positive[i]: ("positive", utils.TransformType.NONLINEAR)
                    for i in range(0, 6)}
        split_g3.update({patients_negative[i]: ("negative", utils.TransformType.NONLINEAR)
                        for i in range(0, 6)})
        split_g3.update({patients_positive[i]: ("positive", utils.TransformType.NONE)
                        for i in range(6, 12)})
        split_g3.update({patients_negative[i]: ("negative", utils.TransformType.NONE)
                        for i in range(6, 12)})
        split_g3.update({patients_positive[i]: ("positive", utils.TransformType.LINEAR)
                        for i in range(12, 18)})
        split_g3.update({patients_negative[i]: ("negative", utils.TransformType.LINEAR)
                        for i in range(12, 18)})

        self.split = {
            1: split_g1,
            2: split_g2,
            3: split_g3
        }

        self._shuffle_data_split()

        """
        print('\t' * 2 + 'Group 1' + '\t' * 5 +
              'Group 2' + '\t' * 5 + 'Group 3')
        for (i1, p1), (i2, p2), (i3, p3) in zip(self.split[1].items(), self.split[2].items(), self.split[3].items()):

            if p1[1] != utils.TransformType.NONLINEAR:
                t1 = 1
            else:
                t1 = 1

            if p2[1] != utils.TransformType.NONLINEAR:
                t2 = 1
            else:
                t2 = 1
            if p3[1] != utils.TransformType.NONLINEAR:
                t3 = 1
            else:
                t3 = 1

            print(
                str(i1) + '\t\t' + p1[0] + '\t' * t1 + p1[1].value + '\t\t' +
                str(i2) + '\t\t' + p2[0] + '\t' * t2 + p2[1].value + '\t\t' +
                str(i3) + '\t\t' + p3[0] + '\t' * t3 + p3[1].value
            )
        print()
        print()
        print()
        print()
        """

    def _shuffle_data_split(self) -> None:

        shuffled_keys = list(self.split[1].keys())

        random.shuffle(shuffled_keys)

        self.split[1] = {k: self.split[1][k] for k in shuffled_keys}
        self.split[2] = {k: self.split[2][k] for k in shuffled_keys}
        self.split[3] = {k: self.split[3][k] for k in shuffled_keys}

    def get_chunked_patient_names_and_paths(
            self,
            patient_name: str,
            chunk_idx: int
    ) -> List[Tuple[str, str]]:

        names_and_paths = []

        for patient_name, transform, present in self.chunked_patients[1][chunk_idx]:
            p = self.data[f"path_study_input_cases_{present}"]
            names_and_paths.append(
                (patient_name, f"{p}{patient_name}"))

        return names_and_paths

    def number_of_tasks(self) -> int:

        calibration_id = list(self.data["participants"].keys())[0]

        return len(self.case_task_transformation_map[calibration_id])

    def current_patient_idx(self, patient_name: str) -> int:
        """
        Returns the index of the current patient across the chunked patient lists.
        """

        idx = 0

        for chunk in self.chunked_patients[1]:
            for patient, _, _ in chunk:
                if patient == patient_name:
                    return idx
                idx += 1

        raise ValueError(
            f"Patient {patient_name} not found in chunks. Only found {self.chunked_patients[1]=}.")

    @property
    def training_case_names(self) -> List[str]:
        """
        Returns the names of the cases used for training
        """

        # list all folders
        path = self.path_study_input_cases_training

        if not os.path.exists(path):
            raise FileNotFoundError(
                f"Path {path} does not exist. Please check the study configuration.")

        training_cases = sorted([f for f in os.listdir(
            path) if os.path.isdir(os.path.join(path, f))])

        return training_cases

    @property
    def simple_training_case_names(self) -> List[str]:

        return self.training_case_names[:3]

    @property
    def full_training_case_names(self) -> List[str]:

        return self.training_case_names[3:]

    @property
    def calibration_case_names(self) -> list[str]:
        """
        Returns the names of the cases used for calibration
        """

        # list all folders
        path = self.path_study_input_cases_calibration

        if not os.path.exists(path):
            raise FileNotFoundError(
                f"Path {path} does not exist. Please check the study configuration.")

        calibration_cases = sorted([f for f in os.listdir(
            path) if os.path.isdir(os.path.join(path, f))])

        return calibration_cases

    def _divide_patients_into_chunks(self) -> None:

        max_chunk_size = 2

        patients: List[str] = []

        for group, split in self.split.items():

            for patient_name, (present, transform) in split.items():

                patients.append((patient_name, transform, present))

            self.chunked_patients[group] = [patients[i:i+max_chunk_size]
                                            for i in range(0, len(patients), max_chunk_size)]

    def _create_case_task_transformation_map(self) -> None:
        """
        Create a mapping of task to transformation for the random case.
        This is used to create the random case in the study.
        """

        self.case_task_transformation_map = {}

        pat_idx = 0

        for rad_id, rad_content in self.participants.items():

            group = int(rad_content["group"])

            temp_rad_map = []

            for chunk in self.chunked_patients[group]:

                temp_chunk_map = []

                for patient_name, transform, present in chunk:

                    for task in tasks.TASK_ORDER.values():

                        # if task not in [tasks.Task.RECURRENCE]:
                        # continue

                        temp_chunk_map.append(
                            (patient_name, task.value, transform.value))

                    pat_idx += 1

                temp_rad_map += temp_chunk_map

            temp_rad_map = self._insert_calibration_cases(temp_rad_map, group)

            temp_rad_map = self._insert_training_cases(temp_rad_map, group)

            self.case_task_transformation_map[rad_id] = temp_rad_map

            for a in self.case_task_transformation_map[rad_id]:
                print(a)

    def _insert_calibration_cases(
            self,
            temp_rad_map: List[List[Tuple[str, str, str]]],
            group: int
    ) -> List[List[Tuple[str, str, str]]]:

        calibration_tasks_start = []
        calibration_tasks_end = []
        calibration_patients = []
        for name, transform in zip(self.calibration_case_names[:-1], [utils.TransformType.NONLINEAR, utils.TransformType.NONE, utils.TransformType.LINEAR]):
            for task in tasks.TASK_ORDER.values():

                # if task != tasks.Task.RECURRENCE:
                #     continue

                calibration_tasks_start.append(
                    (name, task.value, transform.value))

            calibration_patients.append((name, transform, "calibration"))

        self.chunked_patients[group][0] = calibration_patients + \
            self.chunked_patients[group][0]

        for task in tasks.TASK_ORDER.values():
            # if task != tasks.Task.RECURRENCE:
            #     continue
            calibration_tasks_end.append(
                (self.calibration_case_names[-1], task.value, utils.TransformType.NONLINEAR.value))

        self.chunked_patients[group][-1].append(
            (self.calibration_case_names[-1], utils.TransformType.NONLINEAR, "calibration"))

        temp_rad_map = calibration_tasks_start + temp_rad_map + calibration_tasks_end

        return temp_rad_map

    def _insert_training_cases(
            self,
            temp_rad_map: List[List[Tuple[str, str, str]]],
            group: int
    ) -> List[List[Tuple[str, str, str]]]:

        training_names = self.training_case_names

        training_chunk = [(training_names[0], utils.TransformType.NONE, "training"),       # nopep8
                          (training_names[1], utils.TransformType.LINEAR, "training"),     # nopep8
                          (training_names[2], utils.TransformType.NONLINEAR, "training"),  # nopep8
                          (training_names[3], utils.TransformType.NONE, "training"),       # nopep8
                          (training_names[4], utils.TransformType.LINEAR, "training"),     # nopep8
                          (training_names[5], utils.TransformType.NONLINEAR, "training")]  # nopep8
        self.chunked_patients[group].insert(0, training_chunk)

        training_comb_1 = [(training_names[0], tasks.Task.TRAINING_NONE.value,
                           utils.TransformType.LINEAR.value)]
        training_comb_2 = [(training_names[1], tasks.Task.TRAINING_ROTATION.value,
                           utils.TransformType.LINEAR.value)]
        training_comb_3 = [(training_names[2], tasks.Task.TRAINING_NONLINEAR.value,
                           utils.TransformType.NONLINEAR.value)]
        training_comb_4, training_comb_5, training_comb_6 = [], [], []

        for task in tasks.TASK_ORDER.values():
            # if task != tasks.Task.RECURRENCE:
            #     continue
            training_comb_4.append(
                (training_names[3], task.value, utils.TransformType.NONE.value))
            training_comb_5.append(
                (training_names[4], task.value, utils.TransformType.LINEAR.value))
            training_comb_6.append(
                (training_names[5], task.value, utils.TransformType.NONLINEAR.value))

        all_combinations = training_comb_1 + training_comb_2 + training_comb_3 + \
            training_comb_4 + training_comb_5 + training_comb_6

        temp_rad_map = all_combinations + temp_rad_map

        self.number_of_training_patients = len(training_chunk)
        self.number_of_simple_training_patients = 3
        self.number_of_full_training_patients = 3

        self.number_of_training_tasks = len(all_combinations)
        self.number_of_simple_training_tasks = len(
            training_comb_1) + len(training_comb_2) + len(training_comb_3)
        self.number_of_full_training_tasks = len(
            training_comb_4) + len(training_comb_5) + len(training_comb_6)

        return temp_rad_map

    def number_of_patients(self, with_calibration: bool = False) -> int:
        """
        Returns the number of patients in the study.
        """

        if with_calibration:
            increase = len(self.calibration_case_names)
        else:
            increase = 0

        return len(self.data["patients"]["positive"]) + \
            len(self.data["patients"]["negative"]) + increase

    def in_chunk(self, patient_name: str, chunk_idx: int) -> bool:
        for patient, _, _ in self.chunked_patients[1][chunk_idx]:
            if patient_name == patient:
                return True

        return False

    def get_chunk_idx(self, patient_name: str) -> int:
        """
        Returns the index of the chunk that contains the given combination.
        """

        for idx, chunk in enumerate(self.chunked_patients[1]):
            for patient, _, _ in chunk:
                if patient_name == patient:
                    return idx

        raise ValueError(
            f"Patient {patient_name} not found in chunks. Only found {self.chunked_patients[1]=}.")

    def remove_training_combinations(self, rad_id: str) -> None:
        temp = self.case_task_transformation_map[rad_id]
        self.case_task_transformation_map[rad_id] = temp[3:]

        temp = self.chunked_patients[1]
        self.chunked_patients[1] = temp[1:]
        self.chunked_patients[2] = temp[1:]
        self.chunked_patients[3] = temp[1:]

    def group(self, rad_id: str) -> int:

        return self.data["participants"][rad_id]["group"]


def load_current_chunk(self: "registrationViewerWidget") -> None:

    log(logging.INFO, LogType.INTERNAL,
        f"Start loading study data chunk {self.chunk_idx+1}/{len(self.study_data.chunked_patients[1])}")

    # fullscreen_block = utils.show_fullscreen_block("", "")

    utils.set_up_progress_window("Loading data...")

    names_and_paths = self.study_data.get_chunked_patient_names_and_paths(self.current_patient_name,
                                                                          self.chunk_idx)

    for name, _ in names_and_paths:
        log(logging.INFO, LogType.INTERNAL, f"\t{name}")

    no_of_patients = len(names_and_paths)

    progress_val = 0

    for case_name, case_path in names_and_paths:
        progress_val = load_one_case_voxels(
            self,
            case_name,
            case_path,
            no_of_patients,
            progress_val)

        progress_val = load_one_case_annotations(
            self,
            case_name,
            case_path,
            no_of_patients,
            progress_val)

    slicer.progressWindow.close()

    # fullscreen_block.close()

    log(logging.INFO, LogType.INTERNAL,
        f"Finished loading study data chunk {self.chunk_idx+1}/{len(self.study_data.chunked_patients[1])}")


def clear_one_chunk(self: "registrationViewerWidget") -> None:

    log(logging.INFO, LogType.INTERNAL,
        "Start clearing current study data chunk")

    for node_type_and_node in self.study_loaded_data.values():
        for node in node_type_and_node.values():
            slicer.mrmlScene.RemoveNode(node)

    self.study_loaded_data = {}

    for node_type_and_node in self.study_node_groundtruth_points.values():
        for node in node_type_and_node.values():
            slicer.mrmlScene.RemoveNode(node)

    self.study_node_groundtruth_points = {}

    log(logging.INFO, LogType.INTERNAL,
        "Done clearing current study data chunk")


def add_calibration_training_points(self: "registrationViewerWidget") -> None:
    training_patient_names = self.study_data.training_case_names

    self.study_node_groundtruth_points[training_patient_names[0]] = {tasks.Task.TRAINING_NONE: utils.create_gt_point(tasks.Task.TRAINING_NONE.value,
                                                                                                                     (0, 0, 0),
                                                                                                                     [])}
    self.study_node_groundtruth_points[training_patient_names[1]] = {tasks.Task.TRAINING_ROTATION: utils.create_gt_point(tasks.Task.TRAINING_ROTATION.value,
                                                                                                                         (0, 0, 0),
                                                                                                                         [])}
    self.study_node_groundtruth_points[training_patient_names[2]] = {tasks.Task.TRAINING_NONLINEAR: utils.create_gt_point(tasks.Task.TRAINING_NONLINEAR.value,
                                                                                                                          (0, 0, 0),
                                                                                                                          [])}


def load_one_case_voxels(
        self: "registrationViewerWidget",
        case_name: str,
        case_path: str,
        no_of_patients: int,
        progress_val: float,
) -> float:

    path_volume_fixed, path_volume_moving, _, _, \
        path_transform_fixed, path_transform_moving, \
        path_deformation = utils.get_paths_to_load(case_path,
                                                   self.study_data.path_study_input_registrations)

    utils.update_progress_window(
        (progress_val * 90) / (no_of_patients), f"Loading data...")
    progress_val += 0.2
    node_volume_fixed = slicer.util.loadVolume(path_volume_fixed,
                                               {'show': False})
    name_volume_fixed = os.path.basename(
        path_volume_fixed).replace(".nii.gz", "")
    node_volume_fixed.SetName(name_volume_fixed)

    utils.update_progress_window(
        (progress_val * 90) / (no_of_patients), f"Loading data...")
    progress_val += 0.2
    node_volume_moving = slicer.util.loadVolume(path_volume_moving,
                                                {'show': False})
    name_volume_moving = os.path.basename(
        path_volume_moving).replace(".nii.gz", "")
    node_volume_moving.SetName(name_volume_moving)

    utils.update_progress_window(
        (progress_val * 90) / (no_of_patients), f"Loading data...")
    progress_val += 0.05
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
        (progress_val * 90) / (no_of_patients), f"Loading data...")
    progress_val += 0.05
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
        (progress_val * 90) / (no_of_patients), f"Loading data...")
    progress_val += 0.5
    if path_deformation is None:
        node_deformation = slicer.mrmlScene.AddNewNodeByClass(
            "vtkMRMLLinearTransformNode")
    else:
        # node_deformation = slicer.mrmlScene.AddNewNodeByClass(
        # "vtkMRMLLinearTransformNode")
        node_deformation = slicer.util.loadTransform(path_deformation,
                                                     {'show': False})[1]

    if case_name not in self.study_loaded_data:
        self.study_loaded_data[case_name] = {}

    self.study_loaded_data[case_name]["fixed"] = node_volume_fixed
    self.study_loaded_data[case_name]["moving"] = node_volume_moving
    self.study_loaded_data[case_name]["transform_fixed"] = node_transform_fixed
    self.study_loaded_data[case_name]["transform_moving"] = node_transform_moving
    self.study_loaded_data[case_name]["deformation"] = node_deformation

    utils.hide_all_volumes_from_views(
        self.views_first_row + self.views_second_row)

    return progress_val


def load_one_case_annotations(
        self: "registrationViewerWidget",
        case_name: str,
        case_path: str,
        no_of_patients: int,
        progress_val: float,
) -> float:

    l = case_name.lower()

    if "training_1" in l or "training_2" in l or "training_3" in l:
        return progress_val

    volume_moving_name = self.study_loaded_data[case_name]["moving"].GetName(
    )

    study_moving_name = volume_moving_name.split('~')[1]

    path_annotations = os.path.join(case_path,
                                    "preprocessed",
                                    study_moving_name,
                                    "annotations")

    path_points = os.path.join(path_annotations,
                               f"points_{volume_moving_name}.mrk.json")
    utils.update_progress_window(
        (progress_val * 90) / (no_of_patients))
    progress_val += 0.05
    points_node = slicer.util.loadMarkups(path_points)

    points_node.SetName(os.path.basename(
        path_points).replace(".mrk.json", ""))
    points_node_name = points_node.GetName()

    path_lymphnode = os.path.join(path_annotations,
                                  f"roi_lymphnode_{volume_moving_name}.mrk.json")
    utils.update_progress_window(
        (progress_val * 90) / (no_of_patients))
    progress_val += 0.05
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
        self.study_gt_lymphnode_description[case_name] = f.read().split(
            "Description:")[-1].strip()

    try:
        with open(os.path.join(path_annotations, "recurrence.txt")) as f:
            self.study_gt_recurrence_description[case_name] = f.read()
    except FileNotFoundError:
        self.study_gt_recurrence_description[case_name] = "No recurrence information available"
        print(
            f"Recurrence file not found for patient {case_name}. Using default description.")

    for task_name in tasks.TASK_ORDER.values():
        if task_name == tasks.Task.LYMPH_NODE:
            # it is not a point, but a ROI so we skip
            self.study_node_groundtruth_points[case_name][task_name] = lymphnode
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

        if case_name not in self.study_node_groundtruth_points:
            self.study_node_groundtruth_points[case_name] = {}

        self.study_node_groundtruth_points[case_name][task_name] = new_point

    slicer.mrmlScene.RemoveNode(points_node)

    return progress_val


def save_annotations(self: "registrationViewerWidget",
                     task_type: tasks.Task,
                     serialise_to_log: Optional[bool] = False,
                     final_save: bool = False) -> None:

    if self.current_combination_idx < 0:
        return

    current_patient_name = self.current_patient_name

    path_patient = f"{self.study_data.path_study_output}{self.current_radiologist_id}/{current_patient_name}/{self.current_patient_transform_type.value}"  # nopep8

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
