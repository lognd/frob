"""One pytest-spawn resolution helper for the whole codebase (T-3311).

Measured before this ticket: THREE divergent conventions for spawning
pytest as a subprocess, each in a different verification call site --
`sys.executable, "-m", "pytest"` (`frob.gates._bug_repro`, the CORRECT
convention per T-3268's own precedent), a hardcoded `"uv", "run",
"pytest"` (`frob.app.ticket_runner._verify`), and a bare PATH lookup
`"pytest"` (`frob.refactor._verify`). A bare PATH lookup resolves to
whatever `pytest` happens to be first on `PATH` -- in a consumer
environment (an agent's shell, a CI runner with several venvs layered
onto `PATH`) that is usually NOT the project's own interpreter's pytest,
so collection/verification silently runs against the wrong project's
test suite or dependency set. `uv run pytest` assumes `uv` itself is
on `PATH` and a `pyproject.toml` `uv` recognises sits above `cwd` --
another dependency this repo does not otherwise require of a caller.

`sys.executable -m pytest` has neither problem: it is unconditionally
the interpreter the CALLING frob process itself is already running
under, so "this repo's pytest" and "the interpreter that resolved
`import frob`" are the same interpreter by construction. This module
makes that the ONE convention every pytest-spawning call site in this
codebase uses, per T-3268 (`frob.perf._profile`'s own adopted fix) and
T-3305 (`_python_for_tree`'s probe-don't-assume principle, applied here
to pytest itself rather than to `frob`).
"""

from __future__ import annotations

import sys

from typani import Err, ErrorSet, Ok
from typani.result import Result

from frob.logging import get_logger
from frob.process._guard import guarded_subprocess_run

_log = get_logger(__name__)


# frob:doc docs/modules/process.md#public-api
# frob:tests tests/unit/test_pytest_spawn.py::TestResolvePytestArgv.test_err_when_not_importable  # noqa: E501
class PytestSpawnError(ErrorSet):
    """`resolve_pytest_argv`'s one failure mode (T-3311): the resolved
    interpreter does not have `pytest` importable at all -- a spawn
    built from this argv would fail with pytest's own opaque "No module
    named pytest" (or, worse, silently resolve a DIFFERENT `pytest` off
    `PATH`), so this is caught and reported loudly before that argv is
    ever handed to a caller. `pytest` is OPTIONAL_FOR_GATE, not REQUIRED
    (T-3276's `ToolCategory`): frob itself still runs with it absent,
    only a caller that needs to actually RUN tests is affected -- so
    this is a typed `Result` a caller decides how to react to (report a
    gate UNMEASURED, skip a verification step), never a hard crash."""

    NotImportable = "pytest is not importable through the resolved interpreter"


# frob:doc docs/modules/process.md#public-api
# frob:tests tests/unit/test_pytest_spawn.py::TestPytestImportable.test_true_when_importable  # noqa: E501
# frob:tests tests/unit/test_pytest_spawn.py::TestPytestImportable.test_false_when_not_importable  # noqa: E501
def pytest_importable(python: str) -> bool:
    """Whether `pytest` actually imports through `python` (T-3311,
    T-3305's probe-don't-assume principle applied to pytest rather than
    `frob`): runs `<python> -c "import pytest"` with a short timeout and
    reports `True` only on a clean exit 0. A refused spawn
    (`FROB_DISABLE_EXEC=1`), a timeout, or any nonzero exit is "not
    importable" -- this never raises, so a probe failure only ever
    routes `resolve_pytest_argv` to `Err`, never crashes the caller."""
    try:
        guarded = guarded_subprocess_run(
            [python, "-c", "import pytest"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except OSError as exc:
        # `python` itself does not resolve to a real, executable file
        # (T-3305's own sibling probe hits the identical case, guarded
        # there by a pre-check on the venv path this function has no
        # equivalent for -- `python` here can be any caller-supplied
        # string, not always a pre-verified Path) -- "not importable" is
        # the correct verdict either way, never an uncaught crash.
        _log.warning(
            "pytest_spawn: could not spawn %s to probe pytest (%s) -- "
            "treating as not importable",
            python,
            exc,
        )
        return False
    if guarded.is_err:
        _log.warning(
            "pytest_spawn: probe of %s for an importable `pytest` refused "
            "or failed to spawn (%s) -- treating as not importable",
            python,
            guarded.danger_err,
        )
        return False
    return guarded.danger_ok.returncode == 0


# frob:doc docs/modules/process.md#public-api
# frob:tests tests/unit/test_pytest_spawn.py::TestResolvePytestArgv.test_ok_uses_sys_executable  # noqa: E501
# frob:tests tests/unit/test_pytest_spawn.py::TestResolvePytestArgv.test_appends_extra_args  # noqa: E501
# frob:tests tests/unit/test_pytest_spawn.py::TestResolvePytestArgv.test_err_when_not_importable  # noqa: E501
def resolve_pytest_argv(
    *args: str, python: str | None = None
) -> Result[list[str], PytestSpawnError]:
    """The ONE pytest-spawn argv resolution for this codebase (T-3311):
    `[python, "-m", "pytest", *args]`, `python` defaulting to
    `sys.executable` (the calling frob process's own interpreter, T-3268's
    adopted convention) -- never a bare `"pytest"` PATH lookup (resolves
    to whichever `pytest` happens to be first on a caller's `PATH`,
    frequently NOT this project's own) and never a hardcoded `"uv",
    "run", "pytest"` (assumes `uv` is on `PATH` and a `uv`-recognised
    `pyproject.toml` sits above `cwd`, a dependency this repo does not
    otherwise require of a caller).

    `Err(PytestSpawnError.NotImportable)` if `pytest_importable(python)`
    is `False` -- caught HERE, before the argv is ever handed to a
    spawner, so the failure is an explicit, loud, typed value instead of
    pytest's own opaque "No module named pytest" surfacing several
    layers away from where the interpreter was actually chosen."""
    resolved = python if python is not None else sys.executable
    if not pytest_importable(resolved):
        _log.error(
            "pytest_spawn: pytest is NOT importable through %s -- install "
            "it (pip install pytest, or: uv pip install pytest) before "
            "spawning; refusing to build an argv that would fail opaquely",
            resolved,
        )
        return Err(PytestSpawnError.NotImportable)
    return Ok([resolved, "-m", "pytest", *args])


__all__ = [
    "PytestSpawnError",
    "pytest_importable",
    "resolve_pytest_argv",
]
