from enum import Enum
import logging
from pathlib import Path
import traceback

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..registrationViewer import registrationViewerWidget


class LogType(Enum):
    U_MOUSE = "U_MOUSE"
    U_BUTTON = "U_BUTTON"
    U_KEYBOARD = "U_KEYBOARD"
    SAVE = "SAVE"
    INTERNAL = "INTERNAL"


_logger: "MyLogger" = None


class MyLogger:
    def __init__(self,
                 widget: "registrationViewerWidget",
                 log_file_path: str,
                 name: str = "RegistrationEvaluation") -> None:

        self.widget = widget

        self.log_file_path = log_file_path
        self.name = name

        Path(self.log_file_path).parent.mkdir(parents=True, exist_ok=True)

        self._set_up_logger()

    def _set_up_logger(self) -> None:
        self.logger = logging.getLogger(self.name)

        # Clear existing handlers if any.
        if self.logger.hasHandlers():
            self.logger.handlers.clear()

        self.logger.setLevel(logging.DEBUG)
        self.logger.propagate = False

        file_handler = logging.FileHandler(self.log_file_path)
        file_handler.setLevel(logging.DEBUG)

        formatter = logging.Formatter(
            '%(asctime)s ~ %(name)s ~ %(levelname)s ~ %(prefix)s ~ %(message)s'
        )
        file_handler.setFormatter(formatter)

        self.logger.addHandler(file_handler)

    def log(self, log_level: int, log_type: LogType, message: str) -> None:

        try:
            prefix = f"{log_type.value} ~ task_idx_{self.widget.current_combination_idx:04d} ~ {self.widget.current_radiologist_id} ~ {self.widget.current_patient_name} ~ {self.widget.study_current_transform_type} ~ {self.widget.current_task.value}"

        except Exception as e:
            log_level = logging.ERROR
            log_type = LogType.INTERNAL
            message = f"Error while logging: {e}\n{traceback.format_exc()}"

            prefix = log_type.value

        self.logger.log(log_level, message, extra={"prefix": prefix})


def configure_logger(widget: "registrationViewerWidget",
                     log_file_path: str,
                     name: str) -> None:
    global _logger
    try:
        _logger = MyLogger(widget, log_file_path, name)
    except Exception as e:
        default_path = Path.home() / "registrationViewer.log"
        _logger = MyLogger(widget, default_path, name)


def log(log_level: int, log_type: LogType, message: str) -> None:
    """
    Logs a message to the log file
    """

    global _logger
    if _logger is None:
        raise ValueError("Logger not configured")

    _logger.log(log_level, log_type, message)
