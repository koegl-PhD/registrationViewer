from collections import defaultdict
from dataclasses import dataclass, field
import json
import os
from typing import Optional, TYPE_CHECKING

from typing import List, Tuple

import qt
import slicer

from registrationViewerLib import tasks, utils, tasks_ui_logic

path = r"/home/koeglf/Documents/code/registrationViewer/registrationViewer/Resources/example_study/data_master.json"


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

        self.patient_to_rads = self._reverse_participants()

    def _reverse_participants(self):
        reversed_mapping = defaultdict(list)

        for rad_id, info in self.participants.items():
            for transform_type in ["ids_patients_transformation_none",
                                   "ids_patients_transformation_linear",
                                   "ids_patients_transformation_nonlinear"]:
                for patient_id in info.get(transform_type, []):
                    reversed_mapping[patient_id].append(rad_id)

        return dict(reversed_mapping)

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

        for transform_type in ["ids_patients_transformation_nonlinear",
                               "ids_patients_transformation_linear",
                               "ids_patients_transformation_none"]:
            for patient in participant[transform_type]:
                result.append(
                    (utils.TransformType(transform_type.split("_")[-1]), patient))

        # sort by transform_type
        # result.sort(key=lambda x: x[0].value)

        return result


def load_study_volumes(self, path_case: str) -> None:

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

    utils.update_progress_window(10, f"Loading data...")
    node_volume_moving = slicer.util.loadVolume(path_volume_moving,
                                                {'show': False})

    utils.update_progress_window(40, f"Loading data...")
    self.node_transform_fixed = slicer.util.loadTransform(path_transform_fixed,
                                                          {'show': False})[1]

    utils.update_progress_window(50, f"Loading data...")
    self.node_transform_moving = slicer.util.loadTransform(path_transform_moving,
                                                           {'show': False})[1]

    utils.update_progress_window(60, f"Loading data...")
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

    for task_name in tasks.TASK_ORDER.values():
        path_annotation = os.path.join(self.study_data_master.path_study_input_annotations,
                                       patient_name,
                                       study_name,
                                       f"{task_name.value}.mrk.json")

        self.study_node_groundtruth_points[task_name] = slicer.util.loadMarkups(
            path_annotation)

        name = path_annotation.split("/")[-1].split(".")[0]
        self.study_node_groundtruth_points[task_name].SetName(name)

    slicer.progressWindow.close()


def save_annotations(self: "registrationViewerWidget",
                     specific_task: Optional[tasks.Task] = None) -> None:

    if self.current_task_idx < 0:
        return

    path_patient = f"{self.study_data_master.path_study_output}{self.current_radiologist_id}/{self.current_patient_name}"  # nopep8
    if not os.path.exists(path_patient):
        os.makedirs(path_patient)

    tasks_to_save = [
        (tasks.Task.A_VERTEBRALIS_R, tasks_ui_logic.save_a_vertebralis_r),
        (tasks.Task.A_VERTEBRALIS_L, tasks_ui_logic.save_a_vertebralis_l),
        (tasks.Task.A_CAROTISEXTERNA_R, tasks_ui_logic.save_a_carotisexterna_r),
        (tasks.Task.A_CAROTISEXTERNA_L, tasks_ui_logic.save_a_carotisexterna_l),
        (tasks.Task.LYMPH_NODE, lambda path, pts: tasks_ui_logic.save_lymphnode(path, pts, self.study_lymphnode_size)),  # nopep8
        (tasks.Task.RECURRENCE, lambda path, pts: tasks_ui_logic.save_recurrence(path, pts, self.study_recurrence_present))  # nopep8
    ]

    for task, save_func in tasks_to_save:
        if specific_task is None or specific_task == task:
            save_func(path_patient, self.study_node_points)


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
    self.ui_sub_6.study_center_on_point_button.setVisible(False)


def show_module_parts_for_user_study(self: "registrationViewerWidget") -> None:
    self.ui_sub_2.studyCollapsibleButton.setHidden(False)
    self.ui_sub_3.inputsCollapsibleButton.setHidden(False)
    self.ui_sub_4.controlsCollapsibleButton.setHidden(False)
    self.ui_sub_5.annotationsCollapsibleButton.setHidden(False)
    self.loadingCollapsible.setHidden(False)

    self.ui_sub_6.Form_user_study.setHidden(True)
