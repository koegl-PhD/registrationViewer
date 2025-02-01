from enum import Enum


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

    Task.CAROTIS_GABEL: "",

    Task.A_VERTEBRALIS: "",

    Task.RECURRENCE: ""
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
    ui.synchronise_views_general.setVisible(True)

    ui.current_case_label.setVisible(True)
    ui.current_case_label.setText(Case(current_case_num, total_case_count))

    ui.study_current_task_description_label.setText(TASK_DESCRIPTIONS[task])
    ui.study_current_task_description_label.setVisible(True)

    ui.study_add_point_button.setText("Add point")
    ui.study_add_point_button.setVisible(True)
