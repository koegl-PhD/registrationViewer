from enum import Enum

from typing import Dict, Union


class Task(Enum):
    NONE = "none"
    A_VERTEBRALIS_R = "a_vertebralis_r"
    A_VERTEBRALIS_L = "a_vertebralis_l"
    A_CAROTISEXTERNA_R = "a_carotisexterna_r"
    A_CAROTISEXTERNA_L = "a_carotisexterna_l"
    LYMPH_NODE = "lymph_node"
    RECURRENCE = "recurrence"


TASK_ORDER = {
    0: Task.A_VERTEBRALIS_R,
    1: Task.A_VERTEBRALIS_L,
    2: Task.A_CAROTISEXTERNA_R,
    3: Task.A_CAROTISEXTERNA_L,
    4: Task.LYMPH_NODE,
    5: Task.RECURRENCE
}

TASK_DESCRIPTIONS = {

    Task.A_VERTEBRALIS_L: """
Find the A. vertebralis LEFT in the Fixed image (top row).
Set a point in the center of the A. vertebralis.
The A. vertebralis is marked in the moving image (bottom row).""",

    Task.A_VERTEBRALIS_R: """
Find the A. vertebralis RIGHT in the Fixed image (top row).
Set a point in the center of the A. vertebralis.
The A. vertebralis is marked in the moving image (bottom row).""",

    Task.A_CAROTISEXTERNA_L: """
Find the carotid bifurcation LEFT in the Fixed image (top row).
Set a point in the center of the bifurcation.
The carotid bifurcation is marked in the moving image (bottom row).""",

    Task.A_CAROTISEXTERNA_R: """
Find the carotid bifurcation RIGHT in the Fixed image (top row).
Set a point in the center of the bifurcation.
The carotid bifurcation is marked in the moving image (bottom row).""",

    Task.LYMPH_NODE: """
Find level X lymph node in the Fixed image (top row).\n\
Set a point in its center and select if it changed in size.\n\
The ROI of the lymph node is marked in the moving image (bottom row).""",

    Task.RECURRENCE: """"""
}


class Case():
    def __init__(self, current_case: int, case_count: int):
        self.current_case = current_case
        self.case_count = case_count

    def __str__(self):
        return f"Patient {self.current_case}/{self.case_count}"
