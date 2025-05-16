import logging
from pathlib import Path
import random

from typing import Dict, Union, Optional, Callable, TYPE_CHECKING

import slicer

from registrationViewerLib import utils, tasks, view_logic
from registrationViewerLib.custom_logging import log, LogType


if TYPE_CHECKING:
    from ..registrationViewer import registrationViewerWidget


TASK_UI_ADDITIONS: Dict[tasks.Task, Callable[[object], None]] = {
    tasks.Task.LYMPH_NODE: lambda ui: ui.study_dropdown.setVisible(True),
    tasks.Task.RECURRENCE.value: lambda ui: (
        ui.study_checkbox.setText("Recurrence exists"),
        ui.study_checkbox.setVisible(True)
    )
}


def show_task(
    self: "registrationViewerWidget",
    randomise_starting_offset: bool = False,
) -> None:

    if self.current_task == tasks.Task.LYMPH_NODE:
        description = tasks.TASK_DESCRIPTIONS[self.current_task].format(
            lymphnode_description=self.study_gt_lymphnode_description[self.current_patient_name])
    elif self.current_task == tasks.Task.RECURRENCE:
        description = tasks.TASK_DESCRIPTIONS[self.current_task].format(
            recurrence_description=self.study_gt_recurrence_description[self.current_patient_name])
    else:
        description = tasks.TASK_DESCRIPTIONS[self.current_task]

    self.ui_sub_6.study_current_task_description_label.setText(description)  # nopep8

    self.ui_sub_6.study_current_task_description_label.setVisible(True)
    self.ui_sub_6.study_add_point_button.setText("Add point")
    self.ui_sub_6.study_add_point_button.setVisible(True)
    self.ui_sub_6.study_center_on_user_point_button.setVisible(True)
    self.ui_sub_6.study_center_on_gt_point_button.setVisible(True)
    self.ui_sub_6.study_checkbox.setVisible(False)
    self.ui_sub_6.study_dropdown.setVisible(False)

    # Hide all points except the current one
    utils.hide_all_points_except_current_point(self)

    if randomise_starting_offset:
        view_logic.randomise_offsets(
            self.views_first_row + self.views_second_row)

    # we don't want to center on recurrence because we only give a text description
    if self.current_task == tasks.Task.RECURRENCE:
        self.ui_sub_6.study_center_on_user_point_button.setEnabled(False)
        self.ui_sub_6.study_checkbox.blockSignals(True)
        self.ui_sub_6.study_checkbox.setChecked(False)
        self.ui_sub_6.study_checkbox.blockSignals(False)

    else:
        utils.center_on_point(
            self.study_node_groundtruth_points[self.current_patient_name][self.current_task], self.group_second_row)

    if self.current_task == tasks.Task.LYMPH_NODE:
        self.ui_sub_6.study_dropdown.setVisible(True)

    if self.current_task.value in TASK_UI_ADDITIONS:

        TASK_UI_ADDITIONS[self.current_task.value](self.ui_sub_6)


def save_point(
    path_patient: str,
    task: tasks.Task,
    study_node_annotation: Dict[tasks.Task, Union[None, slicer.vtkMRMLMarkupsFiducialNode]],
    additional_info: Optional[Dict[str, str]] = None,
    serialise_to_log: Optional[bool] = False,
    final_save: bool = False
) -> None:

    # create all dirctories in path_patient
    Path(path_patient).mkdir(parents=True, exist_ok=True)

    if study_node_annotation is None and task != tasks.Task.RECURRENCE:
        slicer.util.errorDisplay(F"point {task.value} is missing")
        return
    elif study_node_annotation is None and task == tasks.Task.RECURRENCE:
        pass
    else:
        slicer.util.saveNode(study_node_annotation,
                             path_patient + f"/{study_node_annotation.GetName()}.mrk.json")

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
        if not study_node_annotation and task == tasks.Task.RECURRENCE:
            log(logging.INFO, LogType.SAVE, "No recurrence to save")
            return

        serialised_point = utils.serialise_markup(study_node_annotation)

        if additional_info is not None:
            serialised_point.update(
                {"content": additional_info.get("content")})

        if final_save:
            text = f"Point {task.value} saved ~ {str(serialised_point)}"
        else:
            text = f"Point saved ~ {str(serialised_point)}"

        log(logging.INFO, LogType.SAVE, text)
