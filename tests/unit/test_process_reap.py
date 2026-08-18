"""Tests for `frob.process._reap` (T-2443): SIGTERM-safe reaping of leaked
`multiprocessing` forkserver/worker processes.
"""

from __future__ import annotations

import multiprocessing
import os
import signal
import time
from pathlib import Path

import pytest

from frob.process import _reap
from frob.process._reap import (
    _is_orphaned_forkserver,
    _process_start_age_s,
    count_running_checks,
    install_sigterm_reaper,
    reap_active_multiprocessing_children,
    reap_orphaned_forkservers,
)


def _sleep_forever() -> None:
    """Multiprocessing worker target: a plain, terminate()-able sleep."""
    time.sleep(30)


def _ignore_sigterm_and_sleep() -> None:
    """Multiprocessing worker target that survives `terminate()` (SIGTERM)
    so a test can exercise the kill() escalation path deterministically."""
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    time.sleep(30)


class TestReapActiveChildren:
    """`reap_active_multiprocessing_children` must not leave a lingering
    `multiprocessing.active_children()` process behind -- the same
    real-world defect shape T-1378 fixed for the socket daemon, generalized
    here into the shared primitive both callers use."""

    def test_terminates_and_joins_active_children(self) -> None:
        proc = multiprocessing.Process(target=_sleep_forever, daemon=False)
        proc.start()
        try:
            assert proc in multiprocessing.active_children()
            reaped = reap_active_multiprocessing_children()
            proc.join(timeout=5)
            assert not proc.is_alive()
            assert multiprocessing.active_children() == []
            assert proc.pid in reaped
        finally:
            if proc.is_alive():
                proc.kill()
                proc.join(timeout=5)

    def test_escalates_to_kill_if_terminate_does_not_stick(self) -> None:
        proc = multiprocessing.Process(target=_ignore_sigterm_and_sleep, daemon=False)
        proc.start()
        try:
            deadline = time.monotonic() + 5
            while proc.pid is None and time.monotonic() < deadline:
                time.sleep(0.02)
            assert proc in multiprocessing.active_children()
            reaped = reap_active_multiprocessing_children(grace_s=0.2)
            proc.join(timeout=5)
            assert not proc.is_alive()
            assert multiprocessing.active_children() == []
            assert proc.pid in reaped
        finally:
            if proc.is_alive():
                proc.kill()
                proc.join(timeout=5)

    def test_no_children_is_a_silent_noop(self) -> None:
        assert multiprocessing.active_children() == []
        assert reap_active_multiprocessing_children() == []


class TestInstallSigtermReaper:
    """`install_sigterm_reaper` (T-2443) installs exactly once, chaining to
    whatever handler was previously registered."""

    def test_installs_handler_once(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(_reap, "_sigterm_reaper_installed", False)
        monkeypatch.setattr(_reap, "_prior_sigterm_handler", None)
        prior = signal.getsignal(signal.SIGTERM)
        try:
            install_sigterm_reaper()
            assert signal.getsignal(signal.SIGTERM) is _reap._sigterm_handler
            assert _reap._sigterm_reaper_installed is True
        finally:
            signal.signal(signal.SIGTERM, prior)

    def test_second_call_is_a_noop(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(_reap, "_sigterm_reaper_installed", False)
        monkeypatch.setattr(_reap, "_prior_sigterm_handler", None)
        prior = signal.getsignal(signal.SIGTERM)
        try:
            install_sigterm_reaper()
            installed_handler = signal.getsignal(signal.SIGTERM)
            install_sigterm_reaper()
            assert signal.getsignal(signal.SIGTERM) is installed_handler
        finally:
            signal.signal(signal.SIGTERM, prior)


def _write_proc_entry(
    proc: Path,
    pid: int,
    *,
    cmdline: bytes,
    ppid: int,
    mtime_offset_s: float = 0.0,
) -> None:
    """Build a fake `<proc>/<pid>/{cmdline,stat}` pair matching real
    `/proc`'s own shape closely enough for `_is_orphaned_forkserver`/
    `_process_start_age_s` to parse: `cmdline` is NUL-separated (real
    kernel shape), `stat`'s ppid sits right after the parenthesized comm
    field (real `/proc/<pid>/stat` shape, `man proc`)."""
    entry = proc / str(pid)
    entry.mkdir(parents=True)
    (entry / "cmdline").write_bytes(cmdline)
    (entry / "stat").write_text(f"{pid} (python3) S {ppid} {pid} 0 0 -1 0\n")
    if mtime_offset_s:
        now = time.time()
        os.utime(entry, (now - mtime_offset_s, now - mtime_offset_s))


class TestIsOrphanedForkserver:
    """`_is_orphaned_forkserver` must match forkserver cmdline + ppid==1,
    and nothing else."""

    def test_matches_forkserver_reparented_to_init(self, tmp_path: Path) -> None:
        _write_proc_entry(
            tmp_path,
            4242,
            cmdline=b"python3\x00-c\x00from multiprocessing.forkserver import main; main(...)\x00",
            ppid=1,
        )
        assert _is_orphaned_forkserver(4242, tmp_path) is True

    def test_forkserver_with_live_parent_is_not_orphaned(self, tmp_path: Path) -> None:
        _write_proc_entry(
            tmp_path,
            4242,
            cmdline=b"python3\x00-c\x00from multiprocessing.forkserver import main; main(...)\x00",
            ppid=999,
        )
        assert _is_orphaned_forkserver(4242, tmp_path) is False

    def test_non_forkserver_process_is_never_matched(self, tmp_path: Path) -> None:
        _write_proc_entry(tmp_path, 4242, cmdline=b"sleep\x0030\x00", ppid=1)
        assert _is_orphaned_forkserver(4242, tmp_path) is False

    def test_missing_entry_is_false_not_raised(self, tmp_path: Path) -> None:
        assert _is_orphaned_forkserver(999999, tmp_path) is False


class TestReapOrphanedForkservers:
    """`reap_orphaned_forkservers` (T-2443's defensive startup sweep) only
    signals a forkserver that is BOTH reparented to init AND older than the
    age floor -- never a young one, never a non-forkserver process."""

    def test_terminates_old_orphaned_forkservers(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_proc_entry(
            tmp_path,
            4242,
            cmdline=b"python3\x00-c\x00from multiprocessing.forkserver import main; main(...)\x00",
            ppid=1,
            mtime_offset_s=600.0,
        )
        killed: list[tuple[int, int]] = []
        monkeypatch.setattr(
            _reap.os, "kill", lambda pid, sig: killed.append((pid, sig))
        )
        reaped = reap_orphaned_forkservers(age_floor_s=300.0, proc=tmp_path)
        assert reaped == [4242]
        assert killed == [(4242, signal.SIGTERM)]

    def test_leaves_young_orphaned_forkservers_alone(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_proc_entry(
            tmp_path,
            4242,
            cmdline=b"python3\x00-c\x00from multiprocessing.forkserver import main; main(...)\x00",
            ppid=1,
            mtime_offset_s=5.0,
        )
        killed: list[tuple[int, int]] = []
        monkeypatch.setattr(
            _reap.os, "kill", lambda pid, sig: killed.append((pid, sig))
        )
        reaped = reap_orphaned_forkservers(age_floor_s=300.0, proc=tmp_path)
        assert reaped == []
        assert killed == []

    def test_leaves_non_forkserver_processes_alone(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_proc_entry(
            tmp_path, 4242, cmdline=b"sleep\x00600\x00", ppid=1, mtime_offset_s=600.0
        )
        killed: list[tuple[int, int]] = []
        monkeypatch.setattr(
            _reap.os, "kill", lambda pid, sig: killed.append((pid, sig))
        )
        reaped = reap_orphaned_forkservers(age_floor_s=300.0, proc=tmp_path)
        assert reaped == []
        assert killed == []

    def test_missing_proc_returns_empty(self, tmp_path: Path) -> None:
        assert reap_orphaned_forkservers(proc=tmp_path / "does-not-exist") == []


class TestProcessStartAge:
    """`_process_start_age_s` approximates process age from the `/proc/<pid>`
    directory's own mtime."""

    def test_reads_age_from_mtime(self, tmp_path: Path) -> None:
        _write_proc_entry(
            tmp_path, 4242, cmdline=b"x\x00", ppid=1, mtime_offset_s=120.0
        )
        age = _process_start_age_s(4242, tmp_path, time.time())
        assert age is not None
        assert 110.0 < age < 130.0

    def test_missing_entry_returns_none(self, tmp_path: Path) -> None:
        assert _process_start_age_s(999999, tmp_path, time.time()) is None


# frob:ticket T-2473
class TestCountRunningChecks:
    """`count_running_checks` -- T-2473's advisory concurrent-check
    counter: matches a live `frob check` process by its `frob`/`check`
    argv token pair, excludes the caller's own pid, degrades to `None`
    on an unreadable `/proc`."""

    def test_counts_other_check_processes(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_process_reap.py::TestCountRunningChecks.test_counts_other_check_processes  # noqa: E501
        _write_proc_entry(
            tmp_path, 100, cmdline=b"/home/x/.venv/bin/frob\x00check\x00", ppid=1
        )
        _write_proc_entry(
            tmp_path, 101, cmdline=b"frob\x00check\x00--json\x00", ppid=1
        )
        assert count_running_checks(proc=tmp_path, self_pid=1) == 2

    def test_excludes_self(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_process_reap.py::TestCountRunningChecks.test_excludes_self  # noqa: E501
        _write_proc_entry(tmp_path, 200, cmdline=b"frob\x00check\x00", ppid=1)
        assert count_running_checks(proc=tmp_path, self_pid=200) == 0

    def test_ignores_non_check_processes(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_process_reap.py::TestCountRunningChecks.test_ignores_non_check_processes  # noqa: E501
        # A different frob subcommand -- must NOT count as a check.
        _write_proc_entry(tmp_path, 300, cmdline=b"frob\x00ticket\x00land\x00", ppid=1)
        # A path containing "check" as a substring of a longer word, not
        # a whole argv token -- must NOT count either.
        _write_proc_entry(
            tmp_path, 301, cmdline=b"frob\x00checkpointer\x00", ppid=1
        )
        # "check" present but no "frob" token at all.
        _write_proc_entry(tmp_path, 302, cmdline=b"pytest\x00check\x00", ppid=1)
        assert count_running_checks(proc=tmp_path, self_pid=1) == 0

    def test_missing_proc_returns_none(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_process_reap.py::TestCountRunningChecks.test_missing_proc_returns_none  # noqa: E501
        assert count_running_checks(proc=tmp_path / "does-not-exist") is None
