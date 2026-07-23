"""T-0766: `resolve_lease`'s pinned per-ticket resolution -- the fix for the
T-0695 incident (`frob check --ticket T-0695` twice ran against a
completely different worktree via stale lease state, until `frob ticket
start T-0695` was re-run).

`resolve_lease` reads exactly ONE ticket's own lease file, by its known
per-ticket path -- never by scanning/ordering across every recorded lease
the way a hand-rolled caller on top of `read_all_leases` would have to.
These tests reproduce the cross-talk shape directly: two tickets, two fake
worktree paths, and prove resolution for one ticket id never returns the
other's record, in either lease-file write order.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from frob.tickets._leases import LeaseError, LeaseRecord, leases_dir, resolve_lease


def _run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        argv, cwd=str(cwd), check=True, capture_output=True, text=True
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A minimal real git repo (resolve_lease's `leases_dir` shells out to
    `git rev-parse --git-common-dir`, so a real `.git` is required -- a
    single-checkout repo is enough to test the per-ticket file-resolution
    logic itself; T-0473's actual cross-worktree VISIBILITY is already
    covered by tests/test_ticket_leases_cross_worktree.py)."""
    root = tmp_path / "repo"
    root.mkdir()
    _run(["git", "init", "-q", "-b", "main"], root)
    _run(["git", "config", "user.email", "test@example.com"], root)
    _run(["git", "config", "user.name", "Test"], root)
    (root / "README.md").write_text("x\n", encoding="utf-8")
    _run(["git", "add", "-A"], root)
    _run(["git", "commit", "-q", "-m", "init"], root)
    return root


def _write_lease(
    root: Path, ticket_id: str, worktree: Path, *, scope: tuple[str, ...] = ()
) -> None:
    """Write `ticket_id`'s lease file directly, recording `worktree` as its
    holder -- bypasses `record_lease`'s own `root.resolve()` capture so
    tests can simulate a lease held by a DIFFERENT (possibly nonexistent,
    fake) worktree path than `root` itself."""
    resolved = leases_dir(root)
    assert resolved.is_ok
    leases_root = resolved.danger_ok
    leases_root.mkdir(parents=True, exist_ok=True)
    record = LeaseRecord(
        ticket_id=ticket_id,
        scope=scope,
        worktree=str(worktree),
        branch="main",
        recorded_at="2026-07-22T00:00:00+00:00",
    )
    (leases_root / f"{ticket_id}.json").write_text(
        record.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )


class TestResolveLease:
    """`resolve_lease` pins ticket id -> its own worktree, never a sibling's."""

    def test_resolves_own_ticket_own_worktree(self, repo: Path) -> None:
        """A ticket with a lease recorded for `invoking_worktree` resolves Ok."""
        worktree = repo
        _write_lease(repo, "T-0695", worktree)
        result = resolve_lease(repo, "T-0695", worktree)
        assert result.is_ok
        assert result.danger_ok.ticket_id == "T-0695"

    def test_never_returns_a_sibling_tickets_lease(self, repo: Path) -> None:
        """Reproduces the T-0695 cross-talk shape: two tickets, two fake
        worktree paths, both leases recorded (in either write order) --
        resolving T-0695 must NEVER come back with T-0733's record, and
        vice versa, regardless of which file was written/touched most
        recently."""
        worktree_a = repo / ".." / "agent-a1367e9da4d0a8946-fake"
        worktree_b = repo / ".." / "agent-a86ce74bd40394899-fake"

        # T-0733 written FIRST, T-0695 written SECOND (a later mtime/newer
        # file must not make T-0695's resolution "prefer" it).
        _write_lease(repo, "T-0733", worktree_b)
        _write_lease(repo, "T-0695", worktree_a)

        resolved_695 = resolve_lease(repo, "T-0695", worktree_a)
        assert resolved_695.is_ok
        assert resolved_695.danger_ok.ticket_id == "T-0695"
        assert Path(resolved_695.danger_ok.worktree).resolve() == worktree_a.resolve()

        resolved_733 = resolve_lease(repo, "T-0733", worktree_b)
        assert resolved_733.is_ok
        assert resolved_733.danger_ok.ticket_id == "T-0733"
        assert Path(resolved_733.danger_ok.worktree).resolve() == worktree_b.resolve()

        # T-0695's own worktree (a) is never a valid resolution for T-0733,
        # and T-0733's worktree (b) is never a valid resolution for T-0695
        # -- each must fail loudly (mismatch), never silently borrow.
        cross_a = resolve_lease(repo, "T-0733", worktree_a)
        assert cross_a.is_err
        assert cross_a.danger_err == LeaseError.LeaseWorktreeMismatch

        cross_b = resolve_lease(repo, "T-0695", worktree_b)
        assert cross_b.is_err
        assert cross_b.danger_err == LeaseError.LeaseWorktreeMismatch

    def test_no_lease_for_ticket_fails_loudly(self, repo: Path) -> None:
        """A ticket id with no recorded lease file at all fails loudly
        (`NoLeaseForTicket`) instead of falling back to any other ticket's
        lease -- the "never borrow" contract for the absent case."""
        _write_lease(repo, "T-0733", repo)
        result = resolve_lease(repo, "T-0695", repo)
        assert result.is_err
        assert result.danger_err == LeaseError.NoLeaseForTicket

    def test_lease_recorded_for_a_different_worktree_fails_loudly(
        self, repo: Path
    ) -> None:
        """A ticket's OWN lease exists, but for a worktree other than the
        one invoking resolution -- must fail loudly (`LeaseWorktreeMismatch`),
        never silently substitute the recorded worktree for the invoking one."""
        other_worktree = repo / ".." / "some-other-agent-worktree"
        _write_lease(repo, "T-0695", other_worktree)
        result = resolve_lease(repo, "T-0695", repo)
        assert result.is_err
        assert result.danger_err == LeaseError.LeaseWorktreeMismatch
