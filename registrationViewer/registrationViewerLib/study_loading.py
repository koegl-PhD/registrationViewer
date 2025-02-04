from dataclasses import dataclass, field
from collections import defaultdict
import json

from typing import List, Tuple

import slicer

from registrationViewerLib import utils

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

    def patient_list(self, rad_id: str) -> List[Tuple[utils.TransformType, str]]:

        participant = self.participants.get(rad_id, None)
        if participant is None:
            raise ValueError(f"Rad id {rad_id} not found in data")

        result = []

        for transform_type in ["ids_patients_transformation_nonlinear",
                               "ids_patients_transformation_linear",
                               "ids_patients_transformation_none"]:
            for patient in participant[transform_type]:
                result.append(
                    (utils.TransformType(transform_type.split("_")[-1]), patient))

        # sort by transform_type
        # result.sort(key=lambda x: x[0].value)

        return result


def load_study_volumes(self, path_case: str) -> None:

    slicer.progressWindow = slicer.util.createProgressDialog()
    slicer.progressWindow.show()
    slicer.progressWindow.activateWindow()
    slicer.progressWindow.setValue(0)
    slicer.progressWindow.setLabelText(
        f"Loading data...")
    slicer.app.processEvents()

    path_volume_fixed, path_volume_moving, \
        _, _, \
        path_transform_fixed, path_transform_moving, \
        path_deformation = utils.get_paths_to_load(path_case)

    utils.update_progress_window(0, f"Loading data...")
    node_volume_fixed = slicer.util.loadVolume(path_volume_fixed,
                                               {'show': False})

    utils.update_progress_window(10, f"Loading data...")
    node_volume_moving = slicer.util.loadVolume(path_volume_moving,
                                                {'show': False})

    utils.update_progress_window(40, f"Loading data...")
    self.node_transform_fixed = slicer.util.loadTransform(path_transform_fixed,
                                                          {'show': False})[1]

    utils.update_progress_window(50, f"Loading data...")
    self.node_transform_moving = slicer.util.loadTransform(path_transform_moving,
                                                           {'show': False})[1]

    utils.update_progress_window(60, f"Loading data...")
    node_deformation = slicer.util.loadTransform(path_deformation,
                                                 {'show': False})[1]

    utils.update_progress_window(100, f"Loading data...")

    self.ui_sub_3.inputSelector_fixed.setCurrentNode(
        node_volume_fixed)
    self.ui_sub_3.inputSelector_moving.setCurrentNode(
        node_volume_moving)
    self.ui_sub_3.inputSelector_transformation.setCurrentNode(
        node_deformation)

    slicer.progressWindow.close()
