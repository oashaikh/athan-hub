import json
import logging
from logging.handlers import RotatingFileHandler

from .config import get_settings


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        item = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "time": self.formatTime(record),
        }
        if record.exc_info:
            item["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(item)


def configure_logging() -> None:
    settings = get_settings()
    root = logging.getLogger()
    root.setLevel(settings.log_level.upper())
    if root.handlers:
        return
    stream = logging.StreamHandler()
    stream.setFormatter(JsonFormatter())
    root.addHandler(stream)
    if settings.log_to_file:
        handler = RotatingFileHandler(settings.log_dir / "athan-hub.log", maxBytes=5_000_000, backupCount=3)
        handler.setFormatter(JsonFormatter())
        root.addHandler(handler)

