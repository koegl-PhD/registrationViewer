import logging

from typing import TYPE_CHECKING

from registrationViewerLib.custom_logging import log, LogType

if TYPE_CHECKING:
    from ..registrationViewer import registrationViewerWidget


def log_all_chunks(self: "registrationViewerWidget") -> None:
    """
    Logs all chunks.
    """

    log(logging.INFO, LogType.INTERNAL, "All chunks START")

    for i, chunk in enumerate(self.study_data.chunked_patients[1]):
        log(logging.INFO, LogType.INTERNAL,
            f"Chunk {i+1}/{len(self.study_data.chunked_patients[1])}:")

        for patient_name, transform, present in chunk:
            log(logging.INFO, LogType.INTERNAL,
                f"\t{present} - {patient_name}")
    log(logging.INFO, LogType.INTERNAL, "All chunks END")


def log_all_tasks(self: "registrationViewerWidget") -> None:
    """
    Logs all tasks.
    """

    task_map = self.study_data.case_task_transformation_map[self.current_radiologist_id]

    log(logging.INFO, LogType.INTERNAL, "All tasks to be done START")
    for idx, combination in enumerate(task_map):
        log(logging.INFO, LogType.INTERNAL,
            f"Combination {idx+1}/{len(task_map)}: {combination}")
    log(logging.INFO, LogType.INTERNAL, "All tasks to be done END")
