import logging
from typing import List


class FormattedMessageCollectorHandler(logging.Handler):
    """A logging handler that stores formatted log records in its "messages" attribute."""

    def __init__(self, level=logging.NOTSET) -> None:
        """Create a new log handler."""
        super().__init__(level=level)
        self.level = level
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        """Keep the log records in a list in addition to the log text."""
        self.messages.append(self.format(record))

    def reset(self) -> None:
        """Empty the list of messages"""
        self.messages = []
