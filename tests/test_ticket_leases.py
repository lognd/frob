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
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from frob.app.config import AppConfig
from frob.app.ticket_runner import run as ticket_run
from frob.tickets import TicketState, load_all, transition
from frob.tickets._leases import (
    LEASE_TTL_SECONDS,
    _LeaseRecord,
    _list_agent_worktrees,
    leases_dir,
    read_all_leases,
    resolve_lease,
    sweep_worktrees,
)


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
        # frob:tests tests/test_ticket_leases.py::TestRefusesTerminalState.test_refuses_done_ticket  # noqa: E501
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
        # frob:tests tests/test_ticket_leases.py::TestSweepWorktrees.test_clean_no_lease_removed  # noqa: E501
        wt = _add_agent_worktree(sweep_repo, "wt1")

        result = sweep_worktrees(sweep_repo)
        assert result.is_ok
        verdicts = result.danger_ok
        assert len(verdicts) == 1
        assert verdicts[0].verdict == "removed"
        assert not wt.exists()

    def test_clean_live_lease_kept(self, sweep_repo: Path) -> None:
        # frob:tests tests/test_ticket_leases.py::TestSweepWorktrees.test_clean_live_lease_kept  # noqa: E501
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
        # frob:tests tests/test_ticket_leases.py::TestSweepWorktrees.test_dirty_kept  # noqa: E501
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
        # frob:tests tests/test_ticket_leases.py::TestSweepWorktrees.test_dry_run_removes_nothing  # noqa: E501
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
        # frob:tests tests/test_ticket_leases.py::TestSweepWorktrees.test_branches_survive_removal  # noqa: E501
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

        status = _run(["git", "status", "--porcelain", "--", "tickets.md"], repo)
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

        status = _run(["git", "status", "--porcelain", "--", "tickets.md"], repo)
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
            f"git -C {repo} add tickets.md && git -C {repo} commit -m "
            '"chore(tickets): record T-0001 start transition"'
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
        # frob:waive SEC110 reason="asserting a test-set dispatch-context marker restored, not a secret"
        assert os.environ.get("FROB_AGENT") == "1"

        status = _run(["git", "status", "--porcelain", "--", "tickets.md"], repo)
        assert status.stdout.strip() == ""
