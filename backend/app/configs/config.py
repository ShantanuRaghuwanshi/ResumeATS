# Common logging configuration
import logging

LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_LEVEL = logging.INFO


def setup_logging():
    logging.basicConfig(format=LOG_FORMAT, level=LOG_LEVEL)


def get_logger(name=None):
    setup_logging()
    return logging.getLogger(name)
