from enum import Enum

import registrationViewerLib.task_descriptions as task_descriptions


class Task(Enum):
    NONE = 0
    LYMPH_NODE = 1
    CAROTIS_GABEL = 2
    A_VERTEBRALIS = 3
    RECURRENCE = 4


TASK_DESCRIPTIONS = {

    Task.LYMPH_NODE: "Find level X lymph node in the Fixed image (top row).\n\
                    Set a point in its center and select if it changed in size.\n\
                        The ROI of the lymph node is marked in the moving image (bottom row).",

    Task.CAROTIS_GABEL: "",

    Task.A_VERTEBRALIS: "",

    Task.RECURRENCE: ""
}


def show_task_lymph_node(ui) -> None:
    ui.study_current_task_description_label.setText(
        TASK_DESCRIPTIONS[Task.LYMPH_NODE])
    ui.study_current_task_description_label.setVisible(True)

    ui.study_add_point_button.setText("Add lymph node center")
    ui.study_add_point_button.setVisible(True)


def hide_task(ui) -> None:
    ui.study_current_task_description_label.setText("")
    ui.study_current_task_description_label.setVisible(False)

    ui.study_add_point_button.setText("")
    ui.study_add_point_button.setVisible(True)
