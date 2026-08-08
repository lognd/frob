"""T-0835: `frob ticket start` must refuse a double-dispatch, not silently
succeed. Two refusals, both checked independently of this worktree's own
local ledger view (the whole bug: a worktree whose local `tickets.md` has
not yet merged a sibling's transition can otherwise sail straight past a
purely ledger-based check):

1. The ticket is already in a TERMINAL state (done/dropped) -- no override.
2. The ticket holds a LIVE cross-worktree lease pinned to a DIFFERENT
   worktree -- overridable with `--steal`, which must invalidate the old
   lease (re-pin it to the stealer) so the loser cannot later resolve/close
   against it.

An EXPIRED lease in another worktree must NOT block (the existing T-0782
dead-agent recovery path), and a lease already pinned to THIS worktree must
stay idempotent (restart after an interrupted session).

Real git fixture repos and real lease files throughout -- no mocking of the
lease layer itself, matching `tests/test_ticket_leases_cross_worktree.py`'s
own style for exercising the shared-common-dir side channel."""

from __future__ import annotations

import os
import subprocess
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
from typani import Ok

from frob.app.config import AppConfig
from frob.app.ticket_runner import run as ticket_run
from frob.tickets import (
    TicketState,
    finalize_draft_for_land,
    load_all,
    new_ticket,
    renumber_one,
    transition,
)
from frob.tickets._leases import (
    LEASE_TTL_SECONDS,
    _lease_path,
    _LeaseRecord,
    _list_agent_worktrees,
    lease_age_seconds,
    leases_dir,
    read_all_leases,
    record_lease,
    release_lease,
    rename_lease,
    resolve_lease,
    sweep_worktrees,
    warn_if_worktree_stale,
)
from frob.tickets._models import Origin, TicketKind, TicketSpec


def _run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        argv, cwd=str(cwd), check=True, capture_output=True, text=True
    )


def _git_init(root: Path, *, branch: str = "main") -> None:
    root.mkdir(parents=True, exist_ok=True)
    _run(["git", "init", "-q", "-b", branch], root)
    _run(["git", "config", "user.email", "test@example.com"], root)
    _run(["git", "config", "user.name", "Test"], root)


def _commit_all(root: Path, message: str) -> None:
    _run(["git", "add", "-A"], root)
    _run(["git", "commit", "-q", "-m", message], root)


#: Where this file's fixtures actually keep ledger content. Every `repo`
#: here is a FRESH repo, and T-1553 made fresh repos default to ledger v2
#: (`tickets/T-####/ticket.md`), so a `tickets.md` pathspec now reports
#: clean no matter how dirty the ledger really is -- the exact blind spot
#: that let the v2 auto-commit regression ship green.
_LEDGER_PATHSPEC = "tickets"


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A main checkout with a real git history and an initialized ledger."""
    main_repo = tmp_path / "main"
    _git_init(main_repo)
    (main_repo / "src").mkdir()
    (main_repo / "src" / "feature.py").write_text("# feature\n")
    ticket_run(
        AppConfig(
            ticket_command="new",
            ticket_path=main_repo,
            ticket_title="feature ticket",
            ticket_kind="docs",
            ticket_scope=["src/feature.py"],
            ticket_body="## Done report\n\nDone.\n",
        )
    )
    _commit_all(main_repo, "init: ticket + ledger committed")
    return main_repo


@pytest.fixture
def second_worktree(repo: Path) -> Path:
    """A second linked `git worktree` of `repo`, branched from the SAME
    commit `repo` is on -- both worktrees' local `tickets.md` therefore
    agree on the ticket's state at fixture time (T-0001, QUEUED), matching
    the real double-dispatch shape: only the shared lease side-channel (not
    either worktree's own ledger) can tell the two apart afterward."""
    wt = repo.parent / "wt"
    _run(["git", "worktree", "add", "-b", "feature-wt", str(wt)], repo)
    return wt


def _proc_test_cwd_matches(pid: int, expected: Path) -> bool:
    """`True` iff `/proc/<pid>/cwd` resolves to `expected` (test-only
    startup-race helper for the T-1619 belt-and-braces scan test)."""
    try:
        return Path(os.readlink(f"/proc/{pid}/cwd")).resolve() == expected.resolve()
    except OSError:
        return False


def _write_lease(
    root: Path, ticket_id: str, worktree: Path, *, recorded_at: str
) -> None:
    resolved = leases_dir(root)
    assert resolved.is_ok
    leases_root = resolved.danger_ok
    leases_root.mkdir(parents=True, exist_ok=True)
    record = _LeaseRecord(
        ticket_id=ticket_id,
        scope=("src/feature.py",),
        worktree=str(worktree),
        branch="main",
        recorded_at=recorded_at,
    )
    (leases_root / f"{ticket_id}.json").write_text(
        record.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )


class TestRefusesTerminalState:
    """Behavior 1: `start` refuses a done/dropped ticket outright."""

    def test_refuses_done_ticket(self, repo: Path, caplog) -> None:
        # frob:tests \
        # tests/test_ticket_leases.py::TestRefusesTerminalState.test_refuses_done_ticket
        ticket_run(
            AppConfig(ticket_command="start", ticket_path=repo, ticket_id="T-0001")
        )
        ticket_run(
            AppConfig(
                ticket_command="close",
                ticket_path=repo,
                ticket_id="T-0001",
                ticket_evidence_cmd="true",
            )
        )
        _commit_all(repo, "land T-0001 feature ticket")

        cfg = AppConfig(ticket_command="start", ticket_path=repo, ticket_id="T-0001")
        with caplog.at_level("ERROR"), pytest.raises(SystemExit):
            ticket_run(cfg)
        assert "already done" in caplog.text
        assert "landed at" in caplog.text

    def test_refuses_dropped_ticket(self, repo: Path, caplog) -> None:
        # frob:tests tests/test_ticket_leases.py::TestRefusesTerminalState.test_refuses_dropped_ticket  # noqa: E501
        dropped = transition(repo, "T-0001", TicketState.DROPPED)
        assert dropped.is_ok

        cfg = AppConfig(ticket_command="start", ticket_path=repo, ticket_id="T-0001")
        with caplog.at_level("ERROR"), pytest.raises(SystemExit):
            ticket_run(cfg)
        assert "already dropped" in caplog.text


class TestRefusesForeignLiveLease:
    """Behavior 2 + 4: a live lease pinned to a DIFFERENT worktree refuses;
    an EXPIRED one does not block."""

    def test_refuses_live_lease_in_another_worktree(
        self, repo: Path, second_worktree: Path, caplog
    ) -> None:
        # frob:tests tests/test_ticket_leases.py::TestRefusesForeignLiveLease.test_refuses_live_lease_in_another_worktree  # noqa: E501
        ticket_run(
            AppConfig(ticket_command="start", ticket_path=repo, ticket_id="T-0001")
        )
        assert any(
            lease.ticket_id == "T-0001" for lease in read_all_leases(second_worktree)
        )

        cfg = AppConfig(
            ticket_command="start", ticket_path=second_worktree, ticket_id="T-0001"
        )
        with caplog.at_level("ERROR"), pytest.raises(SystemExit):
            ticket_run(cfg)
        assert "has a live lease held by worktree" in caplog.text
        assert str(repo.resolve()) in caplog.text
        assert "--steal" in caplog.text

        # Refusal must not have mutated the second worktree's own ledger.
        loaded = load_all(second_worktree)
        assert loaded.is_ok
        assert loaded.danger_ok["T-0001"].state == TicketState.QUEUED

    def test_expired_lease_in_another_worktree_does_not_block(
        self, repo: Path, second_worktree: Path
    ) -> None:
        # frob:tests tests/test_ticket_leases.py::TestRefusesForeignLiveLease.test_expired_lease_in_another_worktree_does_not_block  # noqa: E501
        stale_time = (
            datetime.now(UTC) - timedelta(seconds=LEASE_TTL_SECONDS + 3600)
        ).isoformat()
        _write_lease(second_worktree, "T-0001", repo, recorded_at=stale_time)

        cfg = AppConfig(
            ticket_command="start", ticket_path=second_worktree, ticket_id="T-0001"
        )
        ticket_run(cfg)  # must not raise

        loaded = load_all(second_worktree)
        assert loaded.is_ok
        assert loaded.danger_ok["T-0001"].state == TicketState.IN_PROGRESS

    def test_same_worktree_restart_stays_idempotent(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_leases.py::TestRefusesForeignLiveLease.test_same_worktree_restart_stays_idempotent  # noqa: E501
        ticket_run(
            AppConfig(ticket_command="start", ticket_path=repo, ticket_id="T-0001")
        )
        # Requeue to simulate an interrupted session leaving a stale lease
        # behind that a subsequent `start` in the SAME worktree must not
        # treat as foreign.
        requeued = transition(repo, "T-0001", TicketState.QUEUED)
        assert requeued.is_ok
        _write_lease(repo, "T-0001", repo, recorded_at=datetime.now(UTC).isoformat())

        cfg = AppConfig(ticket_command="start", ticket_path=repo, ticket_id="T-0001")
        ticket_run(cfg)  # must not raise -- same worktree, idempotent

        loaded = load_all(repo)
        assert loaded.is_ok
        assert loaded.danger_ok["T-0001"].state == TicketState.IN_PROGRESS


class TestStealOverride:
    """Behavior 2's override: `--steal` proceeds and invalidates the loser's
    lease via the existing `record_lease`/`resolve_lease` machinery -- no
    parallel mechanism."""

    def test_steal_succeeds_and_invalidates_the_other_worktrees_lease(
        self, repo: Path, second_worktree: Path, caplog
    ) -> None:
        # frob:tests tests/test_ticket_leases.py::TestStealOverride.test_steal_succeeds_and_invalidates_the_other_worktrees_lease  # noqa: E501
        ticket_run(
            AppConfig(ticket_command="start", ticket_path=repo, ticket_id="T-0001")
        )
        # Before the steal, `repo`'s own lease resolves fine.
        assert resolve_lease(repo, "T-0001", repo).is_ok

        cfg = AppConfig(
            ticket_command="start",
            ticket_path=second_worktree,
            ticket_id="T-0001",
            ticket_steal=True,
        )
        with caplog.at_level("WARNING"):
            ticket_run(cfg)
        assert "stealing live lease" in caplog.text

        loaded = load_all(second_worktree)
        assert loaded.is_ok
        assert loaded.danger_ok["T-0001"].state == TicketState.IN_PROGRESS

        leases = read_all_leases(repo)
        held = next(lease for lease in leases if lease.ticket_id == "T-0001")
        assert Path(held.worktree).resolve() == second_worktree.resolve()

        # `repo`'s own lease no longer resolves -- reusing the existing
        # `resolve_lease` pin check, the same primitive `frob check
        # --ticket`'s `ticket_lease_pin` gate uses ahead of `close`/`land`.
        stale = resolve_lease(repo, "T-0001", repo)
        assert stale.is_err


class TestDoubleDispatchIncidentRegression:
    """Reconstructs the exact T-0835 incident shape: worktree A leases and
    works a ticket; worktree B's `start` is refused; B `--steal`s; A's
    subsequent lease resolution (the check `close`/`land` depend on) fails
    against its own now-invalidated lease."""

    def test_incident_shape_end_to_end(
        self, repo: Path, second_worktree: Path, caplog
    ) -> None:
        # frob:tests tests/test_ticket_leases.py::TestDoubleDispatchIncidentRegression.test_incident_shape_end_to_end  # noqa: E501
        # A: dispatched first, starts and begins working.
        ticket_run(
            AppConfig(ticket_command="start", ticket_path=repo, ticket_id="T-0001")
        )
        assert resolve_lease(repo, "T-0001", repo).is_ok

        # B: dispatched second (presumed-dead A), plain start is refused.
        plain_cfg = AppConfig(
            ticket_command="start", ticket_path=second_worktree, ticket_id="T-0001"
        )
        with caplog.at_level("ERROR"), pytest.raises(SystemExit):
            ticket_run(plain_cfg)
        assert "has a live lease held by worktree" in caplog.text

        # B: explicit --steal succeeds.
        steal_cfg = AppConfig(
            ticket_command="start",
            ticket_path=second_worktree,
            ticket_id="T-0001",
            ticket_steal=True,
        )
        ticket_run(steal_cfg)
        loaded_b = load_all(second_worktree)
        assert loaded_b.is_ok
        assert loaded_b.danger_ok["T-0001"].state == TicketState.IN_PROGRESS

        # A: its lease is now invalidated -- the resolution the `close`/
        # `land` path relies on (`ticket_lease_pin` -> `resolve_lease`)
        # fails for A, exactly the property that stops the 5.5h duplicate-
        # work incident from repeating.
        assert resolve_lease(repo, "T-0001", repo).is_err


# T-0836: `frob worktree sweep` -- lease-aware stale-worktree cleanup. A raw
# git-level bulk sweep (`git worktree remove` in a loop, skip-listed only by
# a git-dirty check) destroyed a live agent's CLEAN worktree, because git's
# own dirty check cannot see a live agent between writes -- only this
# repo's own lease machinery can. These tests build real fixture repos with
# multiple `.claude/worktrees/`-shaped worktrees (this repo's own dispatch
# convention) and exercise `sweep_worktrees`/`_list_agent_worktrees`
# directly against real git state -- no mocking of the lease or git layers.


@pytest.fixture
def sweep_repo(tmp_path: Path) -> Path:
    """A main checkout with an initial commit, ready to host
    `.claude/worktrees/`-shaped linked worktrees."""
    main_repo = tmp_path / "main"
    _git_init(main_repo)
    (main_repo / "README.md").write_text("root\n")
    _commit_all(main_repo, "init")
    return main_repo


def _add_agent_worktree(repo: Path, name: str) -> Path:
    """Add a linked worktree under `repo`'s own `.claude/worktrees/<name>`
    convention, on a fresh branch `agent-<name>`."""
    wt = repo / ".claude" / "worktrees" / name
    wt.parent.mkdir(parents=True, exist_ok=True)
    _run(["git", "worktree", "add", "-b", f"agent-{name}", str(wt)], repo)
    return wt


def _branch_exists(repo: Path, branch: str) -> bool:
    listing = _run(["git", "branch", "--list", branch], repo).stdout
    return branch in listing


class TestListAgentWorktrees:
    """`_list_agent_worktrees` returns only `.claude/worktrees/`-shaped
    paths, never the repo's own primary checkout."""

    def test_lists_only_dot_claude_worktrees_paths(self, sweep_repo: Path) -> None:
        # frob:tests tests/test_ticket_leases.py::TestListAgentWorktrees.test_lists_only_dot_claude_worktrees_paths  # noqa: E501
        wt = _add_agent_worktree(sweep_repo, "wt1")

        result = _list_agent_worktrees(sweep_repo)
        assert result.is_ok
        paths = result.danger_ok
        assert paths == (wt.resolve(),)
        assert sweep_repo.resolve() not in paths


class TestSweepWorktrees:
    """`sweep_worktrees`'s core removal decision: clean AND no live lease."""

    def test_clean_no_lease_removed(self, sweep_repo: Path) -> None:
        # frob:tests \
        # tests/test_ticket_leases.py::TestSweepWorktrees.test_clean_no_lease_removed
        wt = _add_agent_worktree(sweep_repo, "wt1")

        result = sweep_worktrees(sweep_repo)
        assert result.is_ok
        verdicts = result.danger_ok
        assert len(verdicts) == 1
        assert verdicts[0].verdict == "removed"
        assert not wt.exists()

    def test_clean_live_lease_kept(self, sweep_repo: Path) -> None:
        # frob:tests \
        # tests/test_ticket_leases.py::TestSweepWorktrees.test_clean_live_lease_kept
        wt = _add_agent_worktree(sweep_repo, "wt1")
        _write_lease(
            sweep_repo,
            "T-0900",
            wt,
            recorded_at=datetime.now(UTC).isoformat(),
        )

        result = sweep_worktrees(sweep_repo)
        assert result.is_ok
        verdicts = result.danger_ok
        assert len(verdicts) == 1
        assert verdicts[0].verdict == "kept:lease"
        assert "T-0900" in verdicts[0].detail
        assert wt.exists()

    def test_dirty_kept(self, sweep_repo: Path) -> None:
        # frob:tests tests/test_ticket_leases.py::TestSweepWorktrees.test_dirty_kept
        wt = _add_agent_worktree(sweep_repo, "wt1")
        (wt / "scratch.txt").write_text("uncommitted\n")

        result = sweep_worktrees(sweep_repo)
        assert result.is_ok
        verdicts = result.danger_ok
        assert len(verdicts) == 1
        assert verdicts[0].verdict == "kept:dirty"
        assert wt.exists()

    def test_expired_lease_clean_removed(self, sweep_repo: Path) -> None:
        # frob:tests tests/test_ticket_leases.py::TestSweepWorktrees.test_expired_lease_clean_removed  # noqa: E501
        wt = _add_agent_worktree(sweep_repo, "wt1")
        stale_time = (
            datetime.now(UTC) - timedelta(seconds=LEASE_TTL_SECONDS + 3600)
        ).isoformat()
        _write_lease(sweep_repo, "T-0900", wt, recorded_at=stale_time)

        result = sweep_worktrees(sweep_repo)
        assert result.is_ok
        verdicts = result.danger_ok
        assert len(verdicts) == 1
        assert verdicts[0].verdict == "removed"
        assert not wt.exists()

    def test_dry_run_removes_nothing(self, sweep_repo: Path) -> None:
        # frob:tests \
        # tests/test_ticket_leases.py::TestSweepWorktrees.test_dry_run_removes_nothing
        wt = _add_agent_worktree(sweep_repo, "wt1")

        result = sweep_worktrees(sweep_repo, dry_run=True)
        assert result.is_ok
        verdicts = result.danger_ok
        assert len(verdicts) == 1
        assert verdicts[0].verdict == "removed"
        assert wt.exists()

        # A real removal afterward still succeeds -- dry-run genuinely
        # never touched the worktree.
        result2 = sweep_worktrees(sweep_repo)
        assert result2.is_ok
        assert not wt.exists()

    def test_branches_survive_removal(self, sweep_repo: Path) -> None:
        # frob:tests \
        # tests/test_ticket_leases.py::TestSweepWorktrees.test_branches_survive_removal
        _add_agent_worktree(sweep_repo, "wt1")
        assert _branch_exists(sweep_repo, "agent-wt1")

        result = sweep_worktrees(sweep_repo)
        assert result.is_ok
        assert result.danger_ok[0].verdict == "removed"
        assert _branch_exists(sweep_repo, "agent-wt1")

    def test_min_age_keeps_recent_worktree(self, sweep_repo: Path) -> None:
        # frob:tests tests/test_ticket_leases.py::TestSweepWorktrees.test_min_age_keeps_recent_worktree  # noqa: E501
        wt = _add_agent_worktree(sweep_repo, "wt1")

        result = sweep_worktrees(sweep_repo, min_age_hours=24)
        assert result.is_ok
        verdicts = result.danger_ok
        assert len(verdicts) == 1
        assert verdicts[0].verdict == "kept:age"
        assert wt.exists()


# frob:ticket T-1433
class TestWorktreeSweepCli:
    """`frob worktree sweep`'s CLI entry point (`frob.app.worktree_runner.
    run`) prints one verdict line per worktree plus a summary count."""

    def test_sweep_cli_prints_verdicts_and_summary(
        self, sweep_repo: Path, capsys
    ) -> None:
        # frob:tests tests/test_ticket_leases.py::TestWorktreeSweepCli.test_sweep_cli_prints_verdicts_and_summary  # noqa: E501
        from frob.app.worktree_runner import run as worktree_run

        _add_agent_worktree(sweep_repo, "wt1")

        worktree_run(["sweep", str(sweep_repo), "--dry-run"])
        out = capsys.readouterr().out
        assert "removed" in out
        assert "swept 1 worktree(s)" in out

    def test_sweep_cli_exits_1_on_sweep_error(self, sweep_repo: Path, capsys) -> None:
        # frob:tests tests/test_ticket_leases.py::TestWorktreeSweepCli.test_sweep_cli_exits_1_on_sweep_error  # noqa: E501
        # T-1400: `_run_sweep`'s `result.is_err` branch (worktree_runner.py
        # 69-70) -- `sweep_worktrees` failing (not a repo) must exit 1 with
        # a logged error, not raise or print verdict lines.
        from typani import Err

        from frob.app.worktree_runner import run as worktree_run
        from frob.tickets._leases import _WorktreeSweepError

        with patch(
            "frob.app.worktree_runner.sweep_worktrees",
            return_value=Err(_WorktreeSweepError.NotARepo),
        ):
            with pytest.raises(SystemExit) as exc_info:
                worktree_run(["sweep", str(sweep_repo)])
        assert exc_info.value.code == 1
        out = capsys.readouterr().out
        assert out == ""

    def test_sweep_cli_prints_kept_lease_and_detail_verdicts(
        self, sweep_repo: Path, capsys
    ) -> None:
        # frob:tests tests/test_ticket_leases.py::TestWorktreeSweepCli.test_sweep_cli_prints_kept_lease_and_detail_verdicts  # noqa: E501
        # T-1400: `_run_sweep`'s per-verdict rendering branches
        # (worktree_runner.py 77, 81) -- the dedicated "kept:lease"
        # formatting and the generic `elif verdict.detail:` formatting,
        # distinct from the bare-verdict `else` line already covered by
        # test_sweep_cli_prints_verdicts_and_summary.
        from frob.app.worktree_runner import run as worktree_run
        from frob.tickets._leases import _WorktreeVerdict

        fake_verdicts = [
            _WorktreeVerdict(
                path=str(sweep_repo / "wt-leased"),
                verdict="kept:lease",
                detail="T-0001",
            ),
            _WorktreeVerdict(
                path=str(sweep_repo / "wt-dirty"),
                verdict="kept:dirty",
                detail="uncommitted changes",
            ),
        ]
        with patch(
            "frob.app.worktree_runner.sweep_worktrees",
            return_value=Ok(fake_verdicts),
        ):
            worktree_run(["sweep", str(sweep_repo), "--dry-run"])
        out = capsys.readouterr().out
        assert "kept:lease(T-0001)" in out
        assert "kept:dirty(uncommitted changes)" in out
        assert "swept 2 worktree(s)" in out

    def test_sweep_cli_unrecognized_subcommand_falls_through_to_usage_error(
        self, capsys
    ) -> None:
        # frob:tests tests/test_ticket_leases.py::TestWorktreeSweepCli.test_sweep_cli_unrecognized_subcommand_falls_through_to_usage_error  # noqa: E501
        # T-1400: `run()`'s fallthrough (worktree_runner.py 104-105) --
        # no subcommand at all (argparse's `worktree_command` stays
        # `None`) prints help to stderr and exits 1, instead of silently
        # doing nothing.
        from frob.app.worktree_runner import run as worktree_run

        with pytest.raises(SystemExit) as exc_info:
            worktree_run([])
        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert "usage" in err.lower()


# frob:ticket T-1779
class TestWorktreeRemoveCli:
    """`frob worktree remove PATH`'s CLI entry point (T-1779) -- the safe
    single-worktree alternative to raw `git worktree remove`."""

    def test_remove_cli_removes_a_clean_unleased_worktree(
        self, sweep_repo: Path, capsys
    ) -> None:
        # frob:tests tests/test_ticket_leases.py::TestWorktreeRemoveCli.test_remove_cli_removes_a_clean_unleased_worktree  # noqa: E501
        import os as _os

        from frob.app.worktree_runner import run as worktree_run

        wt = _add_agent_worktree(sweep_repo, "wt1")
        cwd = Path.cwd()
        _os.chdir(sweep_repo)
        try:
            worktree_run(["remove", str(wt)])
        finally:
            _os.chdir(cwd)
        out = capsys.readouterr().out
        assert "removed" in out
        assert not wt.exists()

    def test_remove_cli_exits_1_and_names_the_error_for_a_bad_path(
        self, sweep_repo: Path, tmp_path: Path, capsys
    ) -> None:
        # frob:tests tests/test_ticket_leases.py::TestWorktreeRemoveCli.test_remove_cli_exits_1_and_names_the_error_for_a_bad_path  # noqa: E501
        import os as _os

        from frob.app.worktree_runner import run as worktree_run

        not_a_worktree = tmp_path / "elsewhere"
        not_a_worktree.mkdir()
        cwd = Path.cwd()
        _os.chdir(sweep_repo)
        try:
            with pytest.raises(SystemExit) as exc_info:
                worktree_run(["remove", str(not_a_worktree)])
        finally:
            _os.chdir(cwd)
        assert exc_info.value.code == 1

    def test_remove_cli_exits_1_when_kept(self, sweep_repo: Path, capsys) -> None:
        # frob:tests tests/test_ticket_leases.py::TestWorktreeRemoveCli.test_remove_cli_exits_1_when_kept  # noqa: E501
        import os as _os

        from frob.app.worktree_runner import run as worktree_run

        wt = _add_agent_worktree(sweep_repo, "wt1")
        (wt / "scratch.txt").write_text("uncommitted\n")
        cwd = Path.cwd()
        _os.chdir(sweep_repo)
        try:
            with pytest.raises(SystemExit) as exc_info:
                worktree_run(["remove", str(wt)])
        finally:
            _os.chdir(cwd)
        assert exc_info.value.code == 1
        out = capsys.readouterr().out
        assert "kept:dirty" in out
        assert wt.exists()


# frob:ticket T-1054
class TestCommitStartTransition:
    """T-1054: `frob ticket start` must commit its own `queued/planned ->
    in-progress` ledger write into `root`, not leave `root` dirty for the
    next `frob ticket land` (any worktree) to trip DirtyMain on."""

    def test_commits_dirty_ledger_with_expected_message(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_leases.py::TestCommitStartTransition.test_commits_dirty_ledger_with_expected_message  # noqa: E501
        ticket_run(
            AppConfig(ticket_command="start", ticket_path=repo, ticket_id="T-0001")
        )

        status = _run(["git", "status", "--porcelain", "--", _LEDGER_PATHSPEC], repo)
        assert status.stdout.strip() == ""

        log = _run(["git", "log", "-1", "--pretty=%s"], repo)
        assert log.stdout.strip() == "chore(tickets): record T-0001 start transition"

        loaded = load_all(repo)
        assert loaded.is_ok
        assert loaded.danger_ok["T-0001"].state == TicketState.IN_PROGRESS

    def test_no_op_when_ledger_already_clean(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_leases.py::TestCommitStartTransition.test_no_op_when_ledger_already_clean  # noqa: E501
        from frob.tickets._leases import commit_start_transition

        result = commit_start_transition(repo, "T-0001")
        assert result.is_ok

        status = _run(["git", "status", "--porcelain", "--", _LEDGER_PATHSPEC], repo)
        assert status.stdout.strip() == ""

    def test_reports_exact_recovery_command_on_commit_failure(
        self, repo: Path, caplog
    ) -> None:
        # frob:tests tests/test_ticket_leases.py::TestCommitStartTransition.test_reports_exact_recovery_command_on_commit_failure  # noqa: E501
        from frob.tickets import transition
        from frob.tickets._leases import LeaseError, commit_start_transition

        planned = transition(repo, "T-0001", TicketState.PLANNED)
        assert planned.is_ok
        transitioned = transition(repo, "T-0001", TicketState.IN_PROGRESS)
        assert transitioned.is_ok
        # A stale `index.lock` makes `git add` itself fail even though
        # `tickets.md` is genuinely dirty -- the simplest reliable way to
        # force the commit step to fail without depending on whether this
        # machine has a global git identity fallback configured.
        (repo / ".git" / "index.lock").write_text("")

        with caplog.at_level("ERROR"):
            result = commit_start_transition(repo, "T-0001")
        assert result.is_err
        assert result.danger_err == LeaseError.CommitFailed
        assert "DIRTY" in caplog.text
        assert (
            f"git -C {repo} add tickets/T-0001 && git -C {repo} commit -m "
            '"chore(tickets): record T-0001 start transition" -- tickets/T-0001'
        ) in caplog.text

    def test_commits_cleanly_even_when_caller_shell_has_frob_agent_set(
        self, repo: Path, monkeypatch
    ) -> None:
        # frob:tests tests/test_ticket_leases.py::TestCommitStartTransition.test_commits_cleanly_even_when_caller_shell_has_frob_agent_set  # noqa: E501
        """T-1054 regression: a real dispatched-agent shell exports
        `FROB_AGENT=1` for the whole session (T-0574). The scaffolded T-0431
        `pre-commit` hook unconditionally refuses any commit made while
        `FROB_AGENT` is set, to catch an agent accidentally running a raw
        `git commit` by hand -- but `commit_start_transition`'s own commit
        is `start`'s legitimate internal ledger machinery, not that, and
        must not collide with the guard it is not the target of."""
        from frob.tickets import transition
        from frob.tickets._leases import commit_start_transition

        hooks_dir = repo / ".git" / "hooks"
        hooks_dir.mkdir(parents=True, exist_ok=True)
        (hooks_dir / "pre-commit").write_text(
            "#!/bin/sh\n"
            'if [ -n "$FROB_AGENT" ]; then\n'
            '    echo "frob: refusing commit -- FROB_AGENT is set" >&2\n'
            "    exit 1\n"
            "fi\n"
            "exit 0\n"
        )
        (hooks_dir / "pre-commit").chmod(0o755)

        planned = transition(repo, "T-0001", TicketState.PLANNED)
        assert planned.is_ok
        transitioned = transition(repo, "T-0001", TicketState.IN_PROGRESS)
        assert transitioned.is_ok

        monkeypatch.setenv("FROB_AGENT", "1")
        result = commit_start_transition(repo, "T-0001")
        assert result.is_ok
        # frob:waive SEC110 reason="asserting a test-set dispatch-context marker is \
        # restored after the transition commit; plain env flag, nothing sensitive"
        assert os.environ.get("FROB_AGENT") == "1"

        status = _run(["git", "status", "--porcelain", "--", _LEDGER_PATHSPEC], repo)
        assert status.stdout.strip() == ""


# frob:ticket T-1130
class TestCommitTicketLedgerChange:
    """T-1130: `commit_ticket_ledger_change` -- the generalized (arbitrary
    message, `--no-commit` opt-out) sibling of `commit_start_transition`
    that `frob ticket new`/`drop`/`fail` now use for the same auto-commit
    parity T-1054 gave `start`."""

    def test_commits_dirty_ledger_with_given_message(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_leases.py::TestCommitTicketLedgerChange.test_commits_dirty_ledger_with_given_message  # noqa: E501
        from frob.tickets import transition
        from frob.tickets._leases import commit_ticket_ledger_change

        assert transition(repo, "T-0001", TicketState.PLANNED).is_ok

        result = commit_ticket_ledger_change(
            repo, "T-0001", "chore(tickets): drop T-0001"
        )
        assert result.is_ok

        status = _run(["git", "status", "--porcelain", "--", _LEDGER_PATHSPEC], repo)
        assert status.stdout.strip() == ""

        log = _run(["git", "log", "-1", "--pretty=%s"], repo)
        assert log.stdout.strip() == "chore(tickets): drop T-0001"

    def test_no_op_when_ledger_already_clean(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_leases.py::TestCommitTicketLedgerChange.test_no_op_when_ledger_already_clean  # noqa: E501
        from frob.tickets._leases import commit_ticket_ledger_change

        result = commit_ticket_ledger_change(
            repo, "T-0001", "chore(tickets): drop T-0001"
        )
        assert result.is_ok

        status = _run(["git", "status", "--porcelain", "--", _LEDGER_PATHSPEC], repo)
        assert status.stdout.strip() == ""

    def test_no_commit_flag_skips_entirely_even_when_dirty(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_leases.py::TestCommitTicketLedgerChange.test_no_commit_flag_skips_entirely_even_when_dirty  # noqa: E501
        from frob.tickets import transition
        from frob.tickets._leases import commit_ticket_ledger_change

        assert transition(repo, "T-0001", TicketState.PLANNED).is_ok

        result = commit_ticket_ledger_change(
            repo, "T-0001", "chore(tickets): drop T-0001", no_commit=True
        )
        assert result.is_ok

        # --no-commit means tickets.md is left dirty on purpose.
        status = _run(["git", "status", "--porcelain", "--", _LEDGER_PATHSPEC], repo)
        assert status.stdout.strip() != ""

    # frob:ticket T-1615
    def test_no_commit_flag_warns_when_dirty(
        self, repo: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests tests/test_ticket_leases.py::TestCommitTicketLedgerChange.test_no_commit_flag_warns_when_dirty  # noqa: E501
        """A silent `--no-commit` reproduces the 2026-08-06 DirtyMain
        incident with an extra step -- it must warn, naming the fix."""
        import logging

        from frob.tickets import transition
        from frob.tickets._leases import commit_ticket_ledger_change

        assert transition(repo, "T-0001", TicketState.PLANNED).is_ok

        with caplog.at_level(logging.WARNING, logger="frob.tickets._leases"):
            result = commit_ticket_ledger_change(
                repo, "T-0001", "chore(tickets): drop T-0001", no_commit=True
            )
        assert result.is_ok
        warnings = [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]
        assert any("DirtyMain-block" in w and "T-0001" in w for w in warnings)

    # frob:ticket T-1615
    def test_no_commit_flag_does_not_warn_when_clean(
        self, repo: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests tests/test_ticket_leases.py::TestCommitTicketLedgerChange.test_no_commit_flag_does_not_warn_when_clean  # noqa: E501
        """`--no-commit` against an already-clean ledger has nothing to
        warn about -- an unconditional warning would be noise, not
        signal, on every no-op call."""
        import logging

        from frob.tickets._leases import commit_ticket_ledger_change

        with caplog.at_level(logging.WARNING, logger="frob.tickets._leases"):
            result = commit_ticket_ledger_change(
                repo, "T-0001", "chore(tickets): drop T-0001", no_commit=True
            )
        assert result.is_ok
        warnings = [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]
        assert not any("DirtyMain-block" in w for w in warnings)

    # frob:ticket T-1432
    def test_pre_staged_unrelated_file_never_rides_along_into_the_commit(
        self, repo: Path
    ) -> None:
        # frob:tests tests/test_ticket_leases.py::TestCommitTicketLedgerChange.test_pre_staged_unrelated_file_never_rides_along_into_the_commit  # noqa: E501
        # T-1403's c2fd45da incident, reproduced directly: something else
        # (a conflicted `git stash pop`, or any other reason) leaves an
        # UNRELATED file already staged in the index before
        # commit_ticket_ledger_change ever runs. The old bare `git commit
        # -m message` commits the WHOLE index -- this sentinel file must
        # never ride along into the ledger commit; it must stay staged,
        # untouched, afterward.
        from frob.tickets import transition
        from frob.tickets._leases import commit_ticket_ledger_change

        assert transition(repo, "T-0001", TicketState.PLANNED).is_ok

        sentinel = repo / "sentinel.py"
        sentinel.write_text("# unrelated, pre-staged content\n")
        _run(["git", "add", "sentinel.py"], repo)
        # Precondition: the sentinel really is staged before the ledger
        # commit runs.
        pre_status = _run(["git", "status", "--porcelain"], repo)
        assert "A  sentinel.py" in pre_status.stdout

        result = commit_ticket_ledger_change(
            repo, "T-0001", "chore(tickets): file T-0001"
        )
        assert result.is_ok

        # tickets.md is now committed and clean...
        ledger_status = _run(
            ["git", "status", "--porcelain", "--", _LEDGER_PATHSPEC], repo
        )
        assert ledger_status.stdout.strip() == ""

        # ...but the sentinel must STILL be staged, exactly as it was
        # before -- never committed, never unstaged.
        post_status = _run(["git", "status", "--porcelain"], repo)
        assert "A  sentinel.py" in post_status.stdout, (
            "the pre-staged sentinel was swept into the ledger commit "
            "(or otherwise touched) instead of staying staged (T-1432 "
            "regression)"
        )

        log = _run(["git", "log", "-1", "--name-only", "--pretty=%s"], repo)
        lines = [line for line in log.stdout.splitlines() if line.strip()]
        assert lines[0] == "chore(tickets): file T-0001"
        committed_files = lines[1:]
        assert "sentinel.py" not in committed_files, (
            f"sentinel.py rode along into the ledger commit under an "
            f"unrelated message -- committed files were: {committed_files}"
        )
        assert committed_files == ["tickets/T-0001/ticket.md"]

    # frob:ticket T-1321
    def test_identity_less_environment_falls_back_to_throwaway_git_identity(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_ticket_leases.py::TestCommitTicketLedgerChange.test_identity_less_environment_falls_back_to_throwaway_git_identity  # noqa: E501
        """T-1321: a bare CI runner has no `user.name`/`user.email` in its
        git config (unlike a developer machine's global config, which the
        `repo` fixture's local `git config` calls otherwise mask) -- the
        ledger auto-commit must not fail rc=128 in that environment; it
        retries once with a throwaway `-c` identity."""
        from frob.tickets import transition
        from frob.tickets._leases import commit_ticket_ledger_change

        assert transition(repo, "T-0001", TicketState.PLANNED).is_ok

        # Strip the fixture's own local identity, then isolate this
        # process from ANY other identity source (a real global/system git
        # config on the machine running this test, or GIT_AUTHOR_*/
        # GIT_COMMITTER_* env vars) so the test genuinely reproduces a bare
        # CI runner rather than accidentally falling back to this
        # machine's own config.
        _run(["git", "config", "--unset", "user.email"], repo)
        _run(["git", "config", "--unset", "user.name"], repo)
        fake_home = tmp_path / "fake-home"
        fake_home.mkdir()
        monkeypatch.setenv("HOME", str(fake_home))
        monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
        for var in (
            "GIT_AUTHOR_NAME",
            "GIT_AUTHOR_EMAIL",
            "GIT_COMMITTER_NAME",
            "GIT_COMMITTER_EMAIL",
        ):
            monkeypatch.delenv(var, raising=False)

        result = commit_ticket_ledger_change(
            repo, "T-0001", "chore(tickets): drop T-0001"
        )
        assert result.is_ok, result.err

        status = _run(["git", "status", "--porcelain", "--", _LEDGER_PATHSPEC], repo)
        assert status.stdout.strip() == ""

        log = _run(["git", "log", "-1", "--pretty=%an <%ae>"], repo)
        assert log.stdout.strip() == "frob-bot <frob-bot@example.invalid>"


# frob:ticket T-1615
class TestCommitFullLedgerChange:
    """T-1615: `commit_full_ledger_change` -- `commit_ticket_ledger_
    change`'s twin for a write not scoped to one ticket id (`frob ticket
    archive`, which can move MANY tickets in one call)."""

    def test_commits_dirty_whole_ledger(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_leases.py::TestCommitFullLedgerChange.test_commits_dirty_whole_ledger  # noqa: E501
        from frob.tickets._leases import commit_full_ledger_change

        (repo / "tickets" / "T-0001" / "ticket.md").write_text(
            (repo / "tickets" / "T-0001" / "ticket.md").read_text(encoding="utf-8")
            + "\n<!-- dirtied for the test -->\n",
            encoding="utf-8",
        )

        result = commit_full_ledger_change(repo, "chore(tickets): archive 1 ticket(s)")
        assert result.is_ok, result.err

        status = _run(["git", "status", "--porcelain", "--", _LEDGER_PATHSPEC], repo)
        assert status.stdout.strip() == ""
        log = _run(["git", "log", "-1", "--pretty=%s"], repo)
        assert log.stdout.strip() == "chore(tickets): archive 1 ticket(s)"

    def test_no_op_when_clean(self, repo: Path) -> None:
        # frob:tests \
        # tests/test_ticket_leases.py::TestCommitFullLedgerChange.test_no_op_when_clean
        from frob.tickets._leases import commit_full_ledger_change

        result = commit_full_ledger_change(repo, "chore(tickets): archive 0 ticket(s)")
        assert result.is_ok
        status = _run(["git", "status", "--porcelain", "--", _LEDGER_PATHSPEC], repo)
        assert status.stdout.strip() == ""

    def test_no_commit_flag_warns_when_dirty(
        self, repo: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests tests/test_ticket_leases.py::TestCommitFullLedgerChange.test_no_commit_flag_warns_when_dirty  # noqa: E501
        import logging

        from frob.tickets._leases import commit_full_ledger_change

        (repo / "tickets" / "T-0001" / "ticket.md").write_text(
            (repo / "tickets" / "T-0001" / "ticket.md").read_text(encoding="utf-8")
            + "\n<!-- dirtied for the test -->\n",
            encoding="utf-8",
        )

        with caplog.at_level(logging.WARNING, logger="frob.tickets._leases"):
            result = commit_full_ledger_change(
                repo, "chore(tickets): archive 1 ticket(s)", no_commit=True
            )
        assert result.is_ok
        status = _run(["git", "status", "--porcelain", "--", _LEDGER_PATHSPEC], repo)
        assert status.stdout.strip() != ""
        warnings = [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]
        assert any("DirtyMain-block" in w for w in warnings)

    def test_archive_cli_leaves_repo_clean(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_leases.py::TestCommitFullLedgerChange.test_archive_cli_leaves_repo_clean  # noqa: E501
        """The real incident shape end to end: `frob ticket archive`
        moves a done ticket out of active and into archive, and the
        working tree must be clean afterward -- not just the ticket's own
        write, but the auto-commit T-1615 adds for it."""
        ticket_run(
            AppConfig(
                ticket_command="new",
                ticket_path=repo,
                ticket_title="archive me",
                ticket_kind="docs",
                ticket_body="## Done report\n\nDone.\n",
            )
        )
        ticket_run(
            AppConfig(ticket_command="start", ticket_path=repo, ticket_id="T-0002")
        )
        ticket_run(
            AppConfig(
                ticket_command="close",
                ticket_path=repo,
                ticket_id="T-0002",
                ticket_evidence_cmd="true",
            )
        )
        _commit_all(repo, "pre-archive: T-0002 closed")

        ticket_run(AppConfig(ticket_command="archive", ticket_path=repo))

        status = _run(["git", "status", "--porcelain", "--", _LEDGER_PATHSPEC], repo)
        assert status.stdout.strip() == "", (
            "frob ticket archive left the ledger dirty -- the T-1615 "
            "DirtyMain incident, for the archive verb"
        )


# frob:ticket T-1619
class TestRefuseIfLandInProgress:
    """T-1619: `refuse_if_land_in_progress` -- the exclusive-lease probe
    every ledger-committing verb now runs (via `_add_and_commit_tickets_md`)
    before writing its own commit, so a concurrent `land()` can never race
    a `frob ticket new`/`close`/`drop`/`fail`/`requeue`/`block`/`start`/
    `evidence` commit against the same `root`."""

    def test_allows_when_no_lock_file(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_leases.py::TestRefuseIfLandInProgress.test_allows_when_no_lock_file  # noqa: E501
        from frob.tickets._leases import refuse_if_land_in_progress

        # A fresh checkout that has never landed anything has no land.lock
        # at all -- must never block a first `frob ticket new`.
        assert not (repo / ".frob" / "land.lock").exists()
        result = refuse_if_land_in_progress(repo)
        assert result.is_ok

    def test_refuses_while_land_lock_held(self, repo: Path, caplog) -> None:
        # frob:tests tests/test_ticket_leases.py::TestRefuseIfLandInProgress.test_refuses_while_land_lock_held  # noqa: E501
        import fcntl
        import json

        from frob.tickets._leases import (
            LAND_LOCK_REL,
            LeaseError,
            refuse_if_land_in_progress,
        )

        lock_path = repo / LAND_LOCK_REL
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        holder_fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR, 0o644)
        fcntl.flock(holder_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        os.write(
            holder_fd,
            (json.dumps({"pid": os.getpid(), "ticket_id": "T-9999"}) + "\n").encode(),
        )
        try:
            with caplog.at_level("WARNING"):
                result = refuse_if_land_in_progress(repo)
            assert result.is_err
            assert result.danger_err == LeaseError.LandInProgress
            assert "T-9999" in caplog.text
        finally:
            fcntl.flock(holder_fd, fcntl.LOCK_UN)
            os.close(holder_fd)

    def test_allows_after_a_killed_lands_lock_is_os_released(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_leases.py::TestRefuseIfLandInProgress.test_allows_after_a_killed_lands_lock_is_os_released  # noqa: E501
        # Crash-safety without a timeout or a second liveness mechanism
        # (T-1619's explicit requirement): a subprocess holds the flock,
        # gets SIGKILLed, and the very next probe must see it as free --
        # the kernel releases the lock the instant the holder dies, no
        # polling/TTL/pid-liveness of our own needed.
        from frob.tickets._leases import LAND_LOCK_REL, refuse_if_land_in_progress

        lock_path = repo / LAND_LOCK_REL
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        holder = subprocess.Popen(
            [
                "python3",
                "-c",
                (
                    "import fcntl, os, time, sys\n"
                    "fd = os.open(sys.argv[1], os.O_CREAT | os.O_RDWR, 0o644)\n"
                    "fcntl.flock(fd, fcntl.LOCK_EX)\n"
                    "print('locked', flush=True)\n"
                    "time.sleep(60)\n"
                ),
                str(lock_path),
            ],
            stdout=subprocess.PIPE,
            text=True,
        )
        try:
            assert holder.stdout is not None
            line = holder.stdout.readline()
            assert line.strip() == "locked"

            # While the holder is alive, the probe must refuse.
            blocked = refuse_if_land_in_progress(repo)
            assert blocked.is_err

            holder.kill()
            holder.wait(timeout=5)

            # The instant the holder is gone, the kernel has already freed
            # the flock -- no delay/retry required for the next probe to
            # see it as free.
            freed = refuse_if_land_in_progress(repo)
            assert freed.is_ok
        finally:
            if holder.poll() is None:
                holder.kill()
                holder.wait(timeout=5)

    @pytest.mark.skipif(
        not Path("/proc").is_dir(), reason="T-1619 belt-and-braces scan is Linux-only"
    )
    def test_belt_and_braces_process_scan_without_the_lock_file(
        self, repo: Path, caplog
    ) -> None:
        # frob:tests tests/test_ticket_leases.py::TestRefuseIfLandInProgress.test_belt_and_braces_process_scan_without_the_lock_file  # noqa: E501
        # T-1619, repo owner's explicit second requirement: refuse even
        # when NO land.lock is held at all, as long as a real `frob ticket
        # land`-shaped process is alive with `root` as its cwd -- catches
        # the race window before a land has acquired its flock, and the
        # fcntl-unavailable-platform case, neither of which the flock probe
        # alone can see.
        from frob.tickets._leases import LeaseError, refuse_if_land_in_progress

        assert not (repo / ".frob" / "land.lock").exists()
        holder = subprocess.Popen(
            ["python3", "-c", "import time; time.sleep(30)", "ticket", "land", "T-4242"],
            cwd=str(repo),
        )
        try:
            # Wait for the process to actually appear in /proc under its
            # own cwd before probing -- avoids a startup race against the
            # scan itself.
            for _ in range(50):
                if _proc_test_cwd_matches(holder.pid, repo):
                    break
                time.sleep(0.1)

            with caplog.at_level("WARNING"):
                result = refuse_if_land_in_progress(repo)
            assert result.is_err
            assert result.danger_err == LeaseError.LandInProgress
            assert "T-4242" in caplog.text
        finally:
            holder.kill()
            holder.wait(timeout=5)

    def test_concurrent_land_and_ticket_new_cannot_corrupt_the_ledger(
        self, repo: Path
    ) -> None:
        # frob:tests tests/test_ticket_leases.py::TestRefuseIfLandInProgress.test_concurrent_land_and_ticket_new_cannot_corrupt_the_ledger  # noqa: E501
        # The end-to-end proof: a `land()` call holds `_land_lock` for its
        # duration (simulated here directly, without running the full merge
        # machinery, since this test's job is to prove the EXCLUSIVITY
        # primitive, not re-test `land()` itself elsewhere) while a
        # concurrent `frob ticket new` runs against the SAME root. Before
        # T-1619, `commit_ticket_ledger_change` would happily commit onto
        # `root`'s branch mid-land, moving its tip out from under the land
        # in progress. After T-1619, the ledger write must be refused
        # outright -- `root`'s tip must be UNCHANGED by the attempt, and no
        # new commit may exist naming the ticket the concurrent `new` tried
        # to file.
        from frob.tickets._land import _land_lock

        pre_tip = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()

        with _land_lock(repo, "T-0001"):
            with pytest.raises(SystemExit):
                ticket_run(
                    AppConfig(
                        ticket_command="new",
                        ticket_path=repo,
                        ticket_title="racing ticket",
                        ticket_kind="bug",
                        ticket_scope=["src/feature.py"],
                        ticket_body="## Done report\n\nDone.\n",
                    )
                )

        post_tip = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        assert post_tip == pre_tip, (
            "a concurrent `frob ticket new` moved root's tip while a land "
            "held the exclusive lease -- the exact corruption T-1619 closes"
        )
        log = _run(["git", "log", "--oneline"], repo).stdout
        assert "racing ticket" not in log


# frob:ticket T-1779
class TestDispatchLandGuard:
    """T-1779: `_refuse_if_land_in_progress_for_dispatch` -- the
    pre-dispatch closing of gap 1 (`refuse_if_land_in_progress` used to
    run only at COMMIT time, inside `_add_and_commit_tickets_md`, after a
    mutating verb's handler had already written its change to the
    working tree). This guard runs BEFORE `handler(root, cfg)` for every
    verb except the read-only allowlist and land's own exempt set."""

    def test_refuses_mutating_verb_while_land_in_progress(
        self, repo: Path, caplog
    ) -> None:
        # frob:tests src/frob/app/ticket_runner/__init__.py::_refuse_if_land_in_progress_for_dispatch kind="unit"  # noqa: E501
        import fcntl

        from frob.app.ticket_runner import _refuse_if_land_in_progress_for_dispatch
        from frob.tickets._leases import LAND_LOCK_REL

        lock_path = repo / LAND_LOCK_REL
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        holder_fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR, 0o644)
        fcntl.flock(holder_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            with caplog.at_level("ERROR"), pytest.raises(SystemExit) as exc:
                _refuse_if_land_in_progress_for_dispatch(repo, "priority")
            assert exc.value.code == 1
            assert "priority" in caplog.text
        finally:
            fcntl.flock(holder_fd, fcntl.LOCK_UN)
            os.close(holder_fd)

    def test_read_only_verb_runs_while_land_in_progress(self, repo: Path) -> None:
        # frob:tests src/frob/app/ticket_runner/__init__.py::_refuse_if_land_in_progress_for_dispatch kind="unit"  # noqa: E501
        import fcntl

        from frob.app.ticket_runner import _refuse_if_land_in_progress_for_dispatch
        from frob.tickets._leases import LAND_LOCK_REL

        lock_path = repo / LAND_LOCK_REL
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        holder_fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR, 0o644)
        fcntl.flock(holder_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            # A pure-read verb (e.g. `show`/`list`) must never be blocked
            # from inspecting state while a land holds the lock -- no
            # SystemExit raised.
            _refuse_if_land_in_progress_for_dispatch(repo, "show")
        finally:
            fcntl.flock(holder_fd, fcntl.LOCK_UN)
            os.close(holder_fd)

    def test_refused_verb_never_writes_the_ticket_file_at_all(
        self, repo: Path
    ) -> None:
        # frob:tests src/frob/app/ticket_runner/__init__.py::_refuse_if_land_in_progress_for_dispatch kind="unit"  # noqa: E501
        # Incident 6 (T-1779 follow-up, observed live): the OLD
        # commit-time-only guard let a verb's handler run to completion
        # (writing `runs_last=True` to the ticket file) and only refused
        # the SUBSEQUENT auto-commit -- a partial write, not a clean
        # refusal ("`frob ticket runs-last T-1780 on` printed 'runs-last
        # now True' and THEN 'ledger auto-commit failed... LandInProgress'").
        # This proves the pre-dispatch guard closes that specific gap: the
        # ticket's on-disk `runs_last` field must be UNCHANGED (never even
        # written) when the guard refuses, not merely uncommitted.
        from frob.tickets import load_all
        from frob.tickets._land import _land_lock

        before = load_all(repo)
        assert before.is_ok
        assert before.danger_ok["T-0001"].runs_last is False

        with _land_lock(repo, "T-9999"):
            with pytest.raises(SystemExit):
                ticket_run(
                    AppConfig(
                        ticket_command="runs-last",
                        ticket_path=repo,
                        ticket_id="T-0001",
                        ticket_runs_last_value="on",
                    )
                )

        after = load_all(repo)
        assert after.is_ok
        assert after.danger_ok["T-0001"].runs_last is False, (
            "the ticket's runs_last field was written to disk despite the "
            "land-in-progress refusal -- the guard fired too late (at "
            "commit time), the exact incident-6 partial-write bug"
        )

    def test_land_verb_itself_is_exempt(self, repo: Path) -> None:
        # frob:tests src/frob/app/ticket_runner/__init__.py::_refuse_if_land_in_progress_for_dispatch kind="unit"  # noqa: E501
        import fcntl

        from frob.app.ticket_runner import _refuse_if_land_in_progress_for_dispatch
        from frob.tickets._leases import LAND_LOCK_REL

        lock_path = repo / LAND_LOCK_REL
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        holder_fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR, 0o644)
        fcntl.flock(holder_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            # "land"/"merge-driver"/"sweep-async" are exempt: `land`'s own
            # `_land_lock` already refuses a second concurrent land, and
            # gating "merge-driver" here would deadlock a land against
            # its own git-invoked merge callback.
            _refuse_if_land_in_progress_for_dispatch(repo, "land")
            _refuse_if_land_in_progress_for_dispatch(repo, "merge-driver")
            _refuse_if_land_in_progress_for_dispatch(repo, "sweep-async")
        finally:
            fcntl.flock(holder_fd, fcntl.LOCK_UN)
            os.close(holder_fd)


# frob:ticket T-1779
class TestRemoveWorktree:
    """T-1779: `remove_worktree` -- the single-worktree twin of
    `sweep_worktrees`, reusing the SAME T-1739 per-candidate verdict
    machinery so `frob worktree remove PATH` is a safe alternative to raw
    `git worktree remove` that is actually easier to reach than the
    bulk-scan `sweep` command for one specific worktree."""

    def test_removes_a_clean_unleased_worktree(self, sweep_repo: Path) -> None:
        # frob:tests src/frob/tickets/_leases.py::remove_worktree kind="unit"
        from frob.tickets._leases import remove_worktree

        wt = _add_agent_worktree(sweep_repo, "wt1")

        result = remove_worktree(sweep_repo, wt)
        assert result.is_ok
        assert result.danger_ok.verdict == "removed"
        assert not wt.exists()

    def test_keeps_a_live_process_worktree(self, sweep_repo: Path) -> None:
        # frob:tests src/frob/tickets/_leases.py::remove_worktree kind="unit"
        from frob.tickets._leases import remove_worktree

        wt = _add_agent_worktree(sweep_repo, "wt1")
        holder = subprocess.Popen(
            ["sleep", "60"],
            cwd=str(wt),
        )
        try:
            time.sleep(0.2)
            result = remove_worktree(sweep_repo, wt)
            assert result.is_ok
            assert result.danger_ok.verdict == "kept:live"
            assert wt.exists()
        finally:
            holder.kill()
            holder.wait(timeout=5)

    def test_refuses_a_path_not_registered_as_a_worktree(
        self, sweep_repo: Path, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/tickets/_leases.py::remove_worktree kind="unit"
        from frob.tickets._leases import _WorktreeSweepError, remove_worktree

        not_a_worktree = tmp_path / "elsewhere"
        not_a_worktree.mkdir()

        result = remove_worktree(sweep_repo, not_a_worktree)
        assert result.is_err
        assert result.danger_err == _WorktreeSweepError.NotARegisteredWorktree


# frob:ticket T-1789
class TestOrphanedLeases:
    """T-1779 finding 7: `orphaned_leases` -- a lease whose recorded
    `worktree` path no longer exists on disk at all (a nested worktree
    whose PARENT was retired, taking it with it, is the real incident
    this reproduces)."""

    def test_finds_a_lease_pointing_at_a_gone_worktree(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_leases.py::orphaned_leases kind="unit"
        from frob.tickets._leases import orphaned_leases

        ghost = repo.parent / "nowhere" / "nested" / "gone"
        _write_lease(
            repo, "T-9001", ghost, recorded_at=datetime.now(UTC).isoformat()
        )

        found = orphaned_leases(repo)
        assert [lease.ticket_id for lease in found] == ["T-9001"]

    def test_live_worktree_lease_is_not_orphaned(
        self, repo: Path, second_worktree: Path
    ) -> None:
        # frob:tests src/frob/tickets/_leases.py::orphaned_leases kind="unit"
        from frob.tickets._leases import orphaned_leases

        _write_lease(
            repo,
            "T-9002",
            second_worktree,
            recorded_at=datetime.now(UTC).isoformat(),
        )

        found = orphaned_leases(repo)
        assert found == ()


# frob:ticket T-1789
class TestReleaseOrphanedLease:
    """T-1779 finding 7: `release_orphaned_lease` -- the SAFE, targeted
    release primitive (`frob worktree release-lease TICKET-ID`) that
    refuses to touch anything but a confirmed-orphaned lease."""

    def test_releases_a_genuinely_orphaned_lease(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_leases.py::release_orphaned_lease kind="unit"
        from frob.tickets._leases import _lease_path, leases_dir, release_orphaned_lease

        ghost = repo.parent / "nowhere" / "nested" / "gone"
        _write_lease(
            repo, "T-9001", ghost, recorded_at=datetime.now(UTC).isoformat()
        )
        leases_root = leases_dir(repo).danger_ok
        lease_file = _lease_path(leases_root, "T-9001")
        assert lease_file.exists()

        result = release_orphaned_lease(repo, "T-9001")
        assert result.is_ok
        assert not lease_file.exists()

    def test_refuses_a_live_worktree_lease(
        self, repo: Path, second_worktree: Path
    ) -> None:
        # frob:tests src/frob/tickets/_leases.py::release_orphaned_lease kind="unit"
        from frob.tickets._leases import (
            LeaseError,
            _lease_path,
            leases_dir,
            release_orphaned_lease,
        )

        _write_lease(
            repo,
            "T-9002",
            second_worktree,
            recorded_at=datetime.now(UTC).isoformat(),
        )
        leases_root = leases_dir(repo).danger_ok
        lease_file = _lease_path(leases_root, "T-9002")

        result = release_orphaned_lease(repo, "T-9002")
        assert result.is_err
        assert result.danger_err == LeaseError.LeaseWorktreeMismatch
        assert lease_file.exists()

    def test_refuses_an_unknown_ticket_id(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_leases.py::release_orphaned_lease kind="unit"
        from frob.tickets._leases import LeaseError, release_orphaned_lease

        result = release_orphaned_lease(repo, "T-0000")
        assert result.is_err
        assert result.danger_err == LeaseError.NoLeaseForTicket


# frob:ticket T-1789
class TestWorktreeReleaseLeaseCli:
    """`frob worktree release-lease TICKET-ID`'s CLI entry point."""

    def test_release_lease_cli_releases_an_orphaned_lease(
        self, repo: Path, capsys
    ) -> None:
        # frob:tests src/frob/app/worktree_runner.py::run kind="unit"
        import os as _os

        from frob.app.worktree_runner import run as worktree_run
        from frob.tickets._leases import _lease_path, leases_dir

        ghost = repo.parent / "nowhere" / "nested" / "gone"
        _write_lease(
            repo, "T-9001", ghost, recorded_at=datetime.now(UTC).isoformat()
        )
        leases_root = leases_dir(repo).danger_ok
        lease_file = _lease_path(leases_root, "T-9001")

        cwd = Path.cwd()
        _os.chdir(repo)
        try:
            worktree_run(["release-lease", "T-9001"])
        finally:
            _os.chdir(cwd)
        out = capsys.readouterr().out
        assert "released orphaned lease for T-9001" in out
        assert not lease_file.exists()

    def test_release_lease_cli_exits_1_for_a_live_worktree(
        self, repo: Path, second_worktree: Path, capsys
    ) -> None:
        # frob:tests src/frob/app/worktree_runner.py::run kind="unit"
        import os as _os

        from frob.app.worktree_runner import run as worktree_run

        _write_lease(
            repo,
            "T-9002",
            second_worktree,
            recorded_at=datetime.now(UTC).isoformat(),
        )
        cwd = Path.cwd()
        _os.chdir(repo)
        try:
            with pytest.raises(SystemExit) as exc_info:
                worktree_run(["release-lease", "T-9002"])
        finally:
            _os.chdir(cwd)
        assert exc_info.value.code == 1


# frob:ticket T-1130
class TestNewDropFailAutoCommit:
    """T-1130: `frob ticket new`/`drop`/`fail` each auto-commit their own
    ledger write (parity with `start`'s T-1054 auto-commit) unless
    `--no-commit` is given."""

    def test_new_auto_commits_the_filed_block(self, tmp_path: Path) -> None:
        # frob:tests tests/test_ticket_leases.py::TestNewDropFailAutoCommit.test_new_auto_commits_the_filed_block  # noqa: E501
        main_repo = tmp_path / "main"
        _git_init(main_repo)
        (main_repo / ".gitkeep").write_text("")
        _commit_all(main_repo, "init")

        ticket_run(
            AppConfig(
                ticket_command="new",
                ticket_path=main_repo,
                ticket_title="a new ticket",
                ticket_kind="bug",
            )
        )

        status = _run(
            ["git", "status", "--porcelain", "--", _LEDGER_PATHSPEC], main_repo
        )
        assert status.stdout.strip() == ""
        log = _run(["git", "log", "-1", "--pretty=%s"], main_repo)
        assert log.stdout.strip().startswith("chore(tickets): file T-")
        assert "a new ticket" in log.stdout.strip()

    def test_new_no_commit_leaves_ledger_dirty(self, tmp_path: Path) -> None:
        # frob:tests tests/test_ticket_leases.py::TestNewDropFailAutoCommit.test_new_no_commit_leaves_ledger_dirty  # noqa: E501
        main_repo = tmp_path / "main"
        _git_init(main_repo)
        (main_repo / ".gitkeep").write_text("")
        _commit_all(main_repo, "init")

        ticket_run(
            AppConfig(
                ticket_command="new",
                ticket_path=main_repo,
                ticket_title="a new ticket",
                ticket_kind="bug",
                ticket_no_commit=True,
            )
        )

        status = _run(
            ["git", "status", "--porcelain", "--", _LEDGER_PATHSPEC], main_repo
        )
        assert status.stdout.strip() != ""

    def test_drop_auto_commits_the_state_change(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_leases.py::TestNewDropFailAutoCommit.test_drop_auto_commits_the_state_change  # noqa: E501
        ticket_run(
            AppConfig(
                ticket_command="drop",
                ticket_path=repo,
                ticket_id="T-0001",
                ticket_reason="obsolete",
            )
        )

        status = _run(["git", "status", "--porcelain", "--", _LEDGER_PATHSPEC], repo)
        assert status.stdout.strip() == ""
        log = _run(["git", "log", "-1", "--pretty=%s"], repo)
        assert log.stdout.strip() == "chore(tickets): drop T-0001"

        loaded = load_all(repo)
        assert loaded.is_ok
        assert loaded.danger_ok["T-0001"].state == TicketState.DROPPED

    def test_fail_auto_commits_the_failure_log_and_requeue(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_leases.py::TestNewDropFailAutoCommit.test_fail_auto_commits_the_failure_log_and_requeue  # noqa: E501
        from frob.tickets import transition

        assert transition(repo, "T-0001", TicketState.PLANNED).is_ok
        assert transition(repo, "T-0001", TicketState.IN_PROGRESS).is_ok
        _commit_all(repo, "start T-0001")

        ticket_run(
            AppConfig(
                ticket_command="fail",
                ticket_path=repo,
                ticket_id="T-0001",
                ticket_summary="dead end",
            )
        )

        status = _run(["git", "status", "--porcelain", "--", _LEDGER_PATHSPEC], repo)
        assert status.stdout.strip() == ""
        log = _run(["git", "log", "-1", "--pretty=%s"], repo)
        assert log.stdout.strip() == "chore(tickets): T-0001 fail-logged"

        loaded = load_all(repo)
        assert loaded.is_ok
        assert loaded.danger_ok["T-0001"].state == TicketState.QUEUED


# frob:ticket T-1758
class TestNewTicketProgrammaticAutoCommit:
    """T-1758: `new_ticket` (the LIBRARY function, called directly rather
    than through the `frob ticket new` CLI verb) auto-commits its own
    ledger write -- the structural fix for the gap T-1755 first hit and
    patched with a per-caller wrapper (`_rapid_sweep._commit_regression_
    ticket`): T-1615's uniform auto-commit only ever covered the CLI
    dispatch table, never a programmatic caller like
    `frob.tickets._mutation_sweep_queue`, `frob.testing._stability`,
    `frob.app.sys_runner`, or `frob.fleet` -- all of which call
    `new_ticket` directly and, before this fix, left `tickets.md`
    uncommitted every time, DirtyMain-blocking the next `frob ticket
    land` repo-wide."""

    def test_programmatic_call_auto_commits(self, tmp_path: Path) -> None:
        # frob:tests tests/test_ticket_leases.py::TestNewTicketProgrammaticAutoCommit.test_programmatic_call_auto_commits  # noqa: E501
        from frob.tickets import Origin, TicketKind, TicketSpec, new_ticket

        main_repo = tmp_path / "main"
        _git_init(main_repo)
        (main_repo / ".gitkeep").write_text("")
        _commit_all(main_repo, "init")

        spec = TicketSpec(
            title="filed directly, not via the CLI",
            kind=TicketKind.BUG,
            origin=Origin.AGENT,
        )
        result = new_ticket(main_repo, spec)
        assert result.is_ok, result.danger_err

        status = _run(
            ["git", "status", "--porcelain", "--", _LEDGER_PATHSPEC], main_repo
        )
        assert status.stdout.strip() == "", (
            "a programmatic new_ticket() call must leave the ledger "
            "committed, not dirty -- an uncommitted ledger DirtyMain-"
            "blocks every concurrent `frob ticket land`"
        )
        log = _run(["git", "log", "-1", "--pretty=%s"], main_repo)
        assert log.stdout.strip().startswith("chore(tickets): file T-")

    def test_no_commit_leaves_ledger_dirty_and_warns(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests tests/test_ticket_leases.py::TestNewTicketProgrammaticAutoCommit.test_no_commit_leaves_ledger_dirty_and_warns  # noqa: E501
        import logging

        from frob.tickets import Origin, TicketKind, TicketSpec, new_ticket

        main_repo = tmp_path / "main"
        _git_init(main_repo)
        (main_repo / ".gitkeep").write_text("")
        _commit_all(main_repo, "init")

        spec = TicketSpec(
            title="filed directly with no_commit",
            kind=TicketKind.BUG,
            origin=Origin.AGENT,
        )
        with caplog.at_level(logging.WARNING):
            result = new_ticket(main_repo, spec, no_commit=True)
        assert result.is_ok, result.danger_err

        status = _run(
            ["git", "status", "--porcelain", "--", _LEDGER_PATHSPEC], main_repo
        )
        assert status.stdout.strip() != ""
        assert any("DirtyMain" in r.message for r in caplog.records)

    def test_new_verb_still_produces_one_commit_including_evidence(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_ticket_leases.py::TestNewTicketProgrammaticAutoCommit.test_new_verb_still_produces_one_commit_including_evidence  # noqa: E501
        """T-1758 must not regress `frob ticket new --evidence ...`'s
        documented single-commit behavior (`_new.py`'s own docstring):
        `new_ticket`'s own internal auto-commit is opted OUT of
        (`no_commit=True`) by the CLI verb specifically so its own final
        `commit_ticket_ledger_change` call -- AFTER evidence is applied --
        is still the only commit."""
        main_repo = tmp_path / "main"
        _git_init(main_repo)
        (main_repo / "tests").mkdir()
        (main_repo / "tests" / "test_x.py").write_text(
            "def test_x():\n    assert True\n"
        )
        _commit_all(main_repo, "init")

        before = _run(["git", "log", "--oneline"], main_repo).stdout.strip()
        before_count = len(before.splitlines()) if before else 0

        ticket_run(
            AppConfig(
                ticket_command="new",
                ticket_path=main_repo,
                ticket_title="ticket with evidence",
                ticket_kind="bug",
                ticket_evidence_ids=["tests/test_x.py::test_x"],
            )
        )

        after = _run(["git", "log", "--oneline"], main_repo).stdout.strip()
        after_count = len(after.splitlines()) if after else 0
        assert after_count - before_count == 1, (
            "exactly one new commit -- the filed ticket AND its evidence "
            "together, never split into two"
        )
        status = _run(
            ["git", "status", "--porcelain", "--", _LEDGER_PATHSPEC], main_repo
        )
        assert status.stdout.strip() == ""


class TestCloseEvidenceDoneReportRequeueAutoCommit:
    """T-1178: `frob ticket close`/`evidence`/`done-report`/`requeue` each
    auto-commit their own ledger write via `commit_ticket_ledger_change`
    (T-1130's family extended to every remaining ledger-writing verb) --
    the 2026-07-29 T-0329 incident this closes: a coordinator's uncommitted
    `close` write silently vanished under a concurrent land preflight's
    `git reset --hard`, caught only by T-1131's doctor stale-lease scan.
    """

    def test_evidence_auto_commits(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_leases.py::TestCloseEvidenceDoneReportRequeueAutoCommit.test_evidence_auto_commits  # noqa: E501
        ticket_run(
            AppConfig(
                ticket_command="evidence",
                ticket_path=repo,
                ticket_id="T-0001",
                ticket_evidence_cmd="true",
            )
        )

        status = _run(["git", "status", "--porcelain", "--", _LEDGER_PATHSPEC], repo)
        assert status.stdout.strip() == ""
        log = _run(["git", "log", "-1", "--pretty=%s"], repo)
        assert log.stdout.strip() == "chore(tickets): record evidence for T-0001"

    def test_evidence_no_commit_leaves_ledger_dirty(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_leases.py::TestCloseEvidenceDoneReportRequeueAutoCommit.test_evidence_no_commit_leaves_ledger_dirty  # noqa: E501
        ticket_run(
            AppConfig(
                ticket_command="evidence",
                ticket_path=repo,
                ticket_id="T-0001",
                ticket_evidence_cmd="true",
                ticket_no_commit=True,
            )
        )

        status = _run(["git", "status", "--porcelain", "--", _LEDGER_PATHSPEC], repo)
        assert status.stdout.strip() != ""

    def test_done_report_auto_commits(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_leases.py::TestCloseEvidenceDoneReportRequeueAutoCommit.test_done_report_auto_commits  # noqa: E501
        assert transition(repo, "T-0001", TicketState.PLANNED).is_ok
        assert transition(repo, "T-0001", TicketState.IN_PROGRESS).is_ok
        _commit_all(repo, "start T-0001")

        ticket_run(
            AppConfig(
                ticket_command="done-report",
                ticket_path=repo,
                ticket_id="T-0001",
                ticket_why="did the thing",
            )
        )

        status = _run(["git", "status", "--porcelain", "--", _LEDGER_PATHSPEC], repo)
        assert status.stdout.strip() == ""
        log = _run(["git", "log", "-1", "--pretty=%s"], repo)
        assert log.stdout.strip() == "chore(tickets): T-0001 Done report"

    def test_close_auto_commits(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_leases.py::TestCloseEvidenceDoneReportRequeueAutoCommit.test_close_auto_commits  # noqa: E501
        assert transition(repo, "T-0001", TicketState.PLANNED).is_ok
        assert transition(repo, "T-0001", TicketState.IN_PROGRESS).is_ok
        _commit_all(repo, "start T-0001")

        ticket_run(
            AppConfig(
                ticket_command="close",
                ticket_path=repo,
                ticket_id="T-0001",
                ticket_evidence_cmd="true",
            )
        )

        status = _run(["git", "status", "--porcelain", "--", _LEDGER_PATHSPEC], repo)
        assert status.stdout.strip() == ""
        log = _run(["git", "log", "-1", "--pretty=%s"], repo)
        assert log.stdout.strip() == "chore(tickets): close T-0001"

        loaded = load_all(repo)
        assert loaded.is_ok
        assert loaded.danger_ok["T-0001"].state == TicketState.DONE

    def test_requeue_auto_commits(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_leases.py::TestCloseEvidenceDoneReportRequeueAutoCommit.test_requeue_auto_commits  # noqa: E501
        assert transition(repo, "T-0001", TicketState.PLANNED).is_ok
        assert transition(repo, "T-0001", TicketState.IN_PROGRESS).is_ok
        _commit_all(repo, "start T-0001")

        ticket_run(
            AppConfig(
                ticket_command="requeue",
                ticket_path=repo,
                ticket_id="T-0001",
            )
        )

        status = _run(["git", "status", "--porcelain", "--", _LEDGER_PATHSPEC], repo)
        assert status.stdout.strip() == ""
        log = _run(["git", "log", "-1", "--pretty=%s"], repo)
        assert log.stdout.strip() == "chore(tickets): requeue T-0001"

        loaded = load_all(repo)
        assert loaded.is_ok
        assert loaded.danger_ok["T-0001"].state == TicketState.QUEUED

    def test_requeue_no_commit_leaves_ledger_dirty(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_leases.py::TestCloseEvidenceDoneReportRequeueAutoCommit.test_requeue_no_commit_leaves_ledger_dirty  # noqa: E501
        assert transition(repo, "T-0001", TicketState.PLANNED).is_ok
        assert transition(repo, "T-0001", TicketState.IN_PROGRESS).is_ok
        _commit_all(repo, "start T-0001")

        ticket_run(
            AppConfig(
                ticket_command="requeue",
                ticket_path=repo,
                ticket_id="T-0001",
                ticket_no_commit=True,
            )
        )

        status = _run(["git", "status", "--porcelain", "--", _LEDGER_PATHSPEC], repo)
        assert status.stdout.strip() != ""


# frob:ticket T-1059
class TestWarnIfWorktreeStale:
    """T-1059: `frob ticket start` warns loudly when the worktree's HEAD is
    N+ commits behind `main`'s tip (T-1030's stale-worktree-cut hazard),
    instead of silently carrying a stale base through a whole session."""

    # frob:ticket T-1059
    def test_warns_when_behind_threshold(self, second_worktree: Path) -> None:
        # frob:tests tests/test_ticket_leases.py::TestWarnIfWorktreeStale.test_warns_when_behind_threshold  # noqa: E501
        from frob.tickets._leases import warn_if_worktree_stale

        main_repo = second_worktree.parent / "main"
        for i in range(21):
            (main_repo / f"extra-{i}.py").write_text(f"# extra {i}\n")
            _commit_all(main_repo, f"extra commit {i}")

        import logging

        logger = logging.getLogger("frob.tickets._leases")
        records: list[str] = []

        class _Capture(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                records.append(record.getMessage())

        handler = _Capture()
        logger.addHandler(handler)
        try:
            warn_if_worktree_stale(second_worktree, "T-0001", main_ref="main")
        finally:
            logger.removeHandler(handler)

        assert any("commit(s) behind" in msg for msg in records)
        assert any("T-1030" in msg for msg in records)

    # frob:ticket T-1059
    def test_silent_when_within_threshold(self, second_worktree: Path) -> None:
        # frob:tests tests/test_ticket_leases.py::TestWarnIfWorktreeStale.test_silent_when_within_threshold  # noqa: E501
        from frob.tickets._leases import warn_if_worktree_stale

        main_repo = second_worktree.parent / "main"
        (main_repo / "extra.py").write_text("# extra\n")
        _commit_all(main_repo, "one extra commit")

        import logging

        logger = logging.getLogger("frob.tickets._leases")
        records: list[str] = []

        class _Capture(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                records.append(record.getMessage())

        handler = _Capture()
        logger.addHandler(handler)
        try:
            warn_if_worktree_stale(second_worktree, "T-0001", main_ref="main")
        finally:
            logger.removeHandler(handler)

        assert not any("commit(s) behind" in msg for msg in records)

    # frob:ticket T-1059
    def test_silent_on_non_git_root(self, tmp_path: Path) -> None:
        # frob:tests tests/test_ticket_leases.py::TestWarnIfWorktreeStale.test_silent_on_non_git_root  # noqa: E501
        from frob.tickets._leases import warn_if_worktree_stale

        not_a_repo = tmp_path / "not-a-repo"
        not_a_repo.mkdir()
        # Must not raise despite there being no git repository here at all.
        warn_if_worktree_stale(not_a_repo, "T-0001", main_ref="main")

    # frob:ticket T-1059
    def test_respects_configured_threshold(self, second_worktree: Path) -> None:
        # frob:tests tests/test_ticket_leases.py::TestWarnIfWorktreeStale.test_respects_configured_threshold  # noqa: E501
        from frob.tickets._leases import warn_if_worktree_stale

        main_repo = second_worktree.parent / "main"
        (second_worktree / "frob.toml").write_text(
            "[tickets]\nstale_worktree_warn_commits = 2\n"
        )
        for i in range(3):
            (main_repo / f"small-{i}.py").write_text(f"# small {i}\n")
            _commit_all(main_repo, f"small commit {i}")

        import logging

        logger = logging.getLogger("frob.tickets._leases")
        records: list[str] = []

        class _Capture(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                records.append(record.getMessage())

        handler = _Capture()
        logger.addHandler(handler)
        try:
            warn_if_worktree_stale(second_worktree, "T-0001", main_ref="main")
        finally:
            logger.removeHandler(handler)

        assert any("commit(s) behind" in msg for msg in records)


# frob:ticket T-1059
class TestLoadPositiveIntConfig:
    """T-1059: the shared `[tickets] <key>` positive-int `frob.toml` reader
    both `_load_large_glob_max_files` (T-0453) and
    `_load_stale_worktree_warn_commits` (T-1059) now delegate to."""

    # frob:ticket T-1059
    def test_returns_default_when_frob_toml_absent(self, tmp_path: Path) -> None:
        # frob:tests tests/test_ticket_leases.py::TestLoadPositiveIntConfig.test_returns_default_when_frob_toml_absent  # noqa: E501
        from frob.tickets._leases import load_positive_int_config

        assert load_positive_int_config(tmp_path, "some_key", 7) == 7

    # frob:ticket T-1059
    def test_reads_configured_value(self, tmp_path: Path) -> None:
        # frob:tests tests/test_ticket_leases.py::TestLoadPositiveIntConfig.test_reads_configured_value  # noqa: E501
        from frob.tickets._leases import load_positive_int_config

        (tmp_path / "frob.toml").write_text("[tickets]\nsome_key = 42\n")
        assert load_positive_int_config(tmp_path, "some_key", 7) == 42

    # frob:ticket T-1059
    def test_non_positive_value_falls_back_to_default(self, tmp_path: Path) -> None:
        # frob:tests tests/test_ticket_leases.py::TestLoadPositiveIntConfig.test_non_positive_value_falls_back_to_default  # noqa: E501
        from frob.tickets._leases import load_positive_int_config

        (tmp_path / "frob.toml").write_text("[tickets]\nsome_key = 0\n")
        assert load_positive_int_config(tmp_path, "some_key", 7) == 7

    # frob:ticket T-1059
    def test_malformed_toml_falls_back_to_default(self, tmp_path: Path) -> None:
        # frob:tests tests/test_ticket_leases.py::TestLoadPositiveIntConfig.test_malformed_toml_falls_back_to_default  # noqa: E501
        from frob.tickets._leases import load_positive_int_config

        (tmp_path / "frob.toml").write_text("not valid toml [[[")
        assert load_positive_int_config(tmp_path, "some_key", 7) == 7


# frob:ticket T-1173
class TestRenameLease:
    """T-1173: `renumber_one`'s draft-to-final rename must migrate the
    cross-worktree lease file too, not just the ledger/code references --
    otherwise a worktree that held the draft's lease looks lease-less the
    moment `frob ticket land` renumbers it in that same worktree."""

    def test_rename_migrates_the_lease_file_and_updates_its_ticket_id_field(
        self, repo: Path
    ) -> None:
        # frob:tests tests/test_ticket_leases.py::TestRenameLease.test_rename_migrates_the_lease_file_and_updates_its_ticket_id_field  # noqa: E501
        recorded_at = datetime.now(UTC).isoformat()
        _write_lease(repo, "T-draft-deadbeef", repo, recorded_at=recorded_at)
        resolved = leases_dir(repo)
        assert resolved.is_ok
        old_path = _lease_path(resolved.danger_ok, "T-draft-deadbeef")

        result = rename_lease(repo, "T-draft-deadbeef", "T-0042")
        assert result.is_ok

        new_path = _lease_path(resolved.danger_ok, "T-0042")
        assert not old_path.exists()
        assert new_path.exists()
        migrated = _LeaseRecord.model_validate_json(new_path.read_text())
        # the id embedded in the record's own JSON body is rewritten too --
        # a bare filesystem rename alone would leave the OLD id there,
        # which a reader trusting the parsed record over its path (as
        # read_all_leases does) would still report.
        assert migrated.ticket_id == "T-0042"
        assert migrated.scope == ("src/feature.py",)
        assert migrated.worktree == str(repo)
        assert migrated.branch == "main"
        assert migrated.recorded_at == recorded_at

    def test_rename_is_a_no_op_when_no_lease_exists_for_old_id(
        self, repo: Path
    ) -> None:
        # frob:tests tests/test_ticket_leases.py::TestRenameLease.test_rename_is_a_no_op_when_no_lease_exists_for_old_id  # noqa: E501
        result = rename_lease(repo, "T-draft-noexist", "T-0099")
        assert result.is_ok

        resolved = leases_dir(repo)
        assert resolved.is_ok
        assert not _lease_path(resolved.danger_ok, "T-0099").exists()


# frob:ticket T-1173
class TestRenumberMigratesLeaseEndToEnd:
    """T-1173 regression, real draft+lease fixture end to end: a ticket
    filed off the default branch (minting a provisional T-draft-XXXXXXXX
    id), started IN_PROGRESS in that same worktree (recording its lease
    under the draft id), then renumbered to a final id in the SAME
    worktree (`renumber_one`/`finalize_draft_for_land`, exactly what
    `frob ticket land` does) must leave the worktree still holding a
    resolvable lease under the FINAL id -- the incident T-1172's close
    hit: the lease was left behind under the old draft id, so a
    subsequent `frob check --ticket <final-id>` in that same worktree saw
    no recorded lease at all."""

    def test_renumber_one_migrates_the_lease_the_worktree_still_holds(
        self, repo: Path, second_worktree: Path
    ) -> None:
        # frob:tests tests/test_ticket_leases.py::TestRenumberMigratesLeaseEndToEnd.test_renumber_one_migrates_the_lease_the_worktree_still_holds  # noqa: E501
        (second_worktree / "src").mkdir(parents=True, exist_ok=True)
        (second_worktree / "src" / "widget.py").write_text("# widget\n")
        filed = new_ticket(
            second_worktree,
            TicketSpec(
                title="off-branch widget",
                kind=TicketKind.FEATURE,
                origin=Origin.AGENT,
                scope=("src/widget.py",),
            ),
        )
        assert filed.is_ok
        draft_id = filed.danger_ok.id
        assert draft_id.startswith("T-draft-")

        started = transition(second_worktree, draft_id, TicketState.PLANNED)
        assert started.is_ok
        started = transition(second_worktree, draft_id, TicketState.IN_PROGRESS)
        assert started.is_ok

        resolved = leases_dir(second_worktree)
        assert resolved.is_ok
        draft_lease_path = _lease_path(resolved.danger_ok, draft_id)
        assert draft_lease_path.exists()

        result = renumber_one(second_worktree, draft_id, "T-0777")
        assert result.is_ok

        final_lease_path = _lease_path(resolved.danger_ok, "T-0777")
        assert not draft_lease_path.exists()
        assert final_lease_path.exists()

        # the worktree's own lease-resolution path now finds it under the
        # final id -- the exact "no recorded lease" incident this closes.
        all_leases = read_all_leases(second_worktree)
        assert any(record.ticket_id == "T-0777" for record in all_leases)
        assert not any(record.ticket_id == draft_id for record in all_leases)

    def test_finalize_draft_for_land_migrates_the_lease_the_worktree_still_holds(
        self, repo: Path, second_worktree: Path
    ) -> None:
        # frob:tests tests/test_ticket_leases.py::TestRenumberMigratesLeaseEndToEnd.test_finalize_draft_for_land_migrates_the_lease_the_worktree_still_holds  # noqa: E501
        (second_worktree / "src").mkdir(parents=True, exist_ok=True)
        (second_worktree / "src" / "gadget.py").write_text("# gadget\n")
        filed = new_ticket(
            second_worktree,
            TicketSpec(
                title="off-branch gadget",
                kind=TicketKind.FEATURE,
                origin=Origin.AGENT,
                scope=("src/gadget.py",),
            ),
        )
        assert filed.is_ok
        draft_id = filed.danger_ok.id
        assert draft_id.startswith("T-draft-")

        started = transition(second_worktree, draft_id, TicketState.PLANNED)
        assert started.is_ok
        started = transition(second_worktree, draft_id, TicketState.IN_PROGRESS)
        assert started.is_ok

        resolved = leases_dir(second_worktree)
        assert resolved.is_ok
        draft_lease_path = _lease_path(resolved.danger_ok, draft_id)
        assert draft_lease_path.exists()

        # `finalize_draft_for_land`'s land-path twin: id ceiling read fresh
        # from `repo` (main), rename applied against `second_worktree`
        # (the worktree actually holding the lease) -- exactly `frob
        # ticket land`'s own call shape.
        result = finalize_draft_for_land(second_worktree, draft_id, repo)
        assert result.is_ok
        final_id = result.danger_ok
        assert not final_id.startswith("T-draft-")

        final_lease_path = _lease_path(resolved.danger_ok, final_id)
        assert not draft_lease_path.exists()
        assert final_lease_path.exists()


# frob:ticket T-1650
class TestWarnIfWorktreeStaleFailureBranches:
    """T-draft-c74b8c63 (T-1273 TEST005 remainder): `warn_if_worktree_stale`
    must degrade to a silent no-op on every git/config failure shape it
    claims to tolerate (its own docstring), not just the "not a git repo
    at all" case `test_silent_on_non_git_root` already covers -- these
    exercise the DISTINCT branches: a repo where `main_ref` itself does not
    resolve, a `rev-list --count` that fails, and a genuinely non-numeric
    count -- each must still return `None` and log nothing, never raise."""

    # frob:ticket T-1650
    def test_silent_when_main_ref_does_not_exist(self, second_worktree: Path) -> None:
        # frob:tests tests/test_ticket_leases.py::TestWarnIfWorktreeStaleFailureBranches.test_silent_when_main_ref_does_not_exist  # noqa: E501
        import logging

        logger = logging.getLogger("frob.tickets._leases")
        records: list[str] = []

        class _Capture(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                records.append(record.getMessage())

        handler = _Capture()
        logger.addHandler(handler)
        try:
            # `main_ref` names a branch that has never existed in this
            # fixture repo -- `git merge-base` fails with a nonzero exit,
            # hitting the `merge_base_result...returncode != 0` branch
            # distinctly from the "not a git repo at all" `.is_err` branch.
            warn_if_worktree_stale(second_worktree, "T-0001", main_ref="does-not-exist")
        finally:
            logger.removeHandler(handler)

        assert not any("commit(s) behind" in msg for msg in records)

    # frob:ticket T-1650
    def test_silent_when_rev_list_count_fails(self, second_worktree: Path) -> None:
        # frob:tests tests/test_ticket_leases.py::TestWarnIfWorktreeStaleFailureBranches.test_silent_when_rev_list_count_fails  # noqa: E501
        from frob import gitio

        real_run_argv = gitio.run_argv

        def _fail_rev_list(argv: list[str]) -> object:
            if "rev-list" in argv:
                return real_run_argv(
                    ["git", "-C", str(second_worktree), "this-is-not-a-git-subcommand"]
                )
            return real_run_argv(argv)

        with patch("frob.tickets._leases.gitio.run_argv", side_effect=_fail_rev_list):
            # Must not raise even though the rev-list phase's own git
            # invocation fails -- the `count_result...returncode != 0`
            # branch, reached only after merge-base already succeeded.
            warn_if_worktree_stale(second_worktree, "T-0001", main_ref="main")

    # frob:ticket T-1650
    def test_silent_when_count_is_not_numeric(self, second_worktree: Path) -> None:
        # frob:tests tests/test_ticket_leases.py::TestWarnIfWorktreeStaleFailureBranches.test_silent_when_count_is_not_numeric  # noqa: E501
        from frob import gitio

        real_run_argv = gitio.run_argv

        def _garbage_count(argv: list[str]) -> object:
            result = real_run_argv(argv)
            if "rev-list" in argv and result.is_ok:
                garbled = result.danger_ok.model_copy(
                    update={"stdout": "not-a-number\n"}
                )
                return Ok(garbled)
            return result

        with patch("frob.tickets._leases.gitio.run_argv", side_effect=_garbage_count):
            # `int(count_result...stdout.strip())` raises `ValueError` on a
            # non-numeric count -- must degrade silently, not propagate.
            warn_if_worktree_stale(second_worktree, "T-0001", main_ref="main")

    # frob:ticket T-1650
    def test_silent_when_config_lookup_raises(self, second_worktree: Path) -> None:
        # frob:tests tests/test_ticket_leases.py::TestWarnIfWorktreeStaleFailureBranches.test_silent_when_config_lookup_raises  # noqa: E501
        with patch(
            "frob.tickets._leases._load_stale_worktree_warn_commits",
            side_effect=KeyError("boom"),
        ):
            # The outer `except (KeyError, TypeError)` must swallow a
            # config-lookup surprise from anywhere inside the try block,
            # not just from the git calls themselves.
            warn_if_worktree_stale(second_worktree, "T-0001", main_ref="main")


# frob:ticket T-1650
class TestLeaseAgeSecondsExceptionBranch:
    """T-draft-c74b8c63: `lease_age_seconds` treats ANY unparseable
    `recorded_at` as `None` (its docstring's "defensive -- a lease file is
    peer-writable" contract), not only a `ValueError` from
    `datetime.fromisoformat` -- covers the broader `except Exception`
    fallback the `ValueError`-only existing tests never reach."""

    # frob:ticket T-1650
    def test_none_when_recorded_at_is_not_a_string(self) -> None:
        # frob:tests tests/test_ticket_leases.py::TestLeaseAgeSecondsExceptionBranch.test_none_when_recorded_at_is_not_a_string  # noqa: E501
        record = _LeaseRecord(
            ticket_id="T-0001",
            scope=(),
            worktree="/tmp/wt",
            branch="main",
            recorded_at="",
        )
        # Force a non-`ValueError` failure inside `datetime.fromisoformat`
        # by patching it to raise something else entirely -- the second,
        # broader `except Exception` branch this function's docstring
        # promises to cover.
        with patch("frob.tickets._leases.datetime") as mock_datetime:
            mock_datetime.fromisoformat.side_effect = TypeError("not a valid input")
            assert lease_age_seconds(record) is None


# frob:ticket T-1650
class TestRecordReleaseRenameLeaseErrorBranches:
    """T-draft-c74b8c63: `record_lease`/`release_lease`/`rename_lease` are
    all documented "best-effort" -- an OS-level failure writing, removing,
    or reading a lease file must degrade to a logged warning and `Ok(None)`,
    never propagate. These exercise the OSError branches real git fixtures
    make reachable without mocking the lease layer's own file model."""

    # frob:ticket T-1650
    def test_record_lease_degrades_on_mkdir_failure(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_leases.py::TestRecordReleaseRenameLeaseErrorBranches.test_record_lease_degrades_on_mkdir_failure  # noqa: E501
        with patch(
            "frob.tickets._leases.Path.mkdir",
            side_effect=OSError("permission denied"),
        ):
            result = record_lease(repo, "T-0001", ("src/x.py",))
        # Best-effort: a filesystem failure never turns into an `Err` --
        # the caller's own state transition must proceed regardless.
        assert result.is_ok

    # frob:ticket T-1650
    def test_record_lease_degrades_on_write_failure(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_leases.py::TestRecordReleaseRenameLeaseErrorBranches.test_record_lease_degrades_on_write_failure  # noqa: E501
        with patch(
            "frob.tickets._leases.Path.write_text",
            side_effect=OSError("disk full"),
        ):
            result = record_lease(repo, "T-0001", ("src/x.py",))
        assert result.is_ok
        # And no lease file exists, since the write never happened.
        resolved = leases_dir(repo)
        assert resolved.is_ok
        assert not _lease_path(resolved.danger_ok, "T-0001").exists()

    # frob:ticket T-1650
    def test_release_lease_degrades_on_unlink_failure(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_leases.py::TestRecordReleaseRenameLeaseErrorBranches.test_release_lease_degrades_on_unlink_failure  # noqa: E501
        recorded = record_lease(repo, "T-0002", ("src/y.py",))
        assert recorded.is_ok

        with patch(
            "frob.tickets._leases.Path.unlink",
            side_effect=OSError("permission denied"),
        ):
            result = release_lease(repo, "T-0002")
        assert result.is_ok

    # frob:ticket T-1650
    def test_rename_lease_degrades_on_malformed_old_record(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_leases.py::TestRecordReleaseRenameLeaseErrorBranches.test_rename_lease_degrades_on_malformed_old_record  # noqa: E501
        resolved = leases_dir(repo)
        assert resolved.is_ok
        leases_root = resolved.danger_ok
        leases_root.mkdir(parents=True, exist_ok=True)
        old_path = _lease_path(leases_root, "T-0003")
        old_path.write_text("not valid json{{{", encoding="utf-8")

        result = rename_lease(repo, "T-0003", "T-0004")
        # Malformed old record -> `model_validate_json` raises `ValueError`
        # -> best-effort no-op, and the malformed file is left in place
        # (never partially renamed).
        assert result.is_ok
        assert old_path.exists()
        new_path = _lease_path(leases_root, "T-0004")
        assert not new_path.exists()

    # frob:ticket T-1650
    def test_rename_lease_degrades_on_write_failure(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_leases.py::TestRecordReleaseRenameLeaseErrorBranches.test_rename_lease_degrades_on_write_failure  # noqa: E501
        recorded = record_lease(repo, "T-0005", ("src/z.py",))
        assert recorded.is_ok
        resolved = leases_dir(repo)
        assert resolved.is_ok
        old_path = _lease_path(resolved.danger_ok, "T-0005")
        assert old_path.exists()

        with patch(
            "frob.tickets._leases.Path.write_text",
            side_effect=OSError("disk full"),
        ):
            result = rename_lease(repo, "T-0005", "T-0006")
        assert result.is_ok
        # The old lease survives untouched since the rename's write step
        # (which precedes the unlink) never succeeded.
        assert old_path.exists()


# frob:ticket T-1615
class TestLedgerAutoCommitEnumeratedOverDispatchTable:
    """T-1615: `_auto_commit_ledger_after_dispatch` (`frob.app.ticket_
    runner`) wraps the ONE dispatch call site in `run()`, so every
    ledger-mutating verb -- not a hand-picked sample of them -- must leave
    the repo clean after running. `test_dispatch_table_verbs_are_all_
    accounted_for` below walks the REAL `_ticket_dispatch_table()` and
    fails the instant a verb is added there without a maintainer having
    explicitly filed it into one of this class's buckets (mutating-and-
    tested-here / read-only / needing its own dedicated fixture / owning
    its own multi-file commit transaction) -- this is the "verb number
    twelve" guard the ticket asked for."""

    # Verbs whose only job is reading the ledger: they never call
    # `write_ticket`/`_set_ticket_field` at all, so "leaves the repo
    # clean" holds trivially for them and they need no invocation here.
    # `reverify` re-runs close's own verification guards against an
    # ALREADY-done ticket but never calls `transition` -- its own
    # docstring is explicit: "no write, no state change, either way."
    _READ_ONLY_VERBS = frozenset(
        {"list", "show", "doable", "board", "epic", "brief", "flow", "reverify"}
    )

    # Verbs that DO mutate the ledger but need a fixture/setup shape this
    # class's plain single-ticket `repo` fixture does not provide (a
    # worktree, a second ticket, evidence, a Done report, ...) -- each has
    # its OWN dedicated coverage elsewhere (`TestTicketNew`/`TestTicketDrop`
    # /`TestTicketFail`/`TestTicketClose`/`TestTicketEvidence`/
    # `TestTicketStart`/`TestTicketSweep`/`TestTicketReconcileCli`/
    # `TestTicketMigrate`/`TestTicketArchive` in
    # `tests/unit/test_app_runners_batch7.py`, or the review/scope-ack/
    # sprint/plan/work call sites, or `TestCloseEvidenceDoneReportRequeueAutoCommit`
    # above), so re-deriving their setup here would duplicate fixtures
    # rather than add real coverage. Every one of `new`/`drop`/`fail`/
    # `done-report`/`evidence`/`close`/`start` already calls
    # `commit_ticket_ledger_change` directly (T-1130/T-1178) and was
    # never part of the T-1615 incident in the first place.
    _NEEDS_DEDICATED_FIXTURE = frozenset(
        {
            "new",
            "drop",
            "fail",
            "done-report",
            "evidence",
            "close",
            "start",
            "sweep",
            "scope-ack",
            "sprint",
            "migrate",
            "reconcile",
            "archive",
            "plan",
            "work",
            "review",
        }
    )

    # verb -> the AppConfig kwargs (plus `ticket_command`/`ticket_path`)
    # that exercise it against the shared `repo` fixture's T-0001.
    _MUTATING_VERB_INVOCATIONS: dict[str, dict] = {
        "block": {"ticket_id": "T-0001", "ticket_by": "T-0002"},
        "scope": {
            "ticket_id": "T-0001",
            "ticket_scope_add": ["src/other.py"],
            "ticket_scope_reason": "widen for T-1615 coverage",
        },
        "priority": {"ticket_id": "T-0001", "ticket_priority_level": "high"},
        "kind": {"ticket_id": "T-0001", "ticket_kind_value": "feature"},
        "component": {"ticket_id": "T-0001", "ticket_component": "mycomp"},
        "label": {"ticket_id": "T-0001", "ticket_label_add": ["urgent"]},
        "accept": {
            "ticket_id": "T-0001",
            "ticket_accept_criterion": ["a real criterion"],
        },
        "tier": {"ticket_id": "T-0001", "ticket_tier_value": "story"},
        "runs-last": {"ticket_id": "T-0001", "ticket_runs_last_value": "on"},
        "attach": {"ticket_id": "T-0001"},  # path filled in per-test
        "requeue": {"ticket_id": "T-0001"},  # ticket started first, per-test
    }

    def test_dispatch_table_verbs_are_all_accounted_for(self) -> None:
        # frob:tests tests/test_ticket_leases.py::TestLedgerAutoCommitEnumeratedOverDispatchTable.test_dispatch_table_verbs_are_all_accounted_for  # noqa: E501
        from frob.app.ticket_runner import (
            _LEDGER_TRANSACTIONAL_VERBS,
            _ticket_dispatch_table,
        )

        table_verbs = frozenset(_ticket_dispatch_table().keys())
        accounted = (
            frozenset(self._MUTATING_VERB_INVOCATIONS)
            | self._READ_ONLY_VERBS
            | self._NEEDS_DEDICATED_FIXTURE
            | _LEDGER_TRANSACTIONAL_VERBS
        )
        missing = table_verbs - accounted
        assert not missing, (
            f"verb(s) {sorted(missing)} exist in the real "
            "_ticket_dispatch_table() but are not accounted for by "
            "TestLedgerAutoCommitEnumeratedOverDispatchTable -- file them "
            "into _MUTATING_VERB_INVOCATIONS (if they write the ledger), "
            "_READ_ONLY_VERBS, _NEEDS_DEDICATED_FIXTURE, or "
            "frob.app.ticket_runner._LEDGER_TRANSACTIONAL_VERBS before "
            "this test can pass again"
        )

    @pytest.mark.parametrize("verb", sorted(_MUTATING_VERB_INVOCATIONS))
    def test_verb_leaves_repo_clean(self, repo: Path, verb: str) -> None:
        # frob:tests tests/test_ticket_leases.py::TestLedgerAutoCommitEnumeratedOverDispatchTable.test_verb_leaves_repo_clean  # noqa: E501
        kwargs = dict(self._MUTATING_VERB_INVOCATIONS[verb])
        if verb == "attach":
            attachment = repo / "attachment.txt"
            attachment.write_text("evidence\n", encoding="utf-8")
            kwargs["ticket_attach_path"] = attachment
        if verb == "requeue":
            ticket_run(
                AppConfig(ticket_command="start", ticket_path=repo, ticket_id="T-0001")
            )

        ticket_run(AppConfig(ticket_command=verb, ticket_path=repo, **kwargs))

        status = _run(["git", "status", "--porcelain", "--", _LEDGER_PATHSPEC], repo)
        assert status.stdout.strip() == "", (
            f"frob ticket {verb} left the ledger dirty -- this is exactly "
            "the T-1615 DirtyMain incident"
        )
