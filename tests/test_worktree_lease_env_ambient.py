"""T-3145: an AMBIENT `FROB_WORKTREE` -- one already present in the pytest
worker's own `os.environ` BEFORE any test's own body runs, e.g. inherited
from `frob ticket evidence`'s individual-reverify subprocess spawn when
the recording agent is itself working inside a leased worktree -- must
not leak into a test that calls `new_ticket` (or any other
`enforce_worktree_lease`-guarded mutator) against an unrelated `tmp_path`
fake repo.

This is a DIFFERENT root cause from T-3123: that ticket closed a leak
BETWEEN tests within the same long-lived pytest worker (one test sets
`FROB_WORKTREE` via `apply_agent_env` and never restores it, so a LATER
test in the same worker sees it). T-3123's own fixture
(`_isolate_worktree_lease_env_before_test`) only SNAPSHOTS the value
present at each test's own setup and restores it to that same value
afterward -- it never CLEARS the var during the test body, so a value
already present when the fixture's setup first runs (this ticket's
scenario: inherited from the SPAWNING process, before pytest collection
even starts) survives untouched through every test that fixture ever
wraps. Confirmed directly against the real production path: `FROB_
WORKTREE=<a real leased worktree path> uv run python3 -c "from
frob.tickets import new_ticket, ...; new_ticket(Path('<some unrelated
tmp_path fake repo>'), spec)"` returns `Err(WorktreeLeaseViolation)` even
though the target repo has nothing to do with the leased worktree.

A `monkeypatch.setenv` call INSIDE a test's own body cannot reproduce
this: by the time a test body executes, every fixture that applies to it
-- including `tests/conftest.py`'s function-scoped autouse isolation
fixture -- has already completed its OWN setup phase, so a value only
set from within the test body could never have been present when that
fixture's setup ran. The faithful simulation is a MODULE-scoped autouse
fixture in this file that writes `os.environ` directly, since pytest
sets up broader-scoped fixtures (module) before narrower ones (function)
for the same test -- this genuinely runs before `tests/conftest.py`'s
per-test isolation fixture gets to see or touch the value, exactly
modeling "already set when the worker started."
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

#: A path no real `FROB_WORKTREE` lease will ever resolve to -- compared
#: against explicitly rather than "unset", matching
#: `tests/test_ticket_land.py::TestWorktreeLeaseEnvIsolation`'s own
#: precedent (T-3123): a dispatched agent's real shell legitimately
#: carries a real lease, so asserting plain absence would itself be
#: wrong under ordinary dispatch, independent of any leak.
_AMBIENT_SENTINEL = "/nonexistent/T-3145-ambient-leak-sentinel/wt"


# frob:ticket T-3145
@pytest.fixture(scope="module", autouse=True)
def _simulate_frob_worktree_ambient_before_any_test_in_this_module() -> None:
    """Writes `FROB_WORKTREE` directly into `os.environ`, module-scoped
    (not function-scoped) so it is already present BEFORE `tests/
    conftest.py`'s function-scoped `_isolate_worktree_lease_env_before_
    test` autouse fixture ever runs its own setup for any test in this
    module -- pytest sets up broader-scoped fixtures first. This is the
    faithful stand-in for "inherited from the process that spawned this
    pytest worker," which a `monkeypatch.setenv` call from inside a test
    body cannot reproduce (see module docstring). Left unrestored on
    purpose -- like `apply_agent_env`'s real production behavior -- the
    surrounding session's OWN fixtures are responsible for containing it
    for every OTHER module; this module's own tests below prove exactly
    that containment for themselves."""
    # frob:waive SEC110 reason="deliberate ambient-env simulation, not a secret \
    # read/write -- FROB_WORKTREE is a worktree-lease path marker, never a secret; the \
    # whole point of this fixture (see docstring above) is standing in for a value the \
    # spawning process ambiently inherits"
    os.environ["FROB_WORKTREE"] = _AMBIENT_SENTINEL


# frob:ticket T-3145
def _git_init(root: Path) -> None:
    """A `main` checkout the guarded mutator can target -- no ticket
    ledger needed, `enforce_worktree_lease` only cares about the git
    root, not ledger state."""
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=str(root), check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=str(root),
        check=True,
    )
    subprocess.run(["git", "config", "user.name", "Test"], cwd=str(root), check=True)


# frob:ticket T-3145
class TestAmbientFrobWorktreeDoesNotLeakIntoTests:
    """T-3145's own acceptance pair, both running under this module's
    ambient `FROB_WORKTREE` (set once, module-scoped, above)."""

    def test_new_ticket_against_unrelated_repo_is_unaffected_by_an_ambient_frob_worktree(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_worktree_lease_env_ambient.py::TestAmbientFrobWorktreeDoesNotLeakIntoTests.test_new_ticket_against_unrelated_repo_is_unaffected_by_an_ambient_frob_worktree  # noqa: E501
        # Must-fire fixture: the module-level ambient FROB_WORKTREE
        # (pointed at a sentinel that is never this test's own tmp_path)
        # must not refuse a mutation against THIS test's own unrelated
        # tmp_path repo -- the exact TICK006-fixture-family failure mode
        # T-3145 measured. (Deliberately does NOT assert FROB_WORKTREE ==
        # _AMBIENT_SENTINEL here: the whole point of the fix under test
        # is that tests/conftest.py's per-test isolation fixture pops it
        # again before this test body ever runs.)
        from frob.tickets import Origin, TicketKind, TicketSpec, new_ticket

        repo = tmp_path / "fake-repo"
        _git_init(repo)
        spec = TicketSpec(
            title="ambient env leak repro",
            kind=TicketKind.BUG,
            origin=Origin.AGENT,
        )
        result = new_ticket(repo, spec)
        assert result.is_ok, result

    def test_opt_in_worktree_lease_guard_still_fires_when_deliberately_set(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_worktree_lease_env_ambient.py::TestAmbientFrobWorktreeDoesNotLeakIntoTests.test_opt_in_worktree_lease_guard_still_fires_when_deliberately_set  # noqa: E501
        # The opt-in half of the acceptance criteria: a test that
        # DELIBERATELY exercises enforce_worktree_lease (matching
        # tests/test_gates.py's own
        # test_write_coverage_lock_refuses_under_lease_violation idiom)
        # must still see the guard fire against a path it explicitly
        # names itself -- the fix must not disable the guard, only stop
        # it leaking AMBIENTLY into tests that never opted in.
        from frob.tickets import Origin, TicketKind, TicketSpec, new_ticket
        from frob.tickets._models import TicketError

        repo = tmp_path / "fake-repo"
        _git_init(repo)
        elsewhere = tmp_path / "somewhere-else"
        monkeypatch.setenv("FROB_WORKTREE", str(elsewhere))
        spec = TicketSpec(
            title="deliberate guard exercise",
            kind=TicketKind.BUG,
            origin=Origin.AGENT,
        )
        result = new_ticket(repo, spec)
        assert result.is_err
        assert result.danger_err == TicketError.WorktreeLeaseViolation
