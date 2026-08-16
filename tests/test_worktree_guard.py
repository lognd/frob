"""T-0431: worktree-lease guard -- frob mutating commands fail LOUDLY when
FROB_WORKTREE names a worktree other than the cwd's actual git top-level.

Reproduces the real incident: a dispatched worktree agent ran `frob ticket
new` (and other mutating commands) directly against the shared main
checkout instead of its own worktree."""

from __future__ import annotations

import os
import shlex
import subprocess
import time
from pathlib import Path

import pytest

from frob.app.agent_runner import run as agent_run
from frob.gitio import GitError
from frob.scaffold._managed import _apply_stash_guard
from frob.tickets import Origin, TicketKind, TicketSpec, new_ticket
from frob.tickets._leases import _LeaseRecord, leases_dir, sweep_worktrees
from frob.tickets._models import TicketError
from frob.tickets._worktree_guard import (
    FROB_AGENT_ENV,
    FROB_WORKTREE_ENV,
    PYTEST_XDIST_AUTO_NUM_WORKERS_ENV,
    agent_env_exports,
    enforce_worktree_lease,
)


def _git(*args: str, cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def _init_repo(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    _git("init", "-q", "-b", "main", cwd=root)
    _git("config", "user.email", "test@example.com", cwd=root)
    _git("config", "user.name", "Test", cwd=root)
    (root / "tickets.md").write_text("# Tickets\n\n")
    _git("add", "-A", cwd=root)
    _git("commit", "-q", "-m", "init", cwd=root)


def _write_lease(root: Path, ticket_id: str, worktree: Path) -> None:
    """Writes a live cross-worktree lease file for `ticket_id` (T-2221
    fixture helper, same shape `tests/test_ticket_leases.py::_write_lease`
    uses): `worktree` need only exist on disk for `_probe_worktree_
    liveness` to classify it `"present"` -- it does not need to be a
    registered `git worktree` of `root`."""
    resolved = leases_dir(root)
    assert resolved.is_ok
    leases_root = resolved.danger_ok
    leases_root.mkdir(parents=True, exist_ok=True)
    worktree.mkdir(parents=True, exist_ok=True)
    record = _LeaseRecord(
        ticket_id=ticket_id,
        scope=("src/feature.py",),
        worktree=str(worktree),
        branch=f"agent-{ticket_id}",
        recorded_at="2026-08-16T00:00:00+00:00",
    )
    (leases_root / f"{ticket_id}.json").write_text(
        record.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )


class TestEnforceWorktreeLease:
    def test_no_env_var_is_unrestricted(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_worktree_guard.py::TestEnforceWorktreeLease.test_no_env_var_is_unrestricted  # noqa: E501
        monkeypatch.delenv(FROB_WORKTREE_ENV, raising=False)
        _init_repo(tmp_path)
        assert enforce_worktree_lease(tmp_path).is_ok

    def test_matching_worktree_passes(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_worktree_guard.py::TestEnforceWorktreeLease.test_matching_worktree_passes  # noqa: E501
        _init_repo(tmp_path)
        monkeypatch.setenv(FROB_WORKTREE_ENV, str(tmp_path))
        assert enforce_worktree_lease(tmp_path).is_ok

    def test_mismatched_worktree_refuses(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_worktree_guard.py::TestEnforceWorktreeLease.test_mismatched_worktree_refuses  # noqa: E501
        main_repo = tmp_path / "main"
        _init_repo(main_repo)
        elsewhere = tmp_path / "elsewhere-worktree"
        elsewhere.mkdir()

        monkeypatch.setenv(FROB_WORKTREE_ENV, str(elsewhere))
        result = enforce_worktree_lease(main_repo)
        assert result.is_err
        assert result.danger_err == TicketError.WorktreeLeaseViolation

    def test_non_repo_root_passes_through(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_worktree_guard.py::TestEnforceWorktreeLease.test_non_repo_root_passes_through  # noqa: E501
        not_a_repo = tmp_path / "not-a-repo"
        not_a_repo.mkdir()
        monkeypatch.setenv(FROB_WORKTREE_ENV, str(tmp_path / "elsewhere"))
        assert enforce_worktree_lease(not_a_repo).is_ok


class TestWorktreeGuardWiredIntoMutations:
    """The acceptance case named in the ticket: a mutating command run from
    the WRONG checkout fails loudly; the same command from the leased
    worktree succeeds."""

    def _spec(self) -> TicketSpec:
        return TicketSpec(title="Guarded", kind=TicketKind.BUG, origin=Origin.AGENT)

    def test_new_ticket_from_main_while_leased_elsewhere_fails(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_worktree_guard.py::TestWorktreeGuardWiredIntoMutations.test_new_ticket_from_main_while_leased_elsewhere_fails  # noqa: E501
        main_repo = tmp_path / "main"
        _init_repo(main_repo)
        worktree = tmp_path / "wt"
        _git("worktree", "add", "-b", "feature", str(worktree), cwd=main_repo)

        monkeypatch.setenv(FROB_WORKTREE_ENV, str(worktree))
        result = new_ticket(main_repo, self._spec())
        assert result.is_err
        assert result.danger_err == TicketError.WorktreeLeaseViolation

    def test_new_ticket_from_leased_worktree_succeeds(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_worktree_guard.py::TestWorktreeGuardWiredIntoMutations.test_new_ticket_from_leased_worktree_succeeds  # noqa: E501
        main_repo = tmp_path / "main"
        _init_repo(main_repo)
        worktree = tmp_path / "wt"
        _git("worktree", "add", "-b", "feature", str(worktree), cwd=main_repo)

        monkeypatch.setenv(FROB_WORKTREE_ENV, str(worktree))
        result = new_ticket(worktree, self._spec())
        assert result.is_ok

    def test_coordinator_with_no_lease_mutates_main_fine(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_worktree_guard.py::TestWorktreeGuardWiredIntoMutations.test_coordinator_with_no_lease_mutates_main_fine  # noqa: E501
        monkeypatch.delenv(FROB_WORKTREE_ENV, raising=False)
        main_repo = tmp_path / "main"
        _init_repo(main_repo)
        result = new_ticket(main_repo, self._spec())
        assert result.is_ok


class TestAgentEnvExports:
    """T-0574: `agent_env_exports` resolves the FROB_WORKTREE/FROB_AGENT
    values `frob agent env` prints, mechanically instead of relying on a
    dispatcher/playbook to remember to set them by hand."""

    def test_resolves_worktree_root(self, tmp_path: Path) -> None:
        # frob:tests tests/test_worktree_guard.py::TestAgentEnvExports.test_resolves_worktree_root  # noqa: E501
        _init_repo(tmp_path)
        result = agent_env_exports(tmp_path)
        assert result.is_ok
        exports = result.danger_ok
        assert exports[FROB_WORKTREE_ENV] == str(tmp_path.resolve())
        assert exports[FROB_AGENT_ENV] == "1"

    def test_non_repo_root_errs(self, tmp_path: Path) -> None:
        # frob:tests tests/test_worktree_guard.py::TestAgentEnvExports.test_non_repo_root_errs  # noqa: E501
        not_a_repo = tmp_path / "not-a-repo"
        not_a_repo.mkdir()
        result = agent_env_exports(not_a_repo)
        assert result.is_err
        assert result.danger_err == GitError.NotARepo

    def test_no_fleet_context_omits_xdist_bound(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/test_worktree_guard.py::TestAgentEnvExports.test_no_fleet_context_omits\
        # _xdist_bound
        """T-2221 must-still-pass control: no other live agent lease ->
        `PYTEST_XDIST_AUTO_NUM_WORKERS` is not exported at all, so a pytest
        spawned from this environment resolves `-n auto` against xdist's
        own default (the full CPU count) -- the single-developer path is
        never degraded."""
        _init_repo(tmp_path)
        result = agent_env_exports(tmp_path)
        assert result.is_ok
        assert PYTEST_XDIST_AUTO_NUM_WORKERS_ENV not in result.danger_ok

    def test_fleet_context_bounds_xdist_workers(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/test_worktree_guard.py::TestAgentEnvExports.test_fleet_context_bounds_x\
        # dist_workers
        """T-2221 acceptance 1: three OTHER live agent leases visible via
        the real cross-worktree lease side-channel (never `ps`-parsed) ->
        `agent_env_exports` includes a `PYTEST_XDIST_AUTO_NUM_WORKERS`
        bounded well below the raw CPU count, so a 4th agent joining does
        not also request the whole machine."""
        _init_repo(tmp_path)
        for i in range(3):
            _write_lease(tmp_path, f"T-100{i}", tmp_path.parent / f"peer-wt-{i}")
        result = agent_env_exports(tmp_path)
        assert result.is_ok
        exports = result.danger_ok
        assert PYTEST_XDIST_AUTO_NUM_WORKERS_ENV in exports
        workers = int(exports[PYTEST_XDIST_AUTO_NUM_WORKERS_ENV])
        cpu_count = os.cpu_count() or 1
        assert 1 <= workers <= cpu_count
        # 3 other agents + this one joining = 4-way split, never the raw
        # per-agent `-n auto` count that caused the measured oversubscription.
        assert workers < cpu_count or cpu_count == 1


class TestAgentRunnerEnv:
    """T-0574: `frob agent env` CLI wiring (`frob.app.agent_runner`)."""

    def test_env_prints_export_lines_for_worktree(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        # frob:tests tests/test_worktree_guard.py::TestAgentRunnerEnv.test_env_prints_export_lines_for_worktree  # noqa: E501
        _init_repo(tmp_path)
        agent_run(["env", str(tmp_path)])
        out = capsys.readouterr().out
        assert f"export FROB_WORKTREE={shlex.quote(str(tmp_path.resolve()))}" in out
        assert f"export FROB_AGENT={shlex.quote('1')}" in out

    def test_env_defaults_to_cwd(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        # frob:tests tests/test_worktree_guard.py::TestAgentRunnerEnv.test_env_defaults_to_cwd  # noqa: E501
        _init_repo(tmp_path)
        monkeypatch.chdir(tmp_path)
        agent_run(["env"])
        out = capsys.readouterr().out
        assert f"export FROB_WORKTREE={shlex.quote(str(tmp_path.resolve()))}" in out

    def test_env_non_repo_path_exits_nonzero(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        # frob:tests tests/test_worktree_guard.py::TestAgentRunnerEnv.test_env_non_repo_path_exits_nonzero  # noqa: E501
        not_a_repo = tmp_path / "not-a-repo"
        not_a_repo.mkdir()
        with pytest.raises(SystemExit) as excinfo:
            agent_run(["env", str(not_a_repo)])
        assert excinfo.value.code == 1

    def test_unrecognized_subcommand_falls_through_to_usage_error(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        # frob:tests tests/test_worktree_guard.py::TestAgentRunnerEnv.test_unrecognized_subcommand_falls_through_to_usage_error  # noqa: E501
        # T-1400: `run()`'s fallthrough (agent_runner.py 88-89) -- no
        # subcommand at all (argparse's `agent_command` stays `None`)
        # prints help to stderr and exits 1, instead of silently doing
        # nothing.
        with pytest.raises(SystemExit) as excinfo:
            agent_run([])
        assert excinfo.value.code == 1
        err = capsys.readouterr().err
        assert "usage" in err.lower()


class TestStashGuardHook:
    """T-0574: the scaffold-managed `reference-transaction` hook that
    mechanically refuses `git stash` while sibling worktrees exist for the
    clone (docs/guides/agent-playbook.md#1b). `reference-transaction` is
    used (not an `alias.stash` override, and not the T-0431 `pre-commit`
    hooks) because both alternatives were verified NOT to intercept
    `git stash` at all -- see `frob.scaffold._managed`'s module-level
    comment for the empirical detail."""

    def test_refuses_stash_while_sibling_worktree_exists(self, tmp_path: Path) -> None:
        # frob:tests tests/test_worktree_guard.py::TestStashGuardHook.test_refuses_stash_while_sibling_worktree_exists  # noqa: E501
        main_repo = tmp_path / "main"
        _init_repo(main_repo)
        assert _apply_stash_guard(main_repo).startswith(
            "hook reference-transaction: installed"
        )
        _git("worktree", "add", "-b", "feature", str(tmp_path / "wt"), cwd=main_repo)

        (main_repo / "tickets.md").write_text("# Tickets\n\nchanged\n")
        result = subprocess.run(
            ["git", "stash"], cwd=main_repo, capture_output=True, text=True
        )
        assert result.returncode != 0
        assert "refusing 'git stash'" in result.stderr

    def test_allows_stash_with_no_sibling_worktree(self, tmp_path: Path) -> None:
        # frob:tests tests/test_worktree_guard.py::TestStashGuardHook.test_allows_stash_with_no_sibling_worktree  # noqa: E501
        main_repo = tmp_path / "main"
        _init_repo(main_repo)
        _apply_stash_guard(main_repo)

        (main_repo / "tickets.md").write_text("# Tickets\n\nchanged\n")
        result = subprocess.run(
            ["git", "stash"], cwd=main_repo, capture_output=True, text=True
        )
        assert result.returncode == 0

    def test_commit_is_unaffected_by_the_hook(self, tmp_path: Path) -> None:
        # frob:tests tests/test_worktree_guard.py::TestStashGuardHook.test_commit_is_unaffected_by_the_hook  # noqa: E501
        main_repo = tmp_path / "main"
        _init_repo(main_repo)
        _apply_stash_guard(main_repo)
        _git("worktree", "add", "-b", "feature", str(tmp_path / "wt"), cwd=main_repo)

        (main_repo / "tickets.md").write_text("# Tickets\n\nchanged\n")
        _git("add", "-A", cwd=main_repo)
        result = subprocess.run(
            ["git", "commit", "-m", "test"], cwd=main_repo, capture_output=True
        )
        assert result.returncode == 0

    def test_idempotent_second_apply_is_noop(self, tmp_path: Path) -> None:
        # frob:tests tests/test_worktree_guard.py::TestStashGuardHook.test_idempotent_second_apply_is_noop  # noqa: E501
        main_repo = tmp_path / "main"
        _init_repo(main_repo)
        _apply_stash_guard(main_repo)
        assert (
            _apply_stash_guard(main_repo)
            == "hook reference-transaction: already current"
        )


def _proc_test_cwd_matches(pid: int, expected: Path) -> bool:
    """`True` iff `/proc/<pid>/cwd` resolves to `expected` (test-only
    startup-race helper, same shape as `test_ticket_leases.py`'s own)."""
    try:
        return Path(os.readlink(f"/proc/{pid}/cwd")).resolve() == expected.resolve()
    except OSError:
        return False


class TestSweepWorktreesLiveProcess:
    """T-1739: `frob worktree sweep` must not remove a worktree a live
    process is cwd'd into, no matter how removable the dirty/lease/age
    proxies say it looks. Real 2026-08-07 dry-run: three LIVE agents'
    worktrees were CLEAN (they had committed their own work-in-progress
    as this repo's own stall-insurance guidance instructs), held no
    lease, and had a recent HEAD commit -- exactly the shape that used
    to read as `removed`. This is that exact shape, reproduced."""

    def test_clean_no_lease_recent_head_live_process_kept(self, tmp_path: Path) -> None:
        # frob:tests tests/test_worktree_guard.py::TestSweepWorktreesLiveProcess.test_clean_no_lease_recent_head_live_process_kept  # noqa: E501
        main_repo = tmp_path / "main"
        _init_repo(main_repo)
        wt = tmp_path / "main" / ".claude" / "worktrees" / "agent-live"
        wt.parent.mkdir(parents=True, exist_ok=True)
        _git("worktree", "add", "-b", "agent-live", str(wt), cwd=main_repo)
        # CLEAN (nothing uncommitted), NO lease recorded, RECENT HEAD --
        # every proxy this repo used to trust says "safe to remove".
        holder = subprocess.Popen(
            ["python3", "-c", "import time; time.sleep(30)"], cwd=str(wt)
        )
        try:
            for _ in range(50):
                if _proc_test_cwd_matches(holder.pid, wt):
                    break
                time.sleep(0.1)

            result = sweep_worktrees(main_repo, dry_run=True)
            assert result.is_ok
            verdicts = result.danger_ok
            assert len(verdicts) == 1
            assert verdicts[0].verdict == "kept:live"
            assert str(holder.pid) in verdicts[0].detail
            assert wt.exists()

            # A real (non-dry-run) sweep must keep it too, not just the
            # preview.
            result2 = sweep_worktrees(main_repo)
            assert result2.is_ok
            assert result2.danger_ok[0].verdict == "kept:live"
            assert wt.exists()
        finally:
            holder.kill()
            holder.wait(timeout=5)

    def test_force_overrides_the_live_process_keep(self, tmp_path: Path) -> None:
        # frob:tests tests/test_worktree_guard.py::TestSweepWorktreesLiveProcess.test_force_overrides_the_live_process_keep  # noqa: E501
        main_repo = tmp_path / "main"
        _init_repo(main_repo)
        wt = tmp_path / "main" / ".claude" / "worktrees" / "agent-live"
        wt.parent.mkdir(parents=True, exist_ok=True)
        _git("worktree", "add", "-b", "agent-live", str(wt), cwd=main_repo)
        holder = subprocess.Popen(
            ["python3", "-c", "import time; time.sleep(30)"], cwd=str(wt)
        )
        try:
            for _ in range(50):
                if _proc_test_cwd_matches(holder.pid, wt):
                    break
                time.sleep(0.1)

            result = sweep_worktrees(main_repo, force=True)
            assert result.is_ok
            assert result.danger_ok[0].verdict == "removed"
            assert not wt.exists()
        finally:
            holder.kill()
            holder.wait(timeout=5)
