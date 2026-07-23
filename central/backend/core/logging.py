import logging
import os

BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

LOG_DIR = os.path.join(BASE_DIR, "logs")

# Create logs directory if it doesn't exist
os.makedirs(LOG_DIR, exist_ok=True)

def setup_logging():
    logger = logging.getLogger("vigilai")

    if logger.hasHandlers():
        return logger

    logger.setLevel(logging.INFO)

    log_format = logging.Formatter(
        "%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s - %(message)s"
    )

    log_file = os.path.join(LOG_DIR, "app.log")

    file_handler = logging.FileHandler(
        log_file,
        encoding="utf-8"
    )
    file_handler.setFormatter(log_format)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_format)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger