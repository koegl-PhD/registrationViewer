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

    # we don't want to center on recurrence because we only give a text description
    if task != tasks.Task.RECURRENCE:
        utils.center_on_point(groundtruth_points[task], view_group)

    if task in TASK_UI_ADDITIONS:
        TASK_UI_ADDITIONS[task](ui)


def save_point(
    path_patient: str,
    task: tasks.Task,
    study_node_points: Dict[tasks.Task, Union[None, slicer.vtkMRMLMarkupsFiducialNode]],
    additional_info: Optional[Dict[str, str]] = None,
    serialise_to_log: Optional[bool] = False
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

    if additional_info is not None:
        path = additional_info.get("path")
        content = additional_info.get("content")

        if path and content:
            with open(path, "w") as f:
                f.write(content)
        else:
            print(f"{additional_info=}")
            raise ValueError(
                f"path and content must be provided together to save additional info in {task.value}")

    if serialise_to_log:
        serialised_point = utils.serialise_markup(point)

        if additional_info is not None:
            serialised_point.update(additional_info)

        print(f"WARNING Serialised point: {serialised_point} not logged yet")
