# frob:ticket T-1511
"""Shared `tests/unit/**` test-support fixtures/stand-ins. `pytest.fixture`
functions here are auto-injected by pytest's own conftest discovery; plain
classes/functions (e.g. `_FakeCompletedProcess`, `_load_committed_coverage_
lock`) are NOT auto-injected and must be imported explicitly (`from
tests.unit.conftest import _FakeCompletedProcess`) -- `tests/` is a real
package (`tests/__init__.py`), so this is a normal absolute import, not
pytest plugin machinery."""

from __future__ import annotations

import json
from pathlib import Path

#: Repo root, three levels up from this file (tests/unit/conftest.py ->
#: repo root) -- the same computation `test_coverage_attribution_lock_
#: t1395.py`/`test_makefile_coverage.py` each used to duplicate privately.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


# frob:ticket T-1551
# frob:waive WIRE001 reason="a shared per-file fixture helper used only by this \
# package's own test modules (test_coverage_attribution_lock_t1395.py, \
# test_makefile_coverage.py) -- there is no production caller to wire it to by design, \
# it exists solely to read the committed frob-coverage.lock.json for a regression \
# lock" permanent="true"
def _load_committed_coverage_lock() -> dict[str, float]:
    """`module_line` mapping from the committed `frob-coverage.lock.json`.

    Reads the repo-root lock directly (the same file `write_coverage_lock`/
    `load_coverage_lock` in `frob.gates._coverage` produce and consume) --
    a small, self-contained fixture-free check that named modules stay
    attributed, without depending on a fresh `coverage.xml` this repo does
    not keep around (playbook section 6d). Promoted here (T-1551) from two
    near-identical per-file copies (`test_coverage_attribution_lock_
    t1395.py::_load_committed_lock`, `test_makefile_coverage.py::
    TestPreviouslyZeroModulesNowAttributeInTheCommittedLock.
    _load_committed_lock`) once a second occurrence confirmed the
    duplication (T-1490 found but did not fix this second copy, out of
    its own declared scope)."""
    lock_path = _REPO_ROOT / "frob-coverage.lock.json"
    data = json.loads(lock_path.read_text())
    return data["module_line"]


# frob:ticket T-1511
class _FakeCompletedProcess:
    """Minimal `subprocess.CompletedProcess`-shaped stand-in for a
    monkeypatched `guarded_subprocess_run` return -- promoted here from two
    identical per-file copies (`tests/unit/test_check_ts_runners.py`,
    `tests/unit/test_check_native_cargo_runners.py`) once a second consumer
    confirmed the duplication (T-1511's own follow-up criterion: "if more
    runner tests want the same stub")."""

    def __init__(self, stdout: str = "", stderr: str = "", returncode: int = 0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode
