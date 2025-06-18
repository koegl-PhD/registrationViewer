import logging
from pathlib import Path

from typing import Dict, Union, Optional, Callable, TYPE_CHECKING

import slicer

from registrationViewerLib import utils, tasks, view_logic, texts
from registrationViewerLib.custom_logging import log, LogType


if TYPE_CHECKING:
    from ..registrationViewer import registrationViewerWidget


TASK_UI_ADDITIONS: Dict[tasks.Task, Callable[[object], None]] = {
    tasks.Task.LYMPH_NODE: lambda ui: ui.study_dropdown.setVisible(True),
    tasks.Task.RECURRENCE.value: lambda ui: (
        ui.study_checkbox.setText(
            texts.Buttons.DROPDOWN_RECURRENCE_PRESENT),
        ui.study_checkbox.setVisible(True)
    )
}


def show_task(
    self: "registrationViewerWidget",
    randomise_starting_offset: bool = False,
) -> None:

    if self.crosshair is not None:
        if self.current_patient_transform_type == utils.TransformType.NONE:
            self.crosshair.set_crosshair_visibility_in_views(
                self.views_all, False)
        else:
            self.crosshair.set_crosshair_visibility_in_views(
                self.views_all, True)

    if self.current_task == tasks.Task.LYMPH_NODE:
        description = tasks.TASK_DESCRIPTIONS[self.current_task].format(
            lymphnode_description=self.study_gt_lymphnode_description[self.current_patient_name])
        self.ui_sub_6.study_center_on_gt_point_button.setText(
            texts.Buttons.CENTER_ON_GROUND_TRUTH_LYMPHNODE)
    elif self.current_task == tasks.Task.RECURRENCE:
        description = tasks.TASK_DESCRIPTIONS[self.current_task].format(
            recurrence_description=self.study_gt_recurrence_description[self.current_patient_name])
        self.ui_sub_6.study_center_on_gt_point_button.setText("")
    else:
        description = tasks.TASK_DESCRIPTIONS[self.current_task]
        self.ui_sub_6.study_center_on_gt_point_button.setText(
            texts.Buttons.CENTER_ON_GROUND_TRUTH_POINT)

    self.ui_sub_6.study_current_task_description_label.setText(description)  # nopep8

    self.ui_sub_6.study_current_task_description_label.setVisible(True)
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
        self.ui_sub_6.study_center_on_gt_point_button.setVisible(False)
        utils.set_checkbox_with_signal_block(self, False)
        self.ui_sub_6.study_next_task_button.setEnabled(True)
        self.ui_sub_6.study_next_task_button.toolTip = ""  # nopep8

    # we don't want to center on training tasks because those are not real tasks
    elif self.is_current_task_simple_training_example:
        self.ui_sub_6.study_center_on_gt_point_button.setVisible(False)
    else:
        utils.center_on_point(
            self.study_node_groundtruth_points[self.current_patient_name][self.current_task], self.group_second_row)

    if self.current_task == tasks.Task.LYMPH_NODE:
        self.ui_sub_6.study_dropdown.setVisible(False)

    if self.current_task.value in TASK_UI_ADDITIONS:

        TASK_UI_ADDITIONS[self.current_task.value](self.ui_sub_6)

    def _on_popup_ok() -> None:
        log(logging.INFO, LogType.U_BUTTON, self.start_task_log_text_user)
        self.full_screen_block.close()

    utils.show_fullscreen_popup_with_callback(title=f"Aufgabe {self.current_combination_idx+1}/{self.number_of_study_tasks}",
                                              content=description.replace(
        "\n", "\n\n"),
        center_text=True,
        on_ok=_on_popup_ok)


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
