"""Interpreter-version guard shared by every script under `scripts/` that
uses a Python feature newer than a bare `python3` on PATH might provide
(T-2236). Import this and call `require_python(__file__)` BEFORE any
project-`requires-python`-only import (e.g. `from datetime import UTC`,
a 3.11+ addition) -- import order matters here, this must run first.

This module itself must run under ANY `python3` on PATH, including one
far older than the project requires -- that is the whole point, so it
can detect the mismatch and say so instead of the interpreter raising a
raw `ImportError` three lines later. It therefore avoids any syntax or
stdlib feature newer than a conservative floor: no walrus operator, no
match statement, no f-string debug specifier, and -- critically -- no
`tomllib`, itself a 3.11+ stdlib addition that would make this guard
fail on exactly the interpreter it exists to detect.

Reads `requires-python` from `pyproject.toml`'s own `[project]` table via
a minimal regex, never a TOML parser -- the single source of truth
`pyproject.toml` already declares; this guard never hardcodes its own
copy of the version tuple, so it cannot drift from the real requirement.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_REQUIRES_PYTHON_RE = re.compile(r'requires-python\s*=\s*"[^\d]*(\d+)\.(\d+)')


def _required_version(pyproject_path: Path) -> tuple[int, int] | None:
    """`(major, minor)` parsed from `pyproject_path`'s own `requires-python
    = ">=X.Y"` line, or `None` if the file is unreadable or the line is
    missing/unparseable -- callers must treat `None` as "unknown", never
    as "no requirement" (see `require_python`'s own fail-open posture)."""
    try:
        text = pyproject_path.read_text(encoding="utf-8")
    except OSError:
        return None
    match = _REQUIRES_PYTHON_RE.search(text)
    if match is None:
        return None
    return (int(match.group(1)), int(match.group(2)))


# frob:doc docs/guides/coordinator-scripts.md#require_python
# frob:ticket T-2236
# frob:tests \
# tests/unit/test_require_python.py::TestRequirePython.test_older_interpreter_exits_non\
# zero_with_actionable_message kind="unit"
# frob:tests \
# tests/unit/test_require_python.py::TestRequirePython.test_supported_interpreter_is_a_\
# silent_noop kind="unit"
# frob:tests \
# tests/unit/test_require_python.py::TestRequirePython.test_exact_boundary_version_pass\
# es kind="unit"
# frob:tests \
# tests/unit/test_require_python.py::TestRequirePython.test_unknown_requirement_fails_o\
# pen_never_blocks kind="unit"
def require_python(script_path: str) -> None:
    """Exit(1) with an actionable message -- required version, found
    version, the correct invocation -- if the RUNNING interpreter is
    older than `pyproject.toml`'s own `requires-python`; a silent no-op
    otherwise (including when the requirement cannot be determined at
    all -- fail OPEN, never block a script this guard cannot itself
    evaluate). Call this as the very FIRST statement after `scripts/`'s
    own safe stdlib imports (`sys`, `re`, `pathlib`), before any import
    that might only work on the required version -- the whole reason
    this exists is that an import failure three lines later is a raw,
    unactionable `ImportError` traceback, not this message."""
    pyproject_path = Path(script_path).resolve().parent.parent / "pyproject.toml"
    required = _required_version(pyproject_path)
    if required is None:
        return
    if sys.version_info[:2] >= required:
        return
    found = "%d.%d.%d" % sys.version_info[:3]
    req_str = "%d.%d" % required
    script_name = Path(script_path).name
    sys.stderr.write(
        "ERROR: %s requires Python >=%s (found %s).\n"
        "This is whatever 'python3' resolves to on PATH, not this "
        "project's own venv -- run it through the venv instead:\n"
        "    uv run python %s\n" % (script_name, req_str, found, script_path)
    )
    sys.exit(1)
