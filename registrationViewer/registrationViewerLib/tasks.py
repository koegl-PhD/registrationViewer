from enum import Enum


class Task(Enum):
    NONE = "no_task"
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
Finde den Abgang der A. vertebralis links im Fixed Bild (obere Reihe).
Setze einen Punkt in die Mitte des Abgangs.
Der Abgang ist im Moving Bild markiert (untere Reihe).
""",

    Task.A_VERTEBRALIS_R: """
Finde den Abgang der A. vertebralis rechts im Fixed Bild (obere Reihe).
Setze einen Punkt in die Mitte des Abgangs.
Der Abgang ist im Moving Bild markiert (untere Reihe).
""",

    Task.A_CAROTISEXTERNA_L: """
Finde den Abgang der A. carotis externa links im Fixed Bild (obere Reihe).
Setze einen Punkt in die Mitte des Abgangs.
Der Abgang ist im Moving Bild markiert (untere Reihe).
""",

    Task.A_CAROTISEXTERNA_R: """
Finde den Abgang der A. carotis externa rechts im Fixed Bild (obere Reihe).
Setze einen Punkt in die Mitte des Abgangs.
Der Abgang ist im Moving Bild markiert (untere Reihe).
""",

    Task.LYMPH_NODE: """
Finde den Lymphknoten im Fixed Bild (obere Reihe) ({lymphnode_description}).
Setze einen Punkt in die Mitte des Lymphknotens.
Der Lymphknoten ist im Moving Bild markiert (untere Reihe).
""",

    Task.RECURRENCE: """
Entscheide, ob ein Rezidiv im Fixed Bild (obere Reihe) vorhanden ist ({recurrence_description}).
Wenn ja, setze einen Punkt in seine ungefähre Mitte.
"""
}


class Case():
    def __init__(self, current_case: int, case_count: int):
        self.current_case = current_case
        self.case_count = case_count

    def __str__(self):
        return f"Patient {self.current_case}/{self.case_count}"
