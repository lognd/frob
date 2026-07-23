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

import os
import subprocess
from pathlib import Path

import pytest

from frob.tickets._leases import (
    LeaseError,
    LeaseRecord,
    leases_dir,
    read_all_leases,
    resolve_lease,
)


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


class TestTicketLeasePin:
    """`frob.gates.ticket_lease_pin` (T-0787) -- promotes T-0766's
    `resolve_lease` primitive into a form `frob check`'s `--ticket`
    resolution can consult. Same fail-loud/pin-or-refuse contract as
    `resolve_lease` itself, plus the two "mechanism never engaged" passthrough
    cases `resolve_lease` alone does not decide (it always requires a
    specific lease file to already resolve one way or the other)."""

    def test_no_lease_mechanism_engaged_passes_through(self, repo: Path) -> None:
        """No ticket anywhere in this repo has ever been `frob ticket
        start`ed -- the leases directory does not exist yet. Must pass
        through `Ok` unchanged (plain-repo/non-agent path, T-0787's own
        acceptance criterion)."""
        from frob.gates import ticket_lease_pin

        result = ticket_lease_pin(repo, "T-0787")
        assert result.is_ok

    def test_pinned_lease_for_this_worktree_passes(self, repo: Path) -> None:
        """A lease recorded for exactly this worktree resolves `Ok`."""
        from frob.gates import ticket_lease_pin

        _write_lease(repo, "T-0787", repo)
        result = ticket_lease_pin(repo, "T-0787")
        assert result.is_ok

    def test_lease_absent_for_this_worktree_refuses(self, repo: Path) -> None:
        """The lease mechanism IS engaged in this repo (a different
        ticket's lease exists, so the leases directory is present) but
        T-0787 itself was never started -- must refuse loudly
        (`NoLeaseForTicket`), not silently pass through."""
        from frob.gates import ticket_lease_pin

        _write_lease(repo, "T-0733", repo)
        result = ticket_lease_pin(repo, "T-0787")
        assert result.is_err
        assert result.danger_err == LeaseError.NoLeaseForTicket

    def test_lease_recorded_elsewhere_refuses(self, repo: Path) -> None:
        """T-0787 has a recorded lease, but for a different worktree --
        must refuse loudly (`LeaseWorktreeMismatch`), never silently borrow
        the sibling worktree's lease (the T-0695 incident shape)."""
        from frob.gates import ticket_lease_pin

        other_worktree = repo / ".." / "some-other-agent-worktree"
        _write_lease(repo, "T-0787", other_worktree)
        result = ticket_lease_pin(repo, "T-0787")
        assert result.is_err
        assert result.danger_err == LeaseError.LeaseWorktreeMismatch


class TestCheckTicketLeaseCli:
    """`frob.app.check_runner._refuse_ticket_lease_mismatch` (T-0787) --
    drives `frob check`'s actual `--ticket` resolution entry point (the
    same function `run()` calls before any stage/`run_gates` invocation)
    across two fake worktree paths, reproducing the T-0695 cross-worktree
    shape end to end at the CLI boundary rather than just the gates-level
    primitive above."""

    def test_pins_to_own_worktree_lease(self, repo: Path) -> None:
        """A ticket leased to THIS worktree does not trigger a refusal --
        the no-mismatch, most-common agent-dispatch path keeps working."""
        from frob.app.check_runner import _refuse_ticket_lease_mismatch
        from frob.app.config import AppConfig

        _write_lease(repo, "T-0787", repo)
        cfg = AppConfig(check_ticket="T-0787")
        assert _refuse_ticket_lease_mismatch(repo, cfg) is False

    def test_refuses_when_lease_recorded_for_another_worktree(self, repo: Path) -> None:
        """Reproduces T-0695 end to end: two fake worktree paths, a lease
        recorded for the SIBLING worktree, and this worktree's own `frob
        check --ticket T-0787` call must refuse loudly rather than run
        gates against the wrong worktree's ticket."""
        from frob.app.check_runner import _refuse_ticket_lease_mismatch
        from frob.app.config import AppConfig

        this_worktree = repo
        sibling_worktree = repo / ".." / "agent-sibling-fake-worktree"
        _write_lease(repo, "T-0787", sibling_worktree)
        cfg = AppConfig(check_ticket="T-0787")
        assert _refuse_ticket_lease_mismatch(this_worktree, cfg) is True

    def test_no_ticket_resolved_skips_the_check_entirely(self, repo: Path) -> None:
        """No `--ticket` and no ticket-prefixed branch (`repo`'s fixture
        branch is `main`) -- `active_ticket` resolves `Nothing`, so the
        lease-pin check never fires at all, matching pre-T-0787 behavior
        for a ticket-less invocation."""
        from frob.app.check_runner import _refuse_ticket_lease_mismatch
        from frob.app.config import AppConfig

        cfg = AppConfig(check_ticket=None)
        assert _refuse_ticket_lease_mismatch(repo, cfg) is False


class TestReadAllLeasesSiblingProcessVisibility:
    """T-0773 round 2 (reviewer-caught daemon-blindness bug): `frob.serve`'s
    `poll_rebase_bot` calls `read_all_leases` in a loop for the daemon's
    ENTIRE process lifetime -- a lease written or removed by a SIBLING
    process (a different worktree's CLI invocation) is never THIS
    process's own `record_lease`/`release_lease` call, so there is no
    local write event for a "cache until my own write" design to
    invalidate on. `read_all_leases`'s per-file stat comparison must see
    a sibling's write/removal on the VERY NEXT call regardless -- these
    tests write/delete lease files directly via file IO (bypassing
    `record_lease`/`release_lease` entirely) to simulate exactly that."""

    def test_new_lease_file_written_by_a_sibling_process_is_seen_next_call(
        self, repo: Path
    ) -> None:
        """Populate the cache with one lease, then simulate a SIBLING
        process writing a second lease directly (no `record_lease` call
        in this process) -- the very next `read_all_leases` call must
        see it, not just a fresh-process/`_clear_lease_caches` call."""
        _write_lease(repo, "T-0001", repo)
        first = read_all_leases(repo)
        assert {lease.ticket_id for lease in first} == {"T-0001"}

        # Simulate a sibling process recording a second ticket's lease --
        # this process never called `record_lease` for it.
        _write_lease(repo, "T-0002", repo)
        second = read_all_leases(repo)
        assert {lease.ticket_id for lease in second} == {"T-0001", "T-0002"}

    def test_lease_file_removed_by_a_sibling_process_is_seen_next_call(
        self, repo: Path
    ) -> None:
        """The reverse: a lease file removed by a SIBLING process (no
        `release_lease` call in this process) must disappear from the
        very next `read_all_leases` call."""
        _write_lease(repo, "T-0001", repo)
        _write_lease(repo, "T-0002", repo)
        first = read_all_leases(repo)
        assert {lease.ticket_id for lease in first} == {"T-0001", "T-0002"}

        # Simulate a sibling process's `release_lease` (direct unlink, no
        # call into this process's `release_lease`).
        resolved = leases_dir(repo)
        assert resolved.is_ok
        (resolved.danger_ok / "T-0002.json").unlink()

        second = read_all_leases(repo)
        assert {lease.ticket_id for lease in second} == {"T-0001"}

    def test_unchanged_lease_file_content_is_reused_from_cache(
        self, repo: Path
    ) -> None:
        """A lease file whose stat (mtime/size) is unchanged between two
        `read_all_leases` calls must not be re-parsed from disk -- proven
        indirectly here by corrupting the file's ON-DISK bytes WITHOUT
        touching its mtime/size (same length, same modification time),
        so a naive "always re-read" implementation would fail to parse
        it while the stat-cached implementation still returns the
        original, previously-parsed record."""
        _write_lease(repo, "T-0001", repo, scope=("src/a.py",))
        first = read_all_leases(repo)
        assert len(first) == 1
        assert first[0].scope == ("src/a.py",)

        resolved = leases_dir(repo)
        assert resolved.is_ok
        path = resolved.danger_ok / "T-0001.json"
        stat_before = path.stat()
        # Overwrite with garbage of the EXACT same byte length, then
        # restore the original mtime/size signature via utime -- this
        # simulates a stat collision (same mtime/size, different
        # content) that only a byte-for-byte re-read would ever catch;
        # the cache is intentionally NOT byte-for-byte, only stat-keyed,
        # so it must keep serving the cached parse here.
        original_bytes = path.read_bytes()
        path.write_bytes(b"x" * len(original_bytes))
        os.utime(path, ns=(stat_before.st_mtime_ns, stat_before.st_mtime_ns))

        second = read_all_leases(repo)
        assert len(second) == 1
        assert second[0].scope == ("src/a.py",)
