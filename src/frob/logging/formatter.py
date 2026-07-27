import logging


# frob:doc docs/modules/logging.md#public-api
# frob:waive COV007 reason="docs/modules/logging.md's Public API section individually \
# frob:describes this private formatter and its .format method by name (T-0529) -- a \
# deliberate architecture doc, not accidental drift onto a private helper"
class _FrobFormatter(logging.Formatter):
    """
    Plain formatter. INFO and DEBUG emit just the message; WARNING+ prefix
    with the level name so errors are easy to spot without color codes.
    """

    def __init__(self, show_level: bool = False) -> None:
        super().__init__()
        self._show_level = show_level

    # frob:ticket T-0588
    # frob:tests tests/system/test_cli_check.py::TestGitlessTargetGateSeverity.test_render_lint_gate_warns_not_errors_on_gitless_root  # noqa: E501
    def format(self, record: logging.LogRecord) -> str:
        # frob:doc docs/modules/logging.md#public-api
        msg = record.getMessage()
        if self._show_level or record.levelno >= logging.WARNING:
            return f"{record.levelname}: {msg}"
        return msg
