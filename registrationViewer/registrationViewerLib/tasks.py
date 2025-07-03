from enum import Enum


class Task(Enum):
    NONE = "no_task"
    A_VERTEBRALIS_R = "a_vertebralis_r"
    A_VERTEBRALIS_L = "a_vertebralis_l"
    A_CAROTISEXTERNA_R = "a_carotisexterna_r"
    A_CAROTISEXTERNA_L = "a_carotisexterna_l"
    LYMPH_NODE = "lymph_node"
    RECURRENCE = "recurrence"
    TRAINING_NONE = "training_1_none"
    TRAINING_ROTATION = "training_2_rotation"
    TRAINING_NONLINEAR = "training_3_nonlinear"


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
Finden Sie den Abgang der A. vertebralis links im neuerem Fixed Bild (obere Reihe).
Setzen Sie einen Punkt in die Mitte des Abgangs.
Der Abgang ist im älterem Moving Bild markiert (untere Reihe).
""",

    Task.A_VERTEBRALIS_R: """
Finden Sie den Abgang der A. vertebralis rechts im neuerem Fixed Bild (obere Reihe).
Setzen Sie einen Punkt in die Mitte des Abgangs.
Der Abgang ist im älterem Moving Bild markiert (untere Reihe).
""",

    Task.A_CAROTISEXTERNA_L: """
Finden Sie den Abgang der A. carotis externa links im neuerem Fixed Bild (obere Reihe).
Setzen Sie einen Punkt in die Mitte des Abgangs.
Der Abgang ist im älterem Moving Bild markiert (untere Reihe).
""",

    Task.A_CAROTISEXTERNA_R: """
Finden Sie den Abgang der A. carotis externa rechts im neuerem Fixed Bild (obere Reihe).
Setzen Sie einen Punkt in die Mitte des Abgangs.
Der Abgang ist im älterem Moving Bild markiert (untere Reihe).
""",

    Task.LYMPH_NODE: """
Finden Sie den Lymphknoten ({lymphnode_description}) im neuerem Fixed Bild (obere Reihe).
Setzen Sie einen Punkt in die Mitte des Lymphknotens.
Der Lymphknoten ist im älterem Moving Bild markiert (untere Reihe).
""",

    Task.RECURRENCE: """
Entscheiden Sie, ob ein Rezidiv im neuerem Fixed Bild (obere Reihe) vorhanden ist. Die ursprüngliche Tumorresektion erfolgte im Bereich ({recurrence_description}).
Falls Sie ein Rezidiv erkennen, setzen Sie einen Punkt in dessen ungefähre Mitte.
""",

    Task.TRAINING_NONE: """
Dies ist eine Testaufgabe. In beiden Reihen wird dasselbe Bild angezeigt, daher ist die Registrierung perfekt.
Sie können die Registrierung mit der Taste „t“ oder dem Button "{Buttons.TURN_TRANSFORMATION_ON}" ein- und ausschalten, um den Effekt zu erkunden.
""",

    Task.TRAINING_ROTATION: """
Dies ist eine Testaufgabe. In beiden Reihen wird dasselbe Bild angezeigt, jedoch wurde das Bild in der unteren Reihe um 10° rotiert.
Es gibt daher keine exakt korrespondierenden Schichten zwischen den beiden Bildern.
Schalten Sie die Registrierung mit der Taste „t“ oder dem Button "{Buttons.TURN_TRANSFORMATION_ON}" ein und aus, um den Effekt zu erkunden.
""",

    Task.TRAINING_NONLINEAR: """
Dies ist eine Testaufgabe. Es werden zwei CT-Bilder desselben Patienten angezeigt, aufgenommen zu unterschiedlichen Zeitpunkten.
Das obere Bild ist das neuere – zwischen den Bildern liegt eine reale Deformation vor.
Diese Situation entspricht den Fällen, die in der eigentlichen Studie verwendet werden.
Schalten Sie die Registrierung mit der Taste „t“ oder dem Button "{Buttons.TURN_TRANSFORMATION_ON}" ein und aus, um den Effekt zu erkunden.
"""
}


class Case():
    def __init__(self, current_case: int, case_count: int):
        self.current_case = current_case
        self.case_count = case_count

    def __str__(self):
        return f"Patient {self.current_case}/{self.case_count}"
