from enum import Enum

from typing import Dict, Union


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
