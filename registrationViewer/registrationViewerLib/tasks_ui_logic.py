from typing import Dict, Union, Optional, Callable

import slicer

from registrationViewerLib import utils, tasks

TASK_UI_ADDITIONS: Dict[tasks.Task, Callable[[object], None]] = {
    tasks.Task.LYMPH_NODE: lambda ui: ui.study_dropdown.setVisible(True),
    tasks.Task.RECURRENCE: lambda ui: (
        ui.study_checkbox.setText("Recurrence exists"),
        ui.study_checkbox.setVisible(True)
    )
}


def show_task(
    ui,
    task: tasks.Task,
    study_node_points: Dict[tasks.Task,
                            Union[None, slicer.vtkMRMLMarkupsFiducialNode]],
    groundtruth_points: Dict[tasks.Task,
                             Union[None, slicer.vtkMRMLMarkupsFiducialNode]],
    view_group: int
) -> None:

    ui.current_case_label.setVisible(True)
    ui.study_current_task_description_label.setText(tasks.TASK_DESCRIPTIONS[task])  # nopep8
    ui.study_current_task_description_label.setVisible(True)
    ui.study_add_point_button.setText("Add point")
    ui.study_add_point_button.setVisible(True)
    ui.study_checkbox.setVisible(False)
    ui.study_dropdown.setVisible(False)

    # Hide all points except the current one in both dictionaries
    utils.hide_all_points_except(task, study_node_points)
    utils.hide_all_points_except(task, groundtruth_points)

    position_gt_point = groundtruth_points[task].GetNthControlPointPositionWorld(
        0)
    slicer.modules.markups.logic().JumpSlicesToLocation(*position_gt_point,
                                                        False,
                                                        view_group)

    if task in TASK_UI_ADDITIONS:
        TASK_UI_ADDITIONS[task](ui)


def _save_point(
    path_patient: str,
    task: tasks.Task,
    study_node_points: Dict[tasks.Task, Union[None, slicer.vtkMRMLMarkupsFiducialNode]],
    additional_info: Optional[Dict[str, str]] = None
) -> None:

    point = study_node_points[task]

    if point is None and task != tasks.Task.RECURRENCE:
        slicer.util.errorDisplay(F"point {task.value} is missing")
        return
    elif point is None and task == tasks.Task.RECURRENCE:
        pass
    else:
        slicer.util.saveNode(point,
                             path_patient + f"/{point.GetName()}.mrk.json")

    if additional_info:
        path = additional_info.get("path")
        content = additional_info.get("content")

        if path and content:
            with open(path, "w") as f:
                f.write(content)
        else:
            print(f"{additional_info=}")
            raise ValueError(
                f"path and content must be provided together to save additional info in {task.value}")


def save_a_carotisexterna_l(path_patient: str,
                            study_node_points: Dict[tasks.Task, Union[None, slicer.vtkMRMLMarkupsFiducialNode]]) -> None:

    _save_point(path_patient,
                tasks.Task.A_CAROTISEXTERNA_L,
                study_node_points)


def save_a_carotisexterna_r(path_patient: str,
                            study_node_points: Dict[tasks.Task, Union[None, slicer.vtkMRMLMarkupsFiducialNode]]) -> None:

    _save_point(path_patient,
                tasks.Task.A_CAROTISEXTERNA_R,
                study_node_points)


def save_a_vertebralis_l(path_patient: str,
                         study_node_points: Dict[tasks.Task, Union[None, slicer.vtkMRMLMarkupsFiducialNode]]) -> None:
    _save_point(path_patient,
                tasks.Task.A_VERTEBRALIS_L,
                study_node_points)


def save_a_vertebralis_r(path_patient: str,
                         study_node_points: Dict[tasks.Task, Union[None, slicer.vtkMRMLMarkupsFiducialNode]]) -> None:
    _save_point(path_patient,
                tasks.Task.A_VERTEBRALIS_R,
                study_node_points)


def save_lymphnode(path_patient: str,
                   study_node_points: Dict[tasks.Task, Union[None, slicer.vtkMRMLMarkupsFiducialNode]],
                   study_lymphnode_size: str) -> None:

    _save_point(path_patient,
                tasks.Task.LYMPH_NODE,
                study_node_points,
                additional_info={"path": path_patient + "/lymphnode_size.txt",
                                 "content": study_lymphnode_size})


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
