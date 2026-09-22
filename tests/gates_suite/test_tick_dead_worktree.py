"""tests/gates_suite/test_tick_dead_worktree.py -- TICK015 (T-5121)
coverage: an IN_PROGRESS ticket whose recorded `worktree`/`branch`
(T-5120's ledger-durable stamp) is judged dead must be requeued and
reported; a ticket with a live holder must be left untouched.

Real git fixture repo throughout (matching `tests/unit/tickets/
test_start_transition_ledger.py`'s own style) -- `transition(...,
IN_PROGRESS)` only stamps `worktree`/`branch` durably in the fleet-
dispatch shape (a sibling `.claude/worktrees/` agent worktree
registered), which is also exactly the shape TICK015 exists to judge.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import time
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


class TestTick015DeadWorktreeRequeue:
    """TICK015 (T-5121): an IN_PROGRESS ticket's recorded worktree/branch
    judged dead (path gone, branch gone, or no live process holds it) is
    requeued and reported; a live holder is untouched."""

    # frob:tests \
    # tests/gates_suite/test_tick_dead_worktree.py::TestTick015DeadWorktreeRequeue.test_deleted_worktree_fires_and_requeues  # noqa: E501
    def test_deleted_worktree_fires_and_requeues(self, repo: Path) -> None:
        """Must-fire control: the worktree directory is deleted (and
        pruned from git's own worktree list) out from under an
        IN_PROGRESS ticket -- the measured T-5121 incident shape (38 of
        54 in-progress tickets abandoned with the ledger never told)."""
        tid, sibling = _start_in_progress(repo, "t-dead", "Dead worktree fixture")

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
