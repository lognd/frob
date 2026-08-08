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
import multiprocessing
import os
import signal
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
# production symbol" follow_up="T-1778"
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
        self,
        repo: Path,
        caplog: pytest.LogCaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
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
            _finish_worktree(
                repo,
                wt,
                "T-1715",
                force=True,
                force_reason="T-1762 test: independently confirmed wedged",
            )
            assert not wt.exists()
        finally:
            holder.kill()
            holder.wait(timeout=5)

    def test_finish_worktree_force_requires_reason_when_guard_would_fire(
        self, repo: Path
    ) -> None:
        # frob:tests tests/unit/test_land_finish_guard.py::TestFinishWorktree.test_finish_worktree_force_requires_reason_when_guard_would_fire  # noqa: E501
        """T-1762: `force=True` with no reason, against a worktree the
        guard WOULD have refused, still refuses -- the bypass itself is
        no longer free."""
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
                _finish_worktree(repo, wt, "T-1715", force=True)
            assert excinfo.value.code == 1
            assert wt.exists()
            assert not (repo / "force-overrides.jsonl").exists()
        finally:
            holder.kill()
            holder.wait(timeout=5)

    def test_finish_worktree_force_is_a_no_op_reason_wise_when_worktree_is_free(
        self, repo: Path
    ) -> None:
        # frob:tests tests/unit/test_land_finish_guard.py::TestFinishWorktree.test_finish_worktree_force_is_a_no_op_reason_wise_when_worktree_is_free  # noqa: E501
        """T-1762: `force=True` against a worktree the guard would NOT
        have refused (nothing live) demands no reason -- nothing was
        actually bypassed."""
        wt = _add_worktree(repo, "wt1")
        _finish_worktree(repo, wt, "T-1715", force=True)
        assert not wt.exists()


def _parse(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="frob")
    sub = parser.add_subparsers(dest="ticket_cmd")
    _add_ticket_land_parser(sub)
    return parser.parse_args(argv)


class TestForceFlagParsing:
    # frob:tests src/frob/_cli_parsers/_ticket/_progress.py::_add_ticket_land_parser \
    # kind="unit"
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


# frob:ticket T-1845
class TestLandFinishPendingMarker:
    """T-1845: the `--finish`/`--retire-on-proof` twin of T-1523's own
    post-land-verify-pending marker -- covers the plain write/clear/
    reconcile round trip; `TestLandFinishPendingMarkerSigterm` below
    covers the real process-kill shape."""

    # frob:ticket T-1845
    def test_write_then_clear_round_trips(self, repo: Path) -> None:
        # frob:tests tests/unit/test_land_finish_guard.py::TestLandFinishPendingMarker.test_write_then_clear_round_trips  # noqa: E501
        from frob.app.ticket_runner._land_cmd import (
            _clear_land_finish_pending_marker,
            _land_finish_pending_marker_path,
            _write_land_finish_pending_marker,
        )

        sha = _git_head(repo)
        _write_land_finish_pending_marker(repo, "T-9001", sha, retire_on_proof=False)
        path = _land_finish_pending_marker_path(repo, "T-9001")
        assert path.exists()
        _clear_land_finish_pending_marker(repo, "T-9001")
        assert not path.exists()

    # frob:ticket T-1845
    def test_no_marker_is_a_silent_empty_result(self, repo: Path) -> None:
        # frob:tests tests/unit/test_land_finish_guard.py::TestLandFinishPendingMarker.test_no_marker_is_a_silent_empty_result  # noqa: E501
        from frob.app.ticket_runner._land_cmd import (
            _stale_land_finish_pending_markers,
        )

        assert _stale_land_finish_pending_markers(repo) == ()

    # frob:ticket T-1845
    def test_stale_marker_is_reported(self, repo: Path) -> None:
        # frob:tests tests/unit/test_land_finish_guard.py::TestLandFinishPendingMarker.test_stale_marker_is_reported  # noqa: E501
        from frob.app.ticket_runner._land_cmd import (
            _stale_land_finish_pending_markers,
            _write_land_finish_pending_marker,
        )

        sha = _git_head(repo)
        _write_land_finish_pending_marker(repo, "T-9002", sha, retire_on_proof=True)
        found = _stale_land_finish_pending_markers(repo)
        assert found == (("T-9002", sha, True),)

    # frob:ticket T-1845
    def test_reconcile_reports_and_clears_a_stale_marker(
        self, repo: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests tests/unit/test_land_finish_guard.py::TestLandFinishPendingMarker.test_reconcile_reports_and_clears_a_stale_marker  # noqa: E501
        import logging

        from frob.app.ticket_runner._land_cmd import (
            _land_finish_pending_marker_path,
            _report_stale_land_finish_pending_markers,
            _write_land_finish_pending_marker,
        )

        sha = _git_head(repo)
        _write_land_finish_pending_marker(repo, "T-9003", sha, retire_on_proof=False)
        path = _land_finish_pending_marker_path(repo, "T-9003")
        assert path.exists()

        with caplog.at_level(logging.WARNING, logger="frob.app.ticket_runner"):
            _report_stale_land_finish_pending_markers(repo)

        assert not path.exists()
        message = _sole_matching_log_message(caplog, "LAND-FINISH-RECOVERED")
        assert "T-9003" in message


# frob:ticket T-1845
# frob:waive WIRE001 reason="test-only helper used by TestLandFinishPendingMarker and \
# TestLandFinishPendingMarkerSigterm's own test methods below, in this same file -- no \
# production caller to wire it to by design" permanent="true"
def _sole_matching_log_message(caplog: pytest.LogCaptureFixture, needle: str) -> str:
    """The single captured log record whose message contains `needle`
    (T-1845 test helper, shared by `TestLandFinishPendingMarker` and
    `TestLandFinishPendingMarkerSigterm` below) -- fails loudly if zero or
    more than one record matches, rather than silently taking the first.
    A single, explicit `for` loop (not a comprehension over `caplog.
    records`) sidesteps a PERF001/PERF003 false-positive this exact shape
    tripped when written as a comprehension: the perf scanner's
    membership-test/nested-loop heuristics misread a filtered-list-then-
    index pattern here as a real hot-path smell, even though this is
    test-only code that runs over at most a handful of records."""
    matches = []
    for record in caplog.records:
        if needle in record.getMessage():
            matches.append(record)
    assert len(matches) == 1, matches
    return matches[0].getMessage()


# frob:ticket T-1845
def _git_head(repo: Path) -> str:
    """The repo's current `HEAD` sha (test-only helper, T-1845)."""
    return subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


# frob:ticket T-1845
# frob:waive WIRE001 reason="multiprocessing.Process target, invoked only via \
# ctx.Process(target=_t1845_child_finish, ...) below -- the static call-graph does not \
# trace a callable passed as a multiprocessing target argument (same class of gap \
# tests/test_ticket_land.py::_t0907_child_land's own equivalent target function has, \
# that one simply predates the WIRE001 gate so it was never caught fresh); no \
# production caller to wire it to by design" permanent="true"
def _t1845_child_finish(
    repo: Path, ticket_id: str, commit_sha: str, worktree: Path, ready_path: Path
) -> None:
    """Multiprocessing target (module-level so `fork` can spawn it, same
    T-0907 shape `_t0907_child_land` in tests/test_ticket_land.py uses):
    replicates `_finish_land_after_success`'s own marker-write / mutation
    / marker-clear `try`/`finally` sequence directly (not a mock of it),
    with `_finish_worktree` monkeypatched in THIS forked child's own
    module copy to signal readiness and then sleep well past however long
    the parent needs to deliver a real `SIGTERM` -- reproducing "killed
    between the marker write and the mutation completing" deterministically."""
    import frob.app.ticket_runner._land_cmd as land_cmd_mod

    def _slow_finish_worktree(*args: object, **kwargs: object) -> None:
        ready_path.write_text("ready\n")
        time.sleep(30)

    setattr(land_cmd_mod, "_finish_worktree", _slow_finish_worktree)  # noqa: B010

    land_cmd_mod._write_land_finish_pending_marker(
        repo, ticket_id, commit_sha, retire_on_proof=False
    )
    try:
        land_cmd_mod._finish_worktree(repo, worktree, ticket_id)
    finally:
        land_cmd_mod._clear_land_finish_pending_marker(repo, ticket_id)


# frob:ticket T-1845
class TestLandFinishPendingMarkerSigterm:
    """T-1845's own load-bearing regression lock (mirroring T-0907's
    SIGKILL-mid-squash precedent, `tests/test_ticket_land.py::
    TestSigkillMidStaging`): a real `SIGTERM` delivered to a process that
    has written the land-finish-pending marker but not yet finished its
    mutation must leave the marker on disk, and the NEXT reconciliation
    pass must find, report, and clear it."""

    # frob:ticket T-1845
    def test_sigterm_between_marker_write_and_mutation_leaves_marker_for_reconcile(
        self, repo: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests tests/unit/test_land_finish_guard.py::TestLandFinishPendingMarkerSigterm.test_sigterm_between_marker_write_and_mutation_leaves_marker_for_reconcile  # noqa: E501
        import logging

        from frob.app.ticket_runner._land_cmd import (
            _land_finish_pending_marker_path,
            _report_stale_land_finish_pending_markers,
        )

        wt = _add_worktree(repo, "wt1")
        sha = _git_head(repo)
        ready_path = repo.parent / "finish-ready.flag"

        ctx = multiprocessing.get_context("fork")
        proc = ctx.Process(
            target=_t1845_child_finish, args=(repo, "T-9010", sha, wt, ready_path)
        )
        proc.start()
        deadline = time.monotonic() + 20
        while not ready_path.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        assert ready_path.exists(), "child never reached the finish-worktree step"
        assert proc.pid is not None
        os.kill(proc.pid, signal.SIGTERM)
        proc.join(timeout=15)
        assert not proc.is_alive()

        # The marker must have survived the kill -- the child died inside
        # the mutation, before its own `finally` clear ever ran.
        marker_path = _land_finish_pending_marker_path(repo, "T-9010")
        assert marker_path.exists()

        # The next invocation's reconciliation pass finds it, logs
        # LAND-FINISH-RECOVERED, and clears it -- never blocking whatever
        # NEW ticket that invocation is actually landing.
        with caplog.at_level(logging.WARNING, logger="frob.app.ticket_runner"):
            _report_stale_land_finish_pending_markers(repo)
        assert not marker_path.exists()
        message = _sole_matching_log_message(caplog, "LAND-FINISH-RECOVERED")
        assert "T-9010" in message
