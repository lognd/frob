"""BARETOOL001 finder (T-3887/T-4125): an AST scan for a bare toolchain
binary name (`"ty"`, `"ruff"`, `"pytest"`, ...) as the FIRST element of a
`List`/`Tuple` literal anywhere in a Python module's source.

WHY A BARE FIRST ELEMENT, not just a call-argument shape: T-4125's own
population measurement found the defect in TWO shapes -- an argv literal
built directly at a spawn call site (`subprocess.run(["ruff", ...])`) AND
one built into an intermediate variable several lines before the spawn
(`cmd = ["ty", "check", *py_files]` ... later ... `subprocess.run(cmd,
...)`, `_land_cmd.py`'s exact measured shape). Restricting the scan to
direct call arguments would have missed the second shape -- the one this
repo's own source actually had. Scanning every `List`/`Tuple` literal's
first element, independent of where it is used, catches both without
needing to trace the variable to its eventual spawn call (a much larger,
inter-statement dataflow problem `frob.vet._taint` already discloses it
does not attempt across function boundaries).

WHAT COUNTS AS BARE: the literal's first element is a string `Constant`
whose value is in `BARE_TOOLCHAIN_NAMES` (T-4125's measured population:
`ty`, `ruff`, `pytest`, plus the same-class tools this repo's own
toolchain declares: `mypy`, `black`, `isort`, `pyright`). A list whose
first element is `"uv"` (the correct `project_tool_argv`/`uv run`
spelling), `sys.executable`, or any non-string-constant expression
(a variable, an attribute access, `*args` unpacking as the first
element) is NOT flagged -- this pass only proves a HARDCODED bare name,
never guesses at a dynamically-built argv's ultimate resolution.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from frob.logging import get_logger

_log = get_logger(__name__)

__all__ = ["BareToolchainFinding", "BARE_TOOLCHAIN_NAMES", "bare_toolchain_findings"]

#: T-4125's measured population (`ty`, `ruff`, `pytest`) plus the other
#: Python toolchain binaries this repo's own `pyproject.toml`
#: dev-dependencies name -- the set a bare-name argv literal in THIS
#: codebase could plausibly spell. Deliberately not "every conceivable
#: CLI tool": a name outside this set is not this repo's own toolchain
#: and flagging it would be a false-positive generator with no fix this
#: mechanism can offer (`project_tool_argv` only routes tools the
#: PROJECT's own `uv`-managed environment can resolve).
# frob:doc docs/modules/process.md#project-scoped-toolchain-spawns-t-3887t-4125
BARE_TOOLCHAIN_NAMES: frozenset[str] = frozenset(
    {"ty", "ruff", "pytest", "mypy", "black", "isort", "pyright"}
)


# frob:doc docs/modules/process.md#project-scoped-toolchain-spawns-t-3887t-4125
# frob:tests tests/unit/vet/test_bare_toolchain.py::TestBareToolchainFindings.test_flags_bare_argv_literal  # noqa: E501
@dataclass(frozen=True)
class BareToolchainFinding:
    """One bare-toolchain-name argv literal: `tool` is the flagged name,
    `line`/`col` locate the `List`/`Tuple` literal itself (not the
    eventual spawn call, which may be lines away)."""

    tool: str
    line: int
    col: int


def _first_string_constant(elts: list[ast.expr]) -> tuple[str, int, int] | None:
    """`(value, line, col)` of the first element of `elts` if it is a
    plain string `Constant`, else `None` -- `*args` unpacking (`ast.
    Starred`), a `Name`/`Attribute`/anything else as the first element
    is deliberately not a match (see module docstring). Returns the
    narrowed `str` value directly (not the `ast.Constant` node, whose
    `.value` is typed `object`) so callers never re-narrow it."""
    if not elts:
        return None
    first = elts[0]
    if isinstance(first, ast.Constant) and isinstance(first.value, str):
        return first.value, first.lineno, first.col_offset
    return None


# frob:doc docs/modules/process.md#project-scoped-toolchain-spawns-t-3887t-4125
# frob:tests tests/unit/vet/test_bare_toolchain.py::TestBareToolchainFindings.test_clean_on_project_tool_argv_spelling  # noqa: E501
def bare_toolchain_findings(path: Path) -> list[BareToolchainFinding]:
    """Every `List`/`Tuple` literal in `path` whose first element is a
    bare `BARE_TOOLCHAIN_NAMES` string constant -- a syntax error or
    unreadable file yields `[]` (a file this pass cannot parse is not
    this pass's finding to report; `frob check`'s own parse-error family
    covers that separately)."""
    try:
        source = path.read_text(encoding="utf-8")
    except OSError as exc:
        _log.debug("bare_toolchain_findings: skipping unreadable %s: %s", path, exc)
        return []
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        _log.debug("bare_toolchain_findings: skipping unparsable %s: %s", path, exc)
        return []

    findings: list[BareToolchainFinding] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.List, ast.Tuple)):
            continue
        first = _first_string_constant(node.elts)
        if first is None:
            continue
        value, line, col = first
        if value in BARE_TOOLCHAIN_NAMES:
            findings.append(BareToolchainFinding(tool=value, line=line, col=col))
    return findings
