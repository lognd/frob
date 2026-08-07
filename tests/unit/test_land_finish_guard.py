"""T-1715: `frob ticket land --finish` must refuse to remove a worktree
that is still provably in use, instead of deleting it out from under the
calling agent.

Real incident, 2026-08-06: `--finish` did exactly what its documented
contract says and removed the worktree the calling agent's own process
was still cwd'd into -- every subsequent tool call then failed with "the
isolation worktree appears to have been removed", and the agent could not
be resumed (worktree creation is reserved to whatever spawned it). This
is a footgun specifically because the natural, DOCUMENTED invocation
(dispatch briefs: run `frob ticket land <id> --worktree <your own path>`
from the root checkout) is the one that strands the caller.

Coverage here pins three layers: the shared `/proc` scan primitive
(`scan_for_live_worktree_process`), the lease-liveness helper
(`_live_lease_for_worktree`), the combined refusal
(`refuse_if_worktree_in_use`), `_finish_worktree`'s own wiring of that
refusal (with `--force` as the override), and the CLI's `--force` flag
parsing all the way to `AppConfig.ticket_force`."""

from __future__ import annotations

import argparse
import os
import subprocess
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from frob._cli_parsers._ticket import _add_ticket_land_parser
from frob.app.ticket_runner._land_cmd import _finish_worktree
from frob.tickets._leases import (
    LEASE_TTL_SECONDS,
    WorktreeInUseError,
    _LeaseRecord,
    _live_lease_for_worktree,
    refuse_if_worktree_in_use,
    scan_for_live_worktree_process,
)


def _git(*args: str, cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


# frob:waive DUP001 reason="a minimal git-fixture-repo bootstrap, byte-identical to \
# tests/test_worktree_guard.py::_init_repo and two tests/system/ fixtures by \
# construction (init -b main, set a throwaway identity, seed tickets.md, commit) -- \
# each test module in this repo keeps its own copy of this five-line git bootstrap \
# deliberately (tests/test_ticket_leases.py's own repo fixture is the same shape \
# again), since extracting it into a shared conftest helper would couple \
# otherwise-independent test modules to one import for a helper this small; same \
# disposition every other _init_repo DUP001 in this repo already carries"
def _init_repo(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    _git("init", "-q", "-b", "main", cwd=root)
    _git("config", "user.email", "test@example.com", cwd=root)
    _git("config", "user.name", "Test", cwd=root)
    (root / "tickets.md").write_text("# Tickets\n\n")
    _git("add", "-A", cwd=root)
    _git("commit", "-q", "-m", "init", cwd=root)


# frob:waive WIRE001 reason="shared fixture helper called from every test method in \
# this module (TestScanForLiveWorktreeProcess/TestLiveLeaseForWorktree/ \
# TestRefuseIfWorktreeInUse/TestFinishWorktree) -- test-only by design, same posture \
# as tests/test_ticket_leases.py::_add_agent_worktree, not a genuinely unwired \
# production symbol" follow_up="T-1739"
def _add_worktree(repo: Path, name: str) -> Path:
    wt = repo.parent / f"{repo.name}-{name}"
    _git("worktree", "add", "-b", f"agent-{name}", str(wt), cwd=repo)
    return wt


def _proc_test_cwd_matches(pid: int, expected: Path) -> bool:
    """`True` iff `/proc/<pid>/cwd` resolves to `expected` (test-only
    startup-race helper, same shape as `test_ticket_leases.py`'s own)."""
    try:
        return Path(os.readlink(f"/proc/{pid}/cwd")).resolve() == expected.resolve()
    except OSError:
        return False


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    _init_repo(root)
    return root


class TestScanForLiveWorktreeProcess:
    """The shared `/proc` primitive both T-1715 and T-1739 call."""

    def test_finds_a_process_cwd_into_the_path(self, repo: Path) -> None:
        # frob:tests tests/unit/test_land_finish_guard.py::TestScanForLiveWorktreeProcess.test_finds_a_process_cwd_into_the_path  # noqa: E501
        wt = _add_worktree(repo, "wt1")
        holder = subprocess.Popen(
            ["python3", "-c", "import time; time.sleep(30)"], cwd=str(wt)
        )
        try:
            for _ in range(50):
                if _proc_test_cwd_matches(holder.pid, wt):
                    break
                time.sleep(0.1)
            found = scan_for_live_worktree_process(wt)
            assert found is not None
            pid, _argv = found
            assert pid == holder.pid
        finally:
            holder.kill()
            holder.wait(timeout=5)

    def test_none_when_no_process_matches(self, repo: Path) -> None:
        # frob:tests tests/unit/test_land_finish_guard.py::TestScanForLiveWorktreeProcess.test_none_when_no_process_matches  # noqa: E501
        wt = _add_worktree(repo, "wt1")
        assert scan_for_live_worktree_process(wt) is None


class TestLiveLeaseForWorktree:
    def test_finds_a_live_lease_pinned_to_the_worktree(self, repo: Path) -> None:
        # frob:tests tests/unit/test_land_finish_guard.py::TestLiveLeaseForWorktree.test_finds_a_live_lease_pinned_to_the_worktree  # noqa: E501
        wt = _add_worktree(repo, "wt1")
        record = _LeaseRecord(
            ticket_id="T-0900",
            scope=("src/frob/foo.py",),
            worktree=str(wt),
            branch="agent-wt1",
            recorded_at=datetime.now(UTC).isoformat(),
        )
        found = _live_lease_for_worktree(wt, (record,))
        assert found is not None
        assert found.ticket_id == "T-0900"

    def test_expired_lease_is_not_live(self, repo: Path) -> None:
        # frob:tests tests/unit/test_land_finish_guard.py::TestLiveLeaseForWorktree.test_expired_lease_is_not_live  # noqa: E501
        wt = _add_worktree(repo, "wt1")
        stale = (
            datetime.now(UTC) - timedelta(seconds=LEASE_TTL_SECONDS + 3600)
        ).isoformat()
        record = _LeaseRecord(
            ticket_id="T-0900",
            scope=("src/frob/foo.py",),
            worktree=str(wt),
            branch="agent-wt1",
            recorded_at=stale,
        )
        assert _live_lease_for_worktree(wt, (record,)) is None


class TestRefuseIfWorktreeInUse:
    """The combined T-1715/T-1739 refusal function."""

    def test_refuses_on_a_live_process_and_names_the_pid(
        self, repo: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests tests/unit/test_land_finish_guard.py::TestRefuseIfWorktreeInUse.test_refuses_on_a_live_process_and_names_the_pid  # noqa: E501
        wt = _add_worktree(repo, "wt1")
        holder = subprocess.Popen(
            ["python3", "-c", "import time; time.sleep(30)"], cwd=str(wt)
        )
        try:
            for _ in range(50):
                if _proc_test_cwd_matches(holder.pid, wt):
                    break
                time.sleep(0.1)
            with caplog.at_level("ERROR"):
                result = refuse_if_worktree_in_use(repo, wt)
            assert result.is_err
            assert result.danger_err == WorktreeInUseError.LiveProcess
            assert str(holder.pid) in caplog.text
        finally:
            holder.kill()
            holder.wait(timeout=5)

    def test_refuses_on_a_live_lease(
        self, repo: Path, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_land_finish_guard.py::TestRefuseIfWorktreeInUse.test_refuses_on_a_live_lease  # noqa: E501
        wt = _add_worktree(repo, "wt1")
        from frob.tickets import _leases as leases_mod

        record = _LeaseRecord(
            ticket_id="T-0900",
            scope=("src/frob/foo.py",),
            worktree=str(wt),
            branch="agent-wt1",
            recorded_at=datetime.now(UTC).isoformat(),
        )
        monkeypatch.setattr(leases_mod, "read_all_leases", lambda root: (record,))
        with caplog.at_level("ERROR"):
            result = refuse_if_worktree_in_use(repo, wt)
        assert result.is_err
        assert result.danger_err == WorktreeInUseError.LiveLease
        assert "T-0900" in caplog.text

    def test_allows_when_neither_signal_fires(self, repo: Path) -> None:
        # frob:tests tests/unit/test_land_finish_guard.py::TestRefuseIfWorktreeInUse.test_allows_when_neither_signal_fires  # noqa: E501
        wt = _add_worktree(repo, "wt1")
        assert refuse_if_worktree_in_use(repo, wt).is_ok


class TestFinishWorktree:
    """`_finish_worktree`'s own liveness-refusal wiring."""

    def test_refuses_to_remove_a_worktree_a_live_process_is_cwd_into(
        self, repo: Path
    ) -> None:
        # frob:tests tests/unit/test_land_finish_guard.py::TestFinishWorktree.test_refuses_to_remove_a_worktree_a_live_process_is_cwd_into  # noqa: E501
        wt = _add_worktree(repo, "wt1")
        holder = subprocess.Popen(
            ["python3", "-c", "import time; time.sleep(30)"], cwd=str(wt)
        )
        try:
            for _ in range(50):
                if _proc_test_cwd_matches(holder.pid, wt):
                    break
                time.sleep(0.1)
            with pytest.raises(SystemExit) as excinfo:
                _finish_worktree(repo, wt, "T-1715")
            assert excinfo.value.code == 1
            assert wt.exists()
        finally:
            holder.kill()
            holder.wait(timeout=5)

    def test_removes_a_worktree_with_no_live_process(self, repo: Path) -> None:
        # frob:tests tests/unit/test_land_finish_guard.py::TestFinishWorktree.test_removes_a_worktree_with_no_live_process  # noqa: E501
        wt = _add_worktree(repo, "wt1")
        _finish_worktree(repo, wt, "T-1715")
        assert not wt.exists()

    def test_force_removes_despite_a_live_process(self, repo: Path) -> None:
        # frob:tests tests/unit/test_land_finish_guard.py::TestFinishWorktree.test_force_removes_despite_a_live_process  # noqa: E501
        wt = _add_worktree(repo, "wt1")
        holder = subprocess.Popen(
            ["python3", "-c", "import time; time.sleep(30)"], cwd=str(wt)
        )
        try:
            for _ in range(50):
                if _proc_test_cwd_matches(holder.pid, wt):
                    break
                time.sleep(0.1)
            _finish_worktree(repo, wt, "T-1715", force=True)
            assert not wt.exists()
        finally:
            holder.kill()
            holder.wait(timeout=5)


def _parse(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="frob")
    sub = parser.add_subparsers(dest="ticket_cmd")
    _add_ticket_land_parser(sub)
    return parser.parse_args(argv)


class TestForceFlagParsing:
    # frob:tests src/frob/_cli_parsers/_ticket/_progress.py::_add_ticket_land_parser kind="unit"  # noqa: E501
    def test_force_flag_sets_the_namespace_dest(self) -> None:
        # frob:tests tests/unit/test_land_finish_guard.py::TestForceFlagParsing.test_force_flag_sets_the_namespace_dest  # noqa: E501
        args = _parse(
            ["land", "T-1715", "--worktree", "/tmp/wt", "--finish", "--force"]
        )
        assert args.ticket_force is True

    def test_force_defaults_false(self) -> None:
        # frob:tests tests/unit/test_land_finish_guard.py::TestForceFlagParsing.test_force_defaults_false  # noqa: E501
        args = _parse(["land", "T-1715", "--worktree", "/tmp/wt", "--finish"])
        assert args.ticket_force is False
