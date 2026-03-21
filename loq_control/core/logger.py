import logging
import logging.handlers
import threading
from pathlib import Path
import sys


class LoqLogger:
    """
    Unified Logging + Diagnostics Framework

    Features:
    - Rotating logs
    - Multi-channel hardware logging
    - Safe fallback
    - Debug mode streaming
    """

    _instance = None
    _lock = threading.Lock()

    LOG_DIR = Path.home() / ".local" / "state" / "loq-control" / "logs"

    CHANNELS = [
        "daemon",
        "hardware",
        "gpu",
        "cpu",
        "thermal",
        "firmware",
        "ui",
        "events",
        "ec"
    ]

    def __init__(self, debug=False):
        self.debug = debug
        self.loggers = {}

        self.LOG_DIR.mkdir(parents=True, exist_ok=True)

        for channel in self.CHANNELS:
            self.loggers[channel] = self._create_logger(channel)

    @classmethod
    def get(cls, debug=False):
        with cls._lock:
            if cls._instance is None:
                cls._instance = LoqLogger(debug=debug)
        return cls._instance

    # --------------------------------------------------
    # LOGGER CREATION
    # --------------------------------------------------

    def _create_logger(self, name):
        logger = logging.getLogger(f"loq.{name}")
        logger.setLevel(logging.DEBUG)

        if logger.handlers:
            return logger

        file_handler = logging.handlers.RotatingFileHandler(
            self.LOG_DIR / f"{name}.log",
            maxBytes=2 * 1024 * 1024,
            backupCount=3
        )

        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(threadName)s | %(message)s"
        )

        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        if self.debug:
            stream = logging.StreamHandler(sys.stdout)
            stream.setFormatter(formatter)
            logger.addHandler(stream)

        return logger

    # --------------------------------------------------
    # PUBLIC API
    # --------------------------------------------------

    def log(self, channel, level, message, *args):
        try:
            logger = self.loggers.get(channel)
            if not logger:
                # Fallback to daemon if channel is unregistered
                logger = self.loggers.get("daemon")
                if not logger:
                    return

            if level == "debug":
                logger.debug(message, *args)
            elif level == "info":
                logger.info(message, *args)
            elif level == "warn":
                logger.warning(message, *args)
            elif level == "error":
                logger.error(message, *args)
            elif level == "critical":
                logger.critical(message, *args)

        except Exception:
            # logging must NEVER crash system
            pass

    # Convenience wrappers

    def daemon(self, level, msg, *args): self.log("daemon", level, msg, *args)
    def gpu(self, level, msg, *args): self.log("gpu", level, msg, *args)
    def cpu(self, level, msg, *args): self.log("cpu", level, msg, *args)
    def thermal(self, level, msg, *args): self.log("thermal", level, msg, *args)
    def firmware(self, level, msg, *args): self.log("firmware", level, msg, *args)
    def hardware(self, level, msg, *args): self.log("hardware", level, msg, *args)
    def ui(self, level, msg, *args): self.log("ui", level, msg, *args)
    def events(self, level, msg, *args): self.log("events", level, msg, *args)
    def ec(self, level, msg, *args): self.log("ec", level, msg, *args)


# --------------------------------------------------
# BACKWARD COMPATIBILITY SHIM FOR LEGACY CODEBASE
# --------------------------------------------------

class ShimLogger:
    """Wraps LoqLogger to support standard standard .info()/.debug() calls"""
    def __init__(self, name: str):
        # Map loq-control.events -> events, loq-control.daemon -> daemon
        self.channel = name.split(".")[-1]
        self.loq = LoqLogger.get()

    def _format(self, msg, *args):
        return str(msg) % args if args else str(msg)

    def debug(self, msg, *args): self.loq.log(self.channel, "debug", self._format(msg, *args))
    def info(self, msg, *args): self.loq.log(self.channel, "info", self._format(msg, *args))
    def warning(self, msg, *args): self.loq.log(self.channel, "warn", self._format(msg, *args))
    def error(self, msg, *args): self.loq.log(self.channel, "error", self._format(msg, *args))
    def critical(self, msg, *args): self.loq.log(self.channel, "critical", self._format(msg, *args))
    def exception(self, msg, *args): self.loq.log(self.channel, "error", self._format(msg, *args) + " (Exception)")

def get_logger(name: str):
    """Facade for legacy imports"""
    return ShimLogger(name)
