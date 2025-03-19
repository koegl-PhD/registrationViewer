from enum import Enum
import logging
from pathlib import Path


class LogType(Enum):
    U_MOUSE = "U_MOUSE"
    U_BUTTON = "U_BUTTON"
    U_KEYBOARD = "U_KEYBOARD"
    SAVE = "SAVE"
    INTERNAL = "INTERNAL"


_log_file_path: str = ""
_log_prefix: str = ""
_logger: logging.Logger = None


def configure_logger(log_file_path: str) -> None:
    """
    Configures the logger (for now only the path to the log file).
    """
    global _log_file_path
    _log_file_path = log_file_path

    parent_dir = Path(_log_file_path).parent

    if not parent_dir.exists():
        parent_dir.mkdir(parents=True)


def set_log_prefix(prefix: str) -> None:
    """
    Sets the prefix for each log message
    """
    global _log_prefix
    _log_prefix = prefix


class DynamicPrefixFilter(logging.Filter):
    """
    Dynamically inserts the global log prefix into the log message,
    combining it with an existing prefix if provided.
    """

    def filter(self, record: logging.LogRecord) -> bool:

        # Check if an extra prefix was provided via the extra parameter.
        provided_prefix = getattr(record, "prefix", "")

        # Combine the global prefix with the provided one.
        if provided_prefix:
            record.prefix = f"{_log_prefix} ~ {provided_prefix}"
        else:
            record.prefix = _log_prefix

        return True


def _get_logger(name: str = "RegistrationEvaluation") -> logging.Logger:

    if _log_file_path == "":
        raise ValueError(
            "Logger is not configured. Please call configure_logger() first.")

    logger = logging.getLogger(name)

    # Clear existing handlers if any.
    if logger.hasHandlers():
        logger.handlers.clear()

    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    log_file_path = _log_file_path

    file_handler = logging.FileHandler(log_file_path)
    file_handler.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        '%(asctime)s ~ %(name)s ~ %(levelname)s ~ %(prefix)s ~ %(message)s'
    )
    file_handler.setFormatter(formatter)

    file_handler.addFilter(DynamicPrefixFilter())

    logger.addHandler(file_handler)

    return logger


def log(log_level: int, log_type: LogType, message: str) -> None:
    """
    Logs a message to the log file
    """

    global _logger
    if _logger is None:
        _logger = _get_logger()

    _logger.log(log_level, message, extra={"prefix": log_type.value})
