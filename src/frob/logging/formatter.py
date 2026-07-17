import logging


# frob:doc docs/modules/logging.md#public-api
class FrobFormatter(logging.Formatter):
    """
    Plain formatter. INFO and DEBUG emit just the message; WARNING+ prefix
    with the level name so errors are easy to spot without color codes.
    """

    def __init__(self, show_level: bool = False) -> None:
        super().__init__()
        self._show_level = show_level

    def format(self, record: logging.LogRecord) -> str:
        # frob:doc docs/modules/logging.md#public-api
        msg = record.getMessage()
        if self._show_level or record.levelno >= logging.WARNING:
            return f"{record.levelname}: {msg}"
        return msg
