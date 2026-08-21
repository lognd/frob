"""T-2596 regression: `src/frob/scaffold/project.py` carried genuine E501
(over-88-character) lines with no `# noqa` exemption. `per-file-ignores`
only covers `tests/**`/`tests/fixtures/**`, so `src/` never gets a pass --
these were real style debt, not gate noise, and their presence raised
quarantine, forcing the whole agent fleet into synchronous lands (T-1693).

This test locks the file's real line length directly, independent of ruff
config, so a future line that creeps back over 88 characters (without a
`# noqa: E501`) is caught here too -- and `# noqa: E501`-carrying
`frob:tests` directive lines (which genuinely cannot be wrapped) are
explicitly exempted, matching ruff's own per-file-ignores posture.
"""

from __future__ import annotations

from pathlib import Path

_PROJECT_PY = Path(__file__).resolve().parents[2] / "src/frob/scaffold/project.py"
_MAX_LINE_LEN = 88


class TestScaffoldProjectLineLength:
    """No unwaived over-88-character line in `src/frob/scaffold/project.py`."""

    def test_no_unexempted_long_lines(self) -> None:
        """Every line in project.py is <=88 chars, or carries `# noqa: E501`."""
        text = _PROJECT_PY.read_text()
        offenders = [
            (i, line)
            for i, line in enumerate(text.splitlines(), start=1)
            if len(line) > _MAX_LINE_LEN and "noqa" not in line
        ]
        assert offenders == [], (
            f"unexempted over-{_MAX_LINE_LEN}-char line(s) in project.py: {offenders}"
        )
