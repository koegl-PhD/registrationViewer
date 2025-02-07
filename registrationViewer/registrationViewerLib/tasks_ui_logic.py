from typing import Dict, Union

import slicer

from registrationViewerLib import utils, tasks


def show_generic_task_ui(
        ui,
        task: tasks.Task,
        current_case_num: int,
        total_case_count: int
) -> None:
    ui.current_case_label.setVisible(True)

    ui.study_current_task_description_label.setText(
        tasks.TASK_DESCRIPTIONS[task])
    ui.study_current_task_description_label.setVisible(True)

    ui.study_add_point_button.setText("Add point")
    ui.study_add_point_button.setVisible(True)


def show_task_lymphnode(ui,
                        study_node_points: Dict[tasks.Task, Union[None, slicer.vtkMRMLMarkupsFiducialNode]]) -> None:
    ui.study_checkbox.setVisible(False)
    ui.study_dropdown.setVisible(True)

    show_generic_task_ui(ui,
                         tasks.Task.LYMPH_NODE,
                         1,
                         9)

    utils.hide_all_points_except(tasks.Task.LYMPH_NODE,
                                 study_node_points)


def show_task_carotisgabel(ui,
                           study_node_points: Dict[tasks.Task, Union[None, slicer.vtkMRMLMarkupsFiducialNode]]) -> None:
    ui.study_checkbox.setVisible(False)
    ui.study_dropdown.setVisible(False)

    show_generic_task_ui(ui,
                         tasks.Task.CAROTIS_GABEL,
                         1,
                         9)

    utils.hide_all_points_except(tasks.Task.CAROTIS_GABEL,
                                 study_node_points)


def show_task_avertebralis(ui,
                           study_node_points: Dict[tasks.Task, Union[None, slicer.vtkMRMLMarkupsFiducialNode]]) -> None:
    ui.study_checkbox.setVisible(False)
    ui.study_dropdown.setVisible(False)

    show_generic_task_ui(ui,
                         tasks.Task.A_VERTEBRALIS,
                         1,
                         9)

    utils.hide_all_points_except(tasks.Task.A_VERTEBRALIS,
                                 study_node_points)


def show_task_recurrence(ui,
                         study_node_points: Dict[tasks.Task, Union[None, slicer.vtkMRMLMarkupsFiducialNode]]) -> None:
    ui.study_checkbox.setVisible(True)
    ui.study_dropdown.setVisible(False)
    ui.study_checkbox.setText("Recurrence exists")

    show_generic_task_ui(ui,
                         tasks.Task.RECURRENCE,
                         1,
                         9)

    utils.hide_all_points_except(tasks.Task.RECURRENCE,
                                 study_node_points)


def save_lymphnode(path_patient: str,
                   study_node_points: Dict[tasks.Task, Union[None, slicer.vtkMRMLMarkupsFiducialNode]],
                   study_lymphnode_size: str) -> None:

    point = study_node_points[tasks.Task.LYMPH_NODE]

    if point is None:
        slicer.util.errorDisplay(
            F"point {tasks.Task.LYMPH_NODE.value} is missing")
        return

    slicer.util.saveNode(point,
                         path_patient + f"/{point.GetName()}.mrk.json")

    with open(path_patient + f"/lymphnode_size.txt", "w") as f:
        f.write(str(study_lymphnode_size))


def save_carotisgabel(path_patient: str,
                      study_node_points: Dict[tasks.Task, Union[None, slicer.vtkMRMLMarkupsFiducialNode]]) -> None:
    point = study_node_points[tasks.Task.CAROTIS_GABEL]

    if point is None:
        slicer.util.errorDisplay(
            F"point {tasks.Task.CAROTIS_GABEL.value} is missing")
        return

    slicer.util.saveNode(point,
                         path_patient + f"/{point.GetName()}.mrk.json")


def save_avertebralis(path_patient: str,
                      study_node_points: Dict[tasks.Task, Union[None, slicer.vtkMRMLMarkupsFiducialNode]]) -> None:
    point = study_node_points[tasks.Task.A_VERTEBRALIS]

    if point is None:
        slicer.util.errorDisplay(
            F"point {tasks.Task.A_VERTEBRALIS.value} is missing")
        return

    slicer.util.saveNode(point,
                         path_patient + f"/{point.GetName()}.mrk.json")


def save_recurrence(path_patient: str,
                    study_node_points: Dict[tasks.Task, Union[None, slicer.vtkMRMLMarkupsFiducialNode]],
                    recurrence_present) -> None:
    point = study_node_points[tasks.Task.RECURRENCE]

    if recurrence_present:
        if point is None:
            slicer.util.errorDisplay(
                F"point {tasks.Task.RECURRENCE.value} is missing")
            return

        slicer.util.saveNode(point,
                             path_patient + f"/{point.GetName()}.mrk.json")

    with open(path_patient + f"/recurrence_present.txt", "w") as f:
        f.write(str(recurrence_present))
