from enum import Enum

from typing import Dict, Union

import slicer

from registrationViewerLib import utils


class Task(Enum):
    NONE = "none"
    LYMPH_NODE = "lymph_node"
    CAROTIS_GABEL = "carotis_gabel"
    A_VERTEBRALIS = "a_vertebralis"
    RECURRENCE = "recurrence"


TASK_DESCRIPTIONS = {

    Task.LYMPH_NODE: """
Find level X lymph node in the Fixed image (top row).\n\
Set a point in its center and select if it changed in size.\n\
The ROI of the lymph node is marked in the moving image (bottom row).""",

    Task.CAROTIS_GABEL: """
Find the carotid bifurcation in the Fixed image (top row).
Set a point in the center of the bifurcation.
The carotid bifurcation is marked in the moving image (bottom row).""",

    Task.A_VERTEBRALIS: """
Find the A. vertebralis in the Fixed image (top row).
Set a point in the center of the A. vertebralis.
The A. vertebralis is marked in the moving image (bottom row).""",

    Task.RECURRENCE: """
Decide if a recurrence is present in the Fixed image (top row).
If yes, set a point in the center of the recurrence.
TUMOR TEXT"""
}


class Case():
    def __init__(self, current_case: int, case_count: int):
        self.current_case = current_case
        self.case_count = case_count

    def __str__(self):
        return f"Patient {self.current_case}/{self.case_count}"


def show_generic_task_ui(
        ui,
        task: Task,
        current_case_num: int,
        total_case_count: int
) -> None:
    ui.current_case_label.setVisible(True)

    ui.study_current_task_description_label.setText(TASK_DESCRIPTIONS[task])
    ui.study_current_task_description_label.setVisible(True)

    ui.study_add_point_button.setText("Add point")
    ui.study_add_point_button.setVisible(True)


def show_task_lymphnode(ui,
                        study_node_points: Dict[Task, Union[None, slicer.vtkMRMLMarkupsFiducialNode]]) -> None:
    ui.study_checkbox.setVisible(False)
    ui.study_dropdown.setVisible(True)

    show_generic_task_ui(ui,
                         Task.LYMPH_NODE,
                         1,
                         9)

    utils.hide_all_points_except(Task.LYMPH_NODE,
                                 study_node_points)


def show_task_carotisgabel(ui,
                           study_node_points: Dict[Task, Union[None, slicer.vtkMRMLMarkupsFiducialNode]]) -> None:
    ui.study_checkbox.setVisible(False)
    ui.study_dropdown.setVisible(False)

    show_generic_task_ui(ui,
                         Task.CAROTIS_GABEL,
                         1,
                         9)

    utils.hide_all_points_except(Task.CAROTIS_GABEL,
                                 study_node_points)


def show_task_avertebralis(ui,
                           study_node_points: Dict[Task, Union[None, slicer.vtkMRMLMarkupsFiducialNode]]) -> None:
    ui.study_checkbox.setVisible(False)
    ui.study_dropdown.setVisible(False)

    show_generic_task_ui(ui,
                         Task.A_VERTEBRALIS,
                         1,
                         9)

    utils.hide_all_points_except(Task.A_VERTEBRALIS,
                                 study_node_points)


def show_task_recurrence(ui,
                         study_node_points: Dict[Task, Union[None, slicer.vtkMRMLMarkupsFiducialNode]]) -> None:
    ui.study_checkbox.setVisible(True)
    ui.study_dropdown.setVisible(False)
    ui.study_checkbox.setText("Recurrence exists")

    show_generic_task_ui(ui,
                         Task.RECURRENCE,
                         1,
                         9)

    utils.hide_all_points_except(Task.RECURRENCE,
                                 study_node_points)


def save_lymphnode(path_patient: str,
                   study_node_points: Dict[Task, Union[None, slicer.vtkMRMLMarkupsFiducialNode]],
                   study_lymphnode_size: str) -> None:

    point = study_node_points[Task.LYMPH_NODE]

    if point is None:
        slicer.util.errorDisplay(
            F"point {Task.LYMPH_NODE.value} is missing")
        return

    slicer.util.saveNode(point,
                         path_patient + f"/{point.GetName()}.mrk.json")

    with open(path_patient + f"/lymphnode_size.txt", "w") as f:
        f.write(str(study_lymphnode_size))


def save_carotisgabel(path_patient: str,
                      study_node_points: Dict[Task, Union[None, slicer.vtkMRMLMarkupsFiducialNode]]) -> None:
    point = study_node_points[Task.CAROTIS_GABEL]

    if point is None:
        slicer.util.errorDisplay(
            F"point {Task.CAROTIS_GABEL.value} is missing")
        return

    slicer.util.saveNode(point,
                         path_patient + f"/{point.GetName()}.mrk.json")


def save_avertebralis(path_patient: str,
                      study_node_points: Dict[Task, Union[None, slicer.vtkMRMLMarkupsFiducialNode]]) -> None:
    point = study_node_points[Task.A_VERTEBRALIS]

    if point is None:
        slicer.util.errorDisplay(
            F"point {Task.A_VERTEBRALIS.value} is missing")
        return

    slicer.util.saveNode(point,
                         path_patient + f"/{point.GetName()}.mrk.json")


def save_recurrence(path_patient: str,
                    study_node_points: Dict[Task, Union[None, slicer.vtkMRMLMarkupsFiducialNode]],
                    recurrence_present) -> None:
    point = study_node_points[Task.RECURRENCE]

    if recurrence_present:
        if point is None:
            slicer.util.errorDisplay(
                F"point {Task.RECURRENCE.value} is missing")
            return

        slicer.util.saveNode(point,
                             path_patient + f"/{point.GetName()}.mrk.json")

    with open(path_patient + f"/recurrence_present.txt", "w") as f:
        f.write(str(recurrence_present))
