import logging

from custom_logging import configure_logger, set_log_prefix, log, LogType

configure_logger("test.log")

set_log_prefix("test_prefix")

log(logging.INFO, LogType.MOUSE, "Test message mouse")
log(logging.DEBUG, LogType.BUTTON, "Test message button")
log(logging.WARNING, LogType.KEYBOARD, "Test message keyboard")
log(logging.ERROR, LogType.ANNOTATION, "Test message annotaiton")
