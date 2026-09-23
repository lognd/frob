"""tests/gates_suite/test_tick_dead_worktree.py -- TICK015 (T-5121/T-5358)
coverage: an IN_PROGRESS ticket whose recorded `worktree`/`branch`
(T-5120's ledger-durable stamp) is judged dead must be reported, and
(only when `[gates] tick015_requeue = true`, past a live land-queue entry
and a young-lease guard) requeued; a ticket with a live holder, a live
land-queue entry, or a too-young lease must be left untouched.

Real git fixture repo throughout (matching `tests/unit/tickets/
test_start_transition_ledger.py`'s own style) -- `transition(...,
IN_PROGRESS)` only stamps `worktree`/`branch` durably in the fleet-
dispatch shape (a sibling `.claude/worktrees/` agent worktree
registered), which is also exactly the shape TICK015 exists to judge.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from frob.gates import Severity, tickets_gate
from frob.tickets import (
    Origin,
    TicketKind,
    TicketSpec,
    TicketState,
    new_ticket,
    transition,
)
from frob.tickets._archive import load_queue
from frob.tickets._land_queue import enqueue
from frob.tickets._leases import _lease_path, leases_dir
from frob.tickets._store import atomic_write, ledger_path


def _run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess:
    """Run `argv` in `cwd`, raising on a nonzero exit (test-helper only)."""
    return subprocess.run(
        argv, cwd=str(cwd), check=True, capture_output=True, text=True
    )


def _git_init(root: Path, *, branch: str = "main") -> None:
    """Initialize a real git repo at `root` on `branch` with a test identity."""
    root.mkdir(parents=True, exist_ok=True)
    _run(["git", "init", "-q", "-b", branch], root)
    _run(["git", "config", "user.email", "test@example.com"], root)
    _run(["git", "config", "user.name", "Test"], root)


def _commit_all(root: Path, message: str) -> None:
    """Stage and commit every change under `root` (test-helper only)."""
    _run(["git", "add", "-A"], root)
    _run(["git", "commit", "-q", "-m", message], root)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A real git checkout with an initialized, committed ledger."""
    root = tmp_path / "repo"
    _git_init(root)
    atomic_write(ledger_path(root), "# Tickets\n\n")
    _commit_all(root, "init")
    return root


def _start_in_progress(repo: Path, worktree_name: str, title: str) -> tuple[str, Path]:
    """Register a real sibling `.claude/worktrees/<worktree_name>` agent
    worktree, then file and start a fixture ticket ENTIRELY from it --
    matching real fleet dispatch (`frob ticket work`, one agent worktree
    per ticket) and T-5120's own `repo_with_sibling_worktree` test shape:
    `record_lease`'s ledger commit (and hence the `worktree`/`branch`
    stamp) lands on the CALLING root's own branch, which for a per-
    branch `tickets.md` ledger means the sibling's branch, not `repo`'s.
    Returns `(ticket_id, sibling)`; TICK015 must be evaluated against
    `sibling`, the checkout that actually carries the IN_PROGRESS
    commit."""
    sibling = repo / ".claude" / "worktrees" / worktree_name
    sibling.parent.mkdir(parents=True, exist_ok=True)
    _run(["git", "worktree", "add", "-b", worktree_name, str(sibling)], repo)

    created = new_ticket(
        sibling, TicketSpec(title=title, kind=TicketKind.BUG, origin=Origin.AGENT)
    )
    assert created.is_ok
    tid = created.danger_ok.id
    _commit_all(sibling, f"file {tid}")

    assert transition(sibling, tid, TicketState.PLANNED).is_ok
    result = transition(sibling, tid, TicketState.IN_PROGRESS)
    assert result.is_ok
    assert getattr(result.danger_ok, "worktree", None) == str(sibling.resolve())

    # A real coordinator only ever learns of another worktree's
    # in-progress state through a later sync (`frob ticket reconcile`,
    # a land) -- synthesize that here with a plain merge so `repo`'s OWN
    # `tickets.md` carries the IN_PROGRESS record TICK015 is evaluated
    # against, matching the fixture shape the ticket body's own positive
    # control describes ("a fixture ticket started in a worktree...").
    _run(["git", "merge", "--no-edit", worktree_name], repo)
    return tid, sibling


def _backdate_lease(repo: Path, ticket_id: str, *, hours: float) -> None:
    """Rewrite `ticket_id`'s own lease file's `recorded_at` to `hours` in
    the past (T-5358 test helper) -- direct JSON edit is deliberate here:
    `record_lease` always stamps "now", and TICK015's young-lease guard
    (`_tick015_protected_by_young_lease`) needs a controllable age, not a
    controllable clock."""
    leases_root = leases_dir(repo)
    assert leases_root.is_ok
    path = _lease_path(leases_root.danger_ok, ticket_id)
    record = json.loads(path.read_text())
    record["recorded_at"] = (datetime.now(UTC) - timedelta(hours=hours)).isoformat()
    path.write_text(json.dumps(record))


def _write_frob_toml(repo: Path, *, tick015_requeue: bool) -> None:
    """Commit a minimal `frob.toml` enabling/disabling TICK015's requeue
    side effect (T-5358) -- `_tick015_gates_table` reads `[gates]
    tick015_requeue` from exactly this file."""
    (repo / "frob.toml").write_text(
        f"[gates]\ntick015_requeue = {'true' if tick015_requeue else 'false'}\n"
    )
    _commit_all(repo, "frob.toml")


class TestTick015DeadWorktreeRequeue:
    """TICK015 (T-5121/T-5358): an IN_PROGRESS ticket's recorded worktree/
    branch judged dead (path gone, branch gone, or no live process holds
    it) is reported, and -- only past the land-queue/young-lease guards,
    and only when opted in -- requeued; a live holder, a live queue
    entry, or a too-young lease is left untouched."""

    # frob:tests \
    # tests/gates_suite/test_tick_dead_worktree.py::TestTick015DeadWorktreeRequeue.test_deleted_worktree_fires_and_requeues  # noqa: E501
    def test_deleted_worktree_fires_and_requeues(self, repo: Path) -> None:
        """Must-fire control (T-5358's positive control #3): no land-
        queue entry, a lease old enough to clear the default 6h minimum,
        and `tick015_requeue` opted in -- the worktree directory is
        deleted (and pruned from git's own worktree list) out from under
        an IN_PROGRESS ticket, and TICK015 both reports AND requeues it."""
        tid, sibling = _start_in_progress(repo, "t-dead", "Dead worktree fixture")
        _backdate_lease(repo, tid, hours=7)
        _write_frob_toml(repo, tick015_requeue=True)

        shutil.rmtree(sibling)
        _run(["git", "worktree", "prune"], repo)

        queue = load_queue(repo)
        assert queue.is_ok
        violations = tickets_gate(repo, queue.danger_ok)
        tick015 = [v for v in violations if v.rule == "TICK015"]
        assert len(tick015) == 1
        assert tick015[0].severity == Severity.ERROR
        assert tid in tick015[0].message

        reloaded = load_queue(repo)
        assert reloaded.is_ok
        assert reloaded.danger_ok.tickets[tid].state == TicketState.QUEUED

    # frob:tests \
    # tests/gates_suite/test_tick_dead_worktree.py::TestTick015DeadWorktreeRequeue.test_requeue_disabled_reports_only  # noqa: E501
    def test_requeue_disabled_reports_only(self, repo: Path) -> None:
        """T-5358's positive control #4: same shape as the must-fire
        control above (old-enough lease, no queue entry), but
        `tick015_requeue` is left at its default (`false`) -- TICK015
        must still report the ERROR (naming the manual `frob ticket fail`
        remedy) but must NOT mutate the ledger."""
        tid, sibling = _start_in_progress(repo, "t-report-only", "Report only fixture")
        _backdate_lease(repo, tid, hours=7)
        _write_frob_toml(repo, tick015_requeue=False)

        shutil.rmtree(sibling)
        _run(["git", "worktree", "prune"], repo)

        queue = load_queue(repo)
        assert queue.is_ok
        violations = tickets_gate(repo, queue.danger_ok)
        tick015 = [v for v in violations if v.rule == "TICK015"]
        assert len(tick015) == 1
        assert tick015[0].severity == Severity.ERROR
        assert tid in tick015[0].message
        assert "frob ticket fail" in tick015[0].message

        reloaded = load_queue(repo)
        assert reloaded.is_ok
        assert reloaded.danger_ok.tickets[tid].state == TicketState.IN_PROGRESS

    # frob:tests \
    # tests/gates_suite/test_tick_dead_worktree.py::TestTick015DeadWorktreeRequeue.test_live_queue_entry_is_not_requeued  # noqa: E501
    def test_live_queue_entry_is_not_requeued(self, repo: Path) -> None:
        """T-5358's positive control #1 (the T-5293/T-5267 incident
        shape): the ticket has a live `queued` entry in `.frob/land-
        queue.json` -- a normal, healthy state for a finished ticket
        waiting on the drainer -- even though its worktree is dead and
        `tick015_requeue` is enabled, TICK015 must neither report nor
        requeue it."""
        tid, sibling = _start_in_progress(repo, "t-queued", "Queued land fixture")
        _backdate_lease(repo, tid, hours=7)
        _write_frob_toml(repo, tick015_requeue=True)
        assert enqueue(repo, tid, sibling, "t-queued").is_ok

        shutil.rmtree(sibling)
        _run(["git", "worktree", "prune"], repo)

        queue = load_queue(repo)
        assert queue.is_ok
        violations = tickets_gate(repo, queue.danger_ok)
        assert not any(v.rule == "TICK015" for v in violations)

        reloaded = load_queue(repo)
        assert reloaded.is_ok
        assert reloaded.danger_ok.tickets[tid].state == TicketState.IN_PROGRESS

    # frob:tests \
    # tests/gates_suite/test_tick_dead_worktree.py::TestTick015DeadWorktreeRequeue.test_young_lease_is_not_requeued  # noqa: E501
    def test_young_lease_is_not_requeued(self, repo: Path) -> None:
        """T-5358's positive control #2: no land-queue entry, but the
        ticket's lease was recorded moments ago (well under the default
        6h minimum) -- even with `tick015_requeue` enabled, TICK015 must
        neither report nor requeue it (more likely mid-dispatch than
        abandoned)."""
        tid, sibling = _start_in_progress(repo, "t-young", "Young lease fixture")
        _write_frob_toml(repo, tick015_requeue=True)

        shutil.rmtree(sibling)
        _run(["git", "worktree", "prune"], repo)

        queue = load_queue(repo)
        assert queue.is_ok
        violations = tickets_gate(repo, queue.danger_ok)
        assert not any(v.rule == "TICK015" for v in violations)

        reloaded = load_queue(repo)
        assert reloaded.is_ok
        assert reloaded.danger_ok.tickets[tid].state == TicketState.IN_PROGRESS

    # frob:tests \
    # tests/gates_suite/test_tick_dead_worktree.py::TestTick015DeadWorktreeRequeue.test_live_holder_is_untouched  # noqa: E501
    @pytest.mark.skipif(
        sys.platform == "win32",
        reason="scan_for_live_worktree_process reads /proc/<pid>/cwd directly; Linux-only primitive",
    )
    def test_live_holder_is_untouched(self, repo: Path) -> None:
        """Negative control: the worktree is present AND a real process
        is cwd'd into it -- TICK015 must not fire or mutate the ticket."""
        tid, sibling = _start_in_progress(repo, "t-live", "Live worktree fixture")

        holder = subprocess.Popen(
            ["python3", "-c", "import time; time.sleep(30)"], cwd=str(sibling)
        )
        try:
            time.sleep(0.3)
            queue = load_queue(repo)
            assert queue.is_ok
            violations = tickets_gate(repo, queue.danger_ok)
            assert not any(v.rule == "TICK015" for v in violations)

            reloaded = load_queue(repo)
            assert reloaded.is_ok
            assert reloaded.danger_ok.tickets[tid].state == TicketState.IN_PROGRESS
        finally:
            holder.kill()
            holder.wait(timeout=5)
