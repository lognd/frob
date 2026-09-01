# frob:ticket T-1511
"""Shared `tests/unit/**` test-support fixtures/stand-ins. `pytest.fixture`
functions here are auto-injected by pytest's own conftest discovery; plain
classes/functions (e.g. `_FakeCompletedProcess`, `_load_committed_coverage_
lock`) are NOT auto-injected and must be imported explicitly (`from
tests.unit.conftest import _FakeCompletedProcess`) -- `tests/` is a real
package (`tests/__init__.py`), so this is a normal absolute import, not
pytest plugin machinery."""

from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path
from types import ModuleType
from typing import Any

#: Repo root, three levels up from this file (tests/unit/conftest.py ->
#: repo root) -- the same computation `test_coverage_attribution_lock_
#: t1395.py`/`test_makefile_coverage.py` each used to duplicate privately.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent

_SCRIPTS = _REPO_ROOT / "scripts"


# frob:ticket T-2236
def _load_script(name: str) -> ModuleType:
    """Import `scripts/<name>.py` by path (`scripts/` has no
    `__init__.py`, so it is not an ordinary package import). Promoted
    here (T-2236) from two identical per-file copies
    (`test_coordinator_scripts.py::_load`, `test_require_python.py::
    _load`) once a second consumer confirmed the duplication."""
    path = _SCRIPTS / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"_scripts_under_test.{name}", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


def _report(*, results: list[dict[str, Any]]) -> dict[str, Any]:
    """A minimal `frob check --json`-shaped report for the given results."""
    return {"results": results}


def _completed(stdout: str = "", returncode: int = 0) -> subprocess.CompletedProcess:
    """A `subprocess.CompletedProcess` stub for monkeypatching `subprocess.run`."""
    return subprocess.CompletedProcess(
        args=[], returncode=returncode, stdout=stdout, stderr=""
    )


def _write_ticket(
    tickets_dir: Path,
    ticket_id: str,
    *,
    state: str = "queued",
    priority: str = "high",
    created: str = "2026-01-01",
    tier: str = "ticket",
    runs_last: bool = False,
    parent: str | None = None,
    blocked_by: tuple[str, ...] = (),
) -> None:
    """Write a minimal `tickets/<id>/ticket.md` fixture file with just the
    frontmatter fields `_parse_ticket_ledger_file` reads. `runs_last`
    (T-2200) is written as the same flat `key: value` line real
    `frob ticket` output uses (`runs_last: true`/`runs_last: false`), the
    STRUCTURED field the parser reads -- never inferred from `title`, so a
    fixture whose title happens to say 'RUNS LAST' (mirroring T-1614's
    real title) with `runs_last=False` must NOT be treated as deferred.
    `parent` (T-2229), when given, is written the same way real `frob
    ticket new --parent` output is; omitted entirely when `None` (mirrors
    a ledger row with no `parent:` line at all, not a literal 'null').
    `blocked_by` (T-2449), when non-empty, is written as the same `- item`
    list-block shape real `frob ticket new --blocked-by` output uses;
    omitted entirely when empty (mirrors a ledger row with no
    `blocked_by:` key at all)."""
    ticket_dir = tickets_dir / ticket_id
    ticket_dir.mkdir(parents=True)
    parent_line = f"parent: {parent}\n" if parent is not None else ""
    blocked_by_block = (
        "blocked_by:\n" + "".join(f"- {b}\n" for b in blocked_by) if blocked_by else ""
    )
    (ticket_dir / "ticket.md").write_text(
        f"---\n"
        f"id: {ticket_id}\n"
        f"title: 'a title'\n"
        f"state: {state}\n"
        f"kind: feature\n"
        f"created: '{created}'\n"
        f"priority: {priority}\n"
        f"tier: {tier}\n"
        f"runs_last: {'true' if runs_last else 'false'}\n"
        f"{parent_line}"
        f"{blocked_by_block}"
        f"---\n",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# scripts/ module loads shared across tests.unit.coordinator_suite families
# (T-3594 split: check_summary/fleet_status/verify_lands/wait_for_land_slot
# are each used by more than one destination family, so they live here
# rather than in any single per-family module).
# ---------------------------------------------------------------------------

check_summary = _load_script("check_summary")
fleet_status = _load_script("fleet_status")
verify_lands = _load_script("verify_lands")
wait_for_land_slot = _load_script("wait_for_land_slot")
