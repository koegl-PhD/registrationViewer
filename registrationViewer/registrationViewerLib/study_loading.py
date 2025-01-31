from dataclasses import dataclass, field
from collections import defaultdict
import json

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
                                   "ids_patients_transformation_nonolinear"]:
                for patient_id in info.get(transform_type, []):
                    reversed_mapping[patient_id].append(rad_id)

        return dict(reversed_mapping)

    def save(self, json_path=None):
        if json_path is None:
            json_path = self.path

        with open(json_path, "w") as f:
            json.dump(self.data, f, indent=4)
