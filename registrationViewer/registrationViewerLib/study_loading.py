from dataclasses import dataclass, field
from collections import defaultdict
import json

from typing import List, Tuple

from registrationViewerLib.tasks import TransformType

path = r"/home/koeglf/Documents/code/registrationViewer/registrationViewer/Resources/example_study/data_master.json"


@dataclass
class StudyData:
    path: str
    data: dict = field(init=False)
    patient_to_rads: dict = field(init=False, default_factory=dict)

    def __post_init__(self):
        with open(self.path, "r") as f:
            self.data = json.load(f)

        self.__dict__.update(self.data)

        self.patient_to_rads = self._reverse_participants()

    def _reverse_participants(self):
        reversed_mapping = defaultdict(list)

        for rad_id, info in self.participants.items():
            for transform_type in ["ids_patients_transformation_none",
                                   "ids_patients_transformation_linear",
                                   "ids_patients_transformation_nonlinear"]:
                for patient_id in info.get(transform_type, []):
                    reversed_mapping[patient_id].append(rad_id)

        return dict(reversed_mapping)

    def save(self, json_path=None):
        if json_path is None:
            json_path = self.path

        with open(json_path, "w") as f:
            json.dump(self.data, f, indent=4)

    def patient_list(self, rad_id: str) -> List[Tuple[TransformType, str]]:

        participant = self.participants.get(rad_id, None)
        if participant is None:
            raise ValueError(f"Rad id {rad_id} not found in data")

        result = []

        for transform_type in ["ids_patients_transformation_nonlinear",
                               "ids_patients_transformation_linear",
                               "ids_patients_transformation_none"]:
            for patient in participant[transform_type]:
                result.append(
                    (TransformType(transform_type.split("_")[-1]), patient))

        return result
