from typing import Dict, Union, Optional

import slicer

from registrationViewerLib import utils, tasks


def show_generic_task_ui(
        ui,
        task: tasks.Task,
        study_node_points: Dict[tasks.Task,
                                Union[None, slicer.vtkMRMLMarkupsFiducialNode]]
) -> None:
    ui.current_case_label.setVisible(True)

    ui.study_current_task_description_label.setText(
        tasks.TASK_DESCRIPTIONS[task])
    ui.study_current_task_description_label.setVisible(True)

    ui.study_add_point_button.setText("Add point")
    ui.study_add_point_button.setVisible(True)

    ui.study_checkbox.setVisible(False)
    ui.study_dropdown.setVisible(False)

    utils.hide_all_points_except(task,
                                 study_node_points)


def show_task_carotisgabel_l(ui,
                             study_node_points: Dict[tasks.Task, Union[None, slicer.vtkMRMLMarkupsFiducialNode]]) -> None:
    show_generic_task_ui(ui,
                         tasks.Task.CAROTIS_GABEL_L,
                         study_node_points)


def show_task_carotisgabel_r(ui,
                             study_node_points: Dict[tasks.Task, Union[None, slicer.vtkMRMLMarkupsFiducialNode]]) -> None:
    show_generic_task_ui(ui, tasks.Task.CAROTIS_GABEL_R, study_node_points)


def show_task_avertebralis_l(ui,
                             study_node_points: Dict[tasks.Task, Union[None, slicer.vtkMRMLMarkupsFiducialNode]]) -> None:

    show_generic_task_ui(ui, tasks.Task.A_VERTEBRALIS_L, study_node_points)


def show_task_avertebralis_r(ui,
                             study_node_points: Dict[tasks.Task, Union[None, slicer.vtkMRMLMarkupsFiducialNode]]) -> None:

    show_generic_task_ui(ui, tasks.Task.A_VERTEBRALIS_R, study_node_points)


def show_task_lymphnode(ui,
                        study_node_points: Dict[tasks.Task, Union[None, slicer.vtkMRMLMarkupsFiducialNode]]) -> None:

    show_generic_task_ui(ui, tasks.Task.LYMPH_NODE, study_node_points)

    ui.study_dropdown.setVisible(True)


def show_task_recurrence(ui,
                         study_node_points: Dict[tasks.Task, Union[None, slicer.vtkMRMLMarkupsFiducialNode]]) -> None:

    show_generic_task_ui(ui, tasks.Task.RECURRENCE, study_node_points)

    ui.study_checkbox.setText("Recurrence exists")
    ui.study_checkbox.setVisible(True)


def _save_point(
    path_patient: str,
    task: tasks.Task,
    study_node_points: Dict[tasks.Task, Union[None, slicer.vtkMRMLMarkupsFiducialNode]],
    additional_info: Optional[Dict[str, str]] = None
) -> None:

    point = study_node_points[task]

    if point is None:
        slicer.util.errorDisplay(F"point {task.value} is missing")
        return

    slicer.util.saveNode(point,
                         path_patient + f"/{point.GetName()}.mrk.json")

    if additional_info:
        path = additional_info.get("path")
        content = additional_info.get("content")

        if path and content:
            with open(path, "w") as f:
                f.write(content)
        else:
            raise ValueError(
                f"path and content must be provided together to save additional info in {task.value}")


def save_lymphnode(path_patient: str,
                   study_node_points: Dict[tasks.Task, Union[None, slicer.vtkMRMLMarkupsFiducialNode]],
                   study_lymphnode_size: str) -> None:

    _save_point(path_patient,
                tasks.Task.LYMPH_NODE,
                study_node_points,
                additional_info={"path": path_patient + "/lymphnode_size.txt",
                                 "content": study_lymphnode_size})


def save_carotisgabel_l(path_patient: str,
                        study_node_points: Dict[tasks.Task, Union[None, slicer.vtkMRMLMarkupsFiducialNode]]) -> None:

    _save_point(path_patient,
                tasks.Task.CAROTIS_GABEL_L,
                study_node_points)


def save_carotisgabel_r(path_patient: str,
                        study_node_points: Dict[tasks.Task, Union[None, slicer.vtkMRMLMarkupsFiducialNode]]) -> None:

    _save_point(path_patient,
                tasks.Task.CAROTIS_GABEL_R,
                study_node_points)


def save_avertebralis_l(path_patient: str,
                        study_node_points: Dict[tasks.Task, Union[None, slicer.vtkMRMLMarkupsFiducialNode]]) -> None:
    _save_point(path_patient,
                tasks.Task.A_VERTEBRALIS_L,
                study_node_points)


def save_avertebralis_r(path_patient: str,
                        study_node_points: Dict[tasks.Task, Union[None, slicer.vtkMRMLMarkupsFiducialNode]]) -> None:
    _save_point(path_patient,
                tasks.Task.A_VERTEBRALIS_R,
                study_node_points)


def save_recurrence(path_patient: str,
                    study_node_points: Dict[tasks.Task, Union[None, slicer.vtkMRMLMarkupsFiducialNode]],
                    recurrence_present: bool) -> None:

    _save_point(path_patient,
                tasks.Task.RECURRENCE,
                study_node_points,
                additional_info={"path": path_patient + "/recurrence_present.txt",
                                 "content": str(recurrence_present)})

    with open(path_patient + f"/recurrence_present.txt", "w") as f:
        f.write(str(recurrence_present))
