"""Utility functions for the fabric_mcp module."""

import logging


class Log:
    """Custom class to handle logging set up and log levels."""

    def __init__(self, level: str):
        """Initialize the Log class with a specific log level."""
        self._level_name = level.upper()
        self._level = Log.log_level(self._level_name)
        self._logger = logging.getLogger(__name__)
        logging.basicConfig(
            level=self.level,
            format="%(asctime)s - %(module)s - %(levelname)s - %(message)s",
        )

    @property
    def level_name(self) -> str:
        """Return the log level as a string."""
        return self._level_name

    @property
    def logger(self) -> logging.Logger:
        """Return the logger instance."""
        return self._logger

    @property
    def level(self) -> int:
        """Return the log level as an integer."""
        return self._level

    @staticmethod
    def log_level(level: str) -> int:
        """Convert a string log level to its corresponding integer value."""
        levels = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
        }
        if level not in levels:
            raise ValueError(
                f"Invalid log level: {level}. Choose from {list(levels.keys())}."
            )
        return levels.get(level.lower(), logging.INFO)
