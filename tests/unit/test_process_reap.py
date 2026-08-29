"""Tests for `frob.process._reap` (T-2443): SIGTERM-safe reaping of leaked
`multiprocessing` forkserver/worker processes.
"""

from __future__ import annotations

import multiprocessing
import os
import signal
import sys
import time
from pathlib import Path

import pytest

from frob.process import _reap
from frob.process._reap import (
    FORKSERVER_ARM_PDEATHSIG_ENV,
    _all_process_ppids,
    _arm_forkserver_helper_pdeathsig_if_requested,
    _forkserver_root_is_live_check,
    _is_live_check_process,
    _is_orphaned_forkserver,
    _process_start_age_s,
    arm_parent_death_signal,
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


# frob:ticket T-3152
#: Fixed `/proc/uptime`/clock-tick baseline every `_write_proc_entry` fake
#: `stat` starttime is computed against, so `age_s` below (and any test
#: reading `_process_start_age_s`/`reap_orphaned_forkservers` against this
#: fixture) gets a deterministic, host-independent age regardless of when
#: the test actually runs -- real `os.sysconf("SC_CLK_TCK")` is (almost)
#: universally 100 on Linux, matched here exactly so a real host would
#: reproduce the same numbers.
_FAKE_UPTIME_S = 1_000_000.0
_FAKE_CLK_TCK = 100


def _write_proc_entry(
    proc: Path,
    pid: int,
    *,
    cmdline: bytes,
    ppid: int,
    age_s: float = 0.0,
) -> None:
    """Build a fake `<proc>/<pid>/{cmdline,stat}` pair (plus a shared
    `<proc>/uptime`) matching real `/proc`'s own shape closely enough for
    `_is_orphaned_forkserver`/`_process_start_age_s` to parse: `cmdline`
    is NUL-separated (real kernel shape), `stat`'s fields sit after the
    parenthesized comm field exactly as `man proc` documents -- ppid at
    index 1, `starttime` (clock ticks since boot) at index 19, both after
    `_stat_fields_after_comm`'s split.

    T-3152: `age_s` (renamed from `mtime_offset_s`) now controls the fake
    `starttime` field, computed against the shared `_FAKE_UPTIME_S`/
    `_FAKE_CLK_TCK` baseline (written to `<proc>/uptime` once, idempotent
    across repeat calls for the same `proc`) -- `_process_start_age_s`
    stopped reading the entry directory's own mtime."""
    entry = proc / str(pid)
    entry.mkdir(parents=True)
    (entry / "cmdline").write_bytes(cmdline)
    starttime_ticks = int((_FAKE_UPTIME_S - age_s) * _FAKE_CLK_TCK)
    filler = " ".join(["0"] * 12)
    stat_line = f"{pid} (python3) S {ppid} {pid} 0 0 -1 0 {filler} {starttime_ticks}\n"
    (entry / "stat").write_text(stat_line)
    uptime_path = proc / "uptime"
    if not uptime_path.exists():
        uptime_path.write_text(f"{_FAKE_UPTIME_S} 0.0\n")


# frob:ticket T-3191
class TestReadUptimeAndClkTck:
    """T-3191: `os.sysconf` is POSIX-only (typeshed declares it under
    `if sys.platform != "win32":`) -- these are the must-fire/must-stay-
    quiet pair for the `sys.platform != "win32"` guard `_read_uptime_and_
    clk_tck` now uses instead of a bare unconditional call."""

    def test_win32_skips_sysconf_and_uses_fallback(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # MUST-FIRE: on a win32 host, `os.sysconf` is never called at all
        # (it doesn't exist there) -- `clk_tck` must still come back as
        # the documented 100 fallback rather than raising.
        # frob:tests src/frob/process/_proc_scan.py::_read_uptime_and_clk_tck \
        # kind="unit"
        monkeypatch.setattr(_reap.sys, "platform", "win32")

        def _boom(*a, **kw):
            raise AssertionError("os.sysconf must not be called on win32")

        monkeypatch.setattr(_reap.os, "sysconf", _boom, raising=False)
        _write_proc_entry(tmp_path, pid=1, cmdline=b"x\x00", ppid=0)
        _, clk_tck = _reap._read_uptime_and_clk_tck(tmp_path)
        assert clk_tck == 100

    def test_non_win32_still_reads_sysconf(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # MUST-STAY-QUIET: on every other platform, behavior is unchanged
        # -- `os.sysconf` is still consulted (falling back to 100 only on
        # its own documented failure).
        # frob:tests src/frob/process/_proc_scan.py::_read_uptime_and_clk_tck \
        # kind="unit"
        monkeypatch.setattr(_reap.sys, "platform", "linux")
        monkeypatch.setattr(_reap.os, "sysconf", lambda name: 250, raising=False)
        _write_proc_entry(tmp_path, pid=1, cmdline=b"x\x00", ppid=0)
        _, clk_tck = _reap._read_uptime_and_clk_tck(tmp_path)
        assert clk_tck == 250


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
            age_s=600.0,
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
            age_s=5.0,
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
            tmp_path, 4242, cmdline=b"sleep\x00600\x00", ppid=1, age_s=600.0
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

    def test_forkserver_of_orphaned_forkserver_is_reaped(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_process_reap.py::TestReapOrphanedForkservers.test_forkserver_of_orphaned_forkserver_is_reaped  # noqa: E501
        """T-3072 must-fire: a forkserver (4242) whose parent is ANOTHER
        forkserver (5000) whose own originating check already died
        (reparented to init) -- the one-hop check this replaced read 4242
        as 'live-parented' because 5000 is alive; the multi-hop ancestry
        walk must reap BOTH."""
        _write_proc_entry(
            tmp_path,
            5000,
            cmdline=_FORKSERVER_CMDLINE,
            ppid=1,
            age_s=600.0,
        )
        _write_proc_entry(
            tmp_path,
            4242,
            cmdline=_FORKSERVER_CMDLINE,
            ppid=5000,
            age_s=600.0,
        )
        killed: list[tuple[int, int]] = []
        monkeypatch.setattr(
            _reap.os, "kill", lambda pid, sig: killed.append((pid, sig))
        )
        reaped = reap_orphaned_forkservers(age_floor_s=300.0, proc=tmp_path)
        assert set(reaped) == {5000, 4242}

    def test_forkserver_under_a_live_check_is_never_reaped(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_process_reap.py::TestReapOrphanedForkservers.test_forkserver_under_a_live_check_is_never_reaped  # noqa: E501
        """T-3072 MUST-STAY-QUIET, the one that matters most: a forkserver
        several hops below a genuinely running `frob check` -- invoked the
        fleet's own dominant way, `python -m frob check ...` (T-3072's
        live-fleet evidence: this exact shape is what `scripts/fleet_
        status.py`'s buggy classifier falsely reported orphaned) -- must
        never be reaped, at any depth, even though it is old enough and
        every intermediate hop is itself a forkserver."""
        _write_live_check_entry(tmp_path, 6000, cmdline=_MODULE_INVOKED_CHECK_CMDLINE)
        _write_proc_entry(
            tmp_path,
            5000,
            cmdline=_FORKSERVER_CMDLINE,
            ppid=6000,
            age_s=600.0,
        )
        _write_proc_entry(
            tmp_path,
            4242,
            cmdline=_FORKSERVER_CMDLINE,
            ppid=5000,
            age_s=600.0,
        )
        killed: list[tuple[int, int]] = []
        monkeypatch.setattr(
            _reap.os, "kill", lambda pid, sig: killed.append((pid, sig))
        )
        reaped = reap_orphaned_forkservers(age_floor_s=300.0, proc=tmp_path)
        assert reaped == []
        assert killed == []


_FORKSERVER_CMDLINE = (
    b"python3\x00-c\x00from multiprocessing.forkserver import main; main(...)\x00"
)
#: T-3072: the fleet's own dominant invocation shape -- `python -m frob
#: check ...` -- where the literal `frob` argv token is neither the first
#: token nor preceded by a `/`. `scripts/fleet_status.py`'s pre-T-3072
#: classifier (`re.compile(rb"(?:^|/)frob\x00")`) never matched this;
#: `_is_live_check_process`'s whole-token comparison does.
_MODULE_INVOKED_CHECK_CMDLINE = (
    b"/x/.venv/bin/python\x00-m\x00frob\x00check\x00--json\x00--budget\x00300\x00"
)


def _write_live_check_entry(
    proc: Path, pid: int, *, cmdline: bytes, ppid: int = 1
) -> None:
    """`_write_proc_entry` twin for a LIVE `frob check` ancestor (T-3072)
    -- same fake `/proc/<pid>/{cmdline,stat}` shape, distinct helper name
    only so a test reads as "this pid is the live-check root", matching
    `tests/unit/test_coordinator_scripts.py`'s own `_write_live_check`
    naming convention."""
    _write_proc_entry(proc, pid, cmdline=cmdline, ppid=ppid)


class TestIsLiveCheckProcess:
    """`_is_live_check_process` (T-3072): the whole-token classifier that
    replaced this file's own THIRD copy of `scripts/fleet_status.py`'s
    anchor-bugged `(?:^|/)frob\\x00` regex (`_is_frob_check_process` used
    to carry it directly)."""

    def test_matches_module_invoked_check(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_process_reap.py::TestIsLiveCheckProcess.test_matches_module_invoked_check  # noqa: E501
        """The regression case: `python -m frob check ...` -- the
        anchor-bugged regex this replaced never matched a bare `frob`
        token not preceded by `/` and not at cmdline start."""
        _write_proc_entry(tmp_path, 4242, cmdline=_MODULE_INVOKED_CHECK_CMDLINE, ppid=1)
        assert _is_live_check_process(4242, tmp_path) is True

    def test_matches_executable_path_invoked_check(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_process_reap.py::TestIsLiveCheckProcess.test_matches_executable_path_invoked_check  # noqa: E501
        _write_proc_entry(
            tmp_path,
            4242,
            cmdline=b"/x/.venv/bin/frob\x00check\x00--only\x00gates\x00",
            ppid=1,
        )
        assert _is_live_check_process(4242, tmp_path) is True

    def test_does_not_match_unrelated_process(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_process_reap.py::TestIsLiveCheckProcess.test_does_not_match_unrelated_process  # noqa: E501
        _write_proc_entry(tmp_path, 4242, cmdline=b"sleep\x0030\x00", ppid=1)
        assert _is_live_check_process(4242, tmp_path) is False

    def test_does_not_match_check_repro_subcommand(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_process_reap.py::TestIsLiveCheckProcess.test_does_not_match_check_repro_subcommand  # noqa: E501
        """Must not fire on a DIFFERENT ticket subcommand that merely
        contains the substring 'check' -- token equality, never a
        substring match."""
        _write_proc_entry(
            tmp_path,
            4242,
            cmdline=b"frob\x00ticket\x00check-repro\x00T-1\x00",
            ppid=1,
        )
        assert _is_live_check_process(4242, tmp_path) is False


class TestForkserverRootIsLiveCheck:
    """`_forkserver_root_is_live_check` (T-3072): the multi-hop ancestry
    walk `reap_orphaned_forkservers` now uses instead of a one-hop
    `ppid == 1` test."""

    def test_direct_child_of_live_check_is_not_orphaned(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_process_reap.py::TestForkserverRootIsLiveCheck.test_direct_child_of_live_check_is_not_orphaned  # noqa: E501
        _write_live_check_entry(tmp_path, 999, cmdline=_MODULE_INVOKED_CHECK_CMDLINE)
        _write_proc_entry(tmp_path, 4242, cmdline=_FORKSERVER_CMDLINE, ppid=999)
        ppid_map = _all_process_ppids(tmp_path)
        live = {p for p in ppid_map if _is_live_check_process(p, tmp_path)}
        assert _forkserver_root_is_live_check(4242, ppid_map, live) is True

    def test_orphaned_forkserver_of_forkserver_is_orphaned(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/test_process_reap.py::TestForkserverRootIsLiveCheck.test_orphaned_forkserver_of_forkserver_is_orphaned  # noqa: E501
        _write_proc_entry(tmp_path, 5000, cmdline=_FORKSERVER_CMDLINE, ppid=1)
        _write_proc_entry(tmp_path, 4242, cmdline=_FORKSERVER_CMDLINE, ppid=5000)
        ppid_map = _all_process_ppids(tmp_path)
        live = {p for p in ppid_map if _is_live_check_process(p, tmp_path)}
        assert _forkserver_root_is_live_check(4242, ppid_map, live) is False

    def test_deep_chain_under_a_live_check_is_not_orphaned(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/test_process_reap.py::TestForkserverRootIsLiveCheck.test_deep_chain_under_a_live_check_is_not_orphaned  # noqa: E501
        _write_live_check_entry(tmp_path, 6000, cmdline=_MODULE_INVOKED_CHECK_CMDLINE)
        _write_proc_entry(tmp_path, 5000, cmdline=_FORKSERVER_CMDLINE, ppid=6000)
        _write_proc_entry(tmp_path, 4242, cmdline=_FORKSERVER_CMDLINE, ppid=5000)
        ppid_map = _all_process_ppids(tmp_path)
        live = {p for p in ppid_map if _is_live_check_process(p, tmp_path)}
        assert _forkserver_root_is_live_check(4242, ppid_map, live) is True


class TestProcessStartAge:
    """`_process_start_age_s` (T-3152): derives age from `/proc/<pid>/
    stat`'s own `starttime` field plus `/proc/uptime`, not the `<proc>/
    <pid>` directory's mtime any more."""

    def test_reads_age_from_starttime(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_process_reap.py::TestProcessStartAge.test_reads_age_from_starttime  # noqa: E501
        _write_proc_entry(tmp_path, 4242, cmdline=b"x\x00", ppid=1, age_s=120.0)
        age = _process_start_age_s(4242, tmp_path, _FAKE_UPTIME_S, _FAKE_CLK_TCK)
        assert age is not None
        assert 119.0 < age < 121.0

    def test_missing_entry_returns_none(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_process_reap.py::TestProcessStartAge.test_missing_entry_returns_none  # noqa: E501
        assert (
            _process_start_age_s(999999, tmp_path, _FAKE_UPTIME_S, _FAKE_CLK_TCK)
            is None
        )

    def test_unknown_uptime_returns_none(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_process_reap.py::TestProcessStartAge.test_unknown_uptime_returns_none  # noqa: E501
        # Must-stay-quiet-in-reverse: an unmeasurable /proc/uptime must
        # degrade to None (unmeasured), never a fabricated age.
        _write_proc_entry(tmp_path, 4242, cmdline=b"x\x00", ppid=1, age_s=120.0)
        assert _process_start_age_s(4242, tmp_path, None, _FAKE_CLK_TCK) is None

    def test_zero_clk_tck_returns_none(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_process_reap.py::TestProcessStartAge.test_zero_clk_tck_returns_none  # noqa: E501
        _write_proc_entry(tmp_path, 4242, cmdline=b"x\x00", ppid=1, age_s=120.0)
        assert _process_start_age_s(4242, tmp_path, _FAKE_UPTIME_S, 0) is None


# frob:ticket T-3152
class TestProcessStartAgeMatchesFleetStatus:
    """T-3152's own cross-check: `frob.process._reap._process_start_age_s`
    and `scripts/fleet_status.py::_forkserver_age_s` must compute the
    IDENTICAL age from the identical `stat`/`uptime`/`clk_tck` input --
    unified on the same heuristic (`stat`'s `starttime` field), each in
    its own textually-independent copy (`fleet_status.py`'s "no `frob`
    import" contract, `_stat_fields_after_comm`'s own docstring), so
    nothing else guarantees these two stay in sync except this test."""

    def test_same_stat_line_and_uptime_yield_the_same_age(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_process_reap.py::TestProcessStartAgeMatchesFleetStatus.test_same_stat_line_and_uptime_yield_the_same_age  # noqa: E501
        from tests.unit.conftest import _load_script

        fleet_status = _load_script("fleet_status")

        _write_proc_entry(tmp_path, 4242, cmdline=b"x\x00", ppid=1, age_s=337.0)
        reap_age = _process_start_age_s(4242, tmp_path, _FAKE_UPTIME_S, _FAKE_CLK_TCK)

        stat_text = (tmp_path / "4242" / "stat").read_text(encoding="utf-8")
        fields = fleet_status._stat_fields_after_comm(stat_text)
        assert fields is not None
        fleet_age = fleet_status._forkserver_age_s(
            fields, _FAKE_UPTIME_S, _FAKE_CLK_TCK
        )

        assert reap_age is not None
        assert fleet_age is not None
        assert reap_age == pytest.approx(fleet_age, abs=1e-9)
        assert reap_age == pytest.approx(337.0, abs=0.02)

    def test_both_agree_none_on_unknown_uptime(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_process_reap.py::TestProcessStartAgeMatchesFleetStatus.test_both_agree_none_on_unknown_uptime  # noqa: E501
        from tests.unit.conftest import _load_script

        fleet_status = _load_script("fleet_status")

        _write_proc_entry(tmp_path, 4242, cmdline=b"x\x00", ppid=1, age_s=337.0)
        stat_text = (tmp_path / "4242" / "stat").read_text(encoding="utf-8")
        fields = fleet_status._stat_fields_after_comm(stat_text)
        assert fields is not None

        assert _process_start_age_s(4242, tmp_path, None, _FAKE_CLK_TCK) is None
        assert fleet_status._forkserver_age_s(fields, None, _FAKE_CLK_TCK) is None


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
        _write_proc_entry(tmp_path, 101, cmdline=b"frob\x00check\x00--json\x00", ppid=1)
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
        _write_proc_entry(tmp_path, 301, cmdline=b"frob\x00checkpointer\x00", ppid=1)
        # "check" present but no "frob" token at all.
        _write_proc_entry(tmp_path, 302, cmdline=b"pytest\x00check\x00", ppid=1)
        assert count_running_checks(proc=tmp_path, self_pid=1) == 0

    def test_missing_proc_returns_none(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_process_reap.py::TestCountRunningChecks.test_missing_proc_returns_none  # noqa: E501
        assert count_running_checks(proc=tmp_path / "does-not-exist") is None


# frob:ticket T-2849
# frob:ticket T-2880
class TestArmParentDeathSignal:
    """`arm_parent_death_signal` -- T-2849's root-cause primitive: arms
    `PR_SET_PDEATHSIG` on the calling process so the kernel signals it the
    instant its DIRECT OS parent dies, by any means including `SIGKILL`."""

    def test_arms_successfully_on_linux(self) -> None:
        # frob:tests tests/unit/test_process_reap.py::TestArmParentDeathSignal.test_arms_successfully_on_linux  # noqa: E501
        if sys.platform != "linux":
            pytest.skip("PR_SET_PDEATHSIG is Linux-only")
        read_fd, write_fd = os.pipe()
        pid = os.fork()
        if pid == 0:
            os.close(read_fd)
            armed = arm_parent_death_signal(signal.SIGTERM)
            os.write(write_fd, b"1" if armed else b"0")
            os.close(write_fd)
            os._exit(0)
        os.close(write_fd)
        try:
            outcome = os.read(read_fd, 1)
        finally:
            os.close(read_fd)
            os.waitpid(pid, 0)
        assert outcome == b"1"

    def test_self_kills_on_missed_reparent_race(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_process_reap.py::TestArmParentDeathSignal.test_self_kills_on_missed_reparent_race  # noqa: E501
        # T-2930: this exercises the Linux-only self-kill logic PAST the
        # `sys.platform != "linux"` guard via mocked `getppid`/`ctypes.
        # CDLL`, same as `test_self_kills_when_already_reparented_before_
        # entry` below -- it must pin `sys.platform` itself (matching
        # `test_returns_false_off_linux`'s own deliberate pin the other
        # direction) or this unconditionally short-circuits to `False` on
        # any CI runner that is not actually Linux (measured: 156-failure
        # macOS run, T-2917 PR#1), never reaching the mocked machinery at
        # all -- a test-only gap, not a product defect (the function's
        # real, documented, non-Linux behavior is exactly `return False`).
        monkeypatch.setattr(sys, "platform", "linux")
        ppid_sequence = iter([111, 222])
        monkeypatch.setattr(os, "getppid", lambda: next(ppid_sequence))
        killed: list[tuple[int, int]] = []
        monkeypatch.setattr(os, "kill", lambda pid, sig: killed.append((pid, sig)))

        class _FakeLibc:
            def prctl(self, *args: object) -> int:
                return 0

        monkeypatch.setattr(_reap.ctypes, "CDLL", lambda *a, **k: _FakeLibc())
        result = arm_parent_death_signal(signal.SIGTERM)
        assert result is True
        assert killed == [(os.getpid(), signal.SIGTERM)]

    def test_returns_false_off_linux(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # frob:tests tests/unit/test_process_reap.py::TestArmParentDeathSignal.test_returns_false_off_linux  # noqa: E501
        monkeypatch.setattr(sys, "platform", "darwin")
        assert arm_parent_death_signal(signal.SIGTERM) is False

    def test_self_kills_when_already_reparented_before_entry(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_process_reap.py::TestArmParentDeathSignal.test_self_kills_when_already_reparented_before_entry  # noqa: E501
        # T-2880: the real parent died BEFORE this function was ever
        # entered (the fork()-to-arm race window T-2849's before/after
        # diff cannot see) -- both getppid() reads inside the function
        # already agree on pid 1 (init), so the old before/after-diff
        # check found nothing wrong and the process armed pdeathsig
        # against a parent (init) that will never die, leaking forever.
        # This is exactly the mechanism T-2880's failure log identified
        # as the gap T-2849 left open; reproduced here without a real
        # fork/exec race by making BOTH getppid() reads return 1.
        # T-2930: pin `sys.platform` so this reaches the mocked machinery
        # on any runner -- see the sibling test above for the full why.
        monkeypatch.setattr(sys, "platform", "linux")
        monkeypatch.setattr(os, "getppid", lambda: 1)
        killed: list[tuple[int, int]] = []
        monkeypatch.setattr(os, "kill", lambda pid, sig: killed.append((pid, sig)))

        class _FakeLibc:
            def prctl(self, *args: object) -> int:
                return 0

        monkeypatch.setattr(_reap.ctypes, "CDLL", lambda *a, **k: _FakeLibc())
        result = arm_parent_death_signal(signal.SIGTERM)
        assert result is True
        assert killed == [(os.getpid(), signal.SIGTERM)]

    def test_default_arg_is_not_evaluated_at_def_time(self) -> None:
        """T-2936: `arm_parent_death_signal`'s default for `sig` MUST be a
        platform-neutral sentinel (`None`), never `signal.SIGKILL` bound
        directly in the `def` line -- a default argument value is
        computed exactly once, when the `def` statement itself executes
        at MODULE LOAD, so `sig: int = signal.SIGKILL` crashed the
        IMPORT of this whole module on Windows (`signal.SIGKILL` does
        not exist there) with an `AttributeError`, before this
        function's own body -- including its own `sys.platform !=
        "linux"` guard -- ever ran once. This inspects the function's
        real `__defaults__` tuple directly: it is the one place a
        crash-on-import regression here is provably impossible to miss,
        since evaluating this assertion at all already proves the `def`
        statement itself imported cleanly."""
        # frob:tests tests/unit/test_process_reap.py::TestArmParentDeathSignal.test_default_arg_is_not_evaluated_at_def_time  # noqa: E501
        assert arm_parent_death_signal.__defaults__ == (None,)

    def test_sig_none_resolves_to_sigkill_only_after_the_platform_guard(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The `None` sentinel must still behave exactly like the old
        `signal.SIGKILL` default on the one platform where SIGKILL
        exists -- resolving late must not silently change behavior for
        every existing Linux caller that relies on the default."""
        # frob:tests tests/unit/test_process_reap.py::TestArmParentDeathSignal.test_sig_none_resolves_to_sigkill_only_after_the_platform_guard  # noqa: E501
        if sys.platform != "linux":
            pytest.skip("PR_SET_PDEATHSIG is Linux-only")
        monkeypatch.setattr(os, "getppid", lambda: 1)
        killed: list[tuple[int, int]] = []
        monkeypatch.setattr(os, "kill", lambda pid, sig: killed.append((pid, sig)))

        class _FakeLibc:
            def prctl(self, *args: object) -> int:
                return 0

        monkeypatch.setattr(_reap.ctypes, "CDLL", lambda *a, **k: _FakeLibc())
        result = arm_parent_death_signal()
        assert result is True
        assert killed == [(os.getpid(), signal.SIGKILL)]


# frob:ticket T-2849
class TestArmForkserverHelperPdeathsigIfRequested:
    """`_arm_forkserver_helper_pdeathsig_if_requested` -- the module-import
    -time hook `frob.gates._FORKSERVER_PRELOAD` triggers inside the
    forkserver helper; must be a no-op unless the env marker is set."""

    def test_noop_without_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # frob:tests tests/unit/test_process_reap.py::TestArmForkserverHelperPdeathsigIfRequested.test_noop_without_env_var  # noqa: E501
        monkeypatch.delenv(FORKSERVER_ARM_PDEATHSIG_ENV, raising=False)
        called: list[None] = []
        monkeypatch.setattr(
            _reap, "arm_parent_death_signal", lambda: called.append(None) or True
        )
        _arm_forkserver_helper_pdeathsig_if_requested()
        assert called == []

    def test_arms_when_env_var_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """T-2936: the call site passes NO explicit `sig` argument any
        more -- `arm_parent_death_signal` resolves its own safe default
        internally, after its own platform guard, rather than the caller
        binding `signal.SIGKILL` (the crash-on-Windows-import shape this
        ticket fixed) itself."""
        # frob:tests tests/unit/test_process_reap.py::TestArmForkserverHelperPdeathsigIfRequested.test_arms_when_env_var_set  # noqa: E501
        monkeypatch.setenv(FORKSERVER_ARM_PDEATHSIG_ENV, "1")
        called = 0

        def _fake() -> bool:
            nonlocal called
            called += 1
            return True

        monkeypatch.setattr(_reap, "arm_parent_death_signal", _fake)
        _arm_forkserver_helper_pdeathsig_if_requested()
        assert called == 1

    def test_success_logs_nothing_at_all(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests tests/unit/test_process_reap.py::TestArmForkserverHelperPdeathsigIfRequested.test_success_logs_nothing_at_all  # noqa: E501
        # A DEBUG-level log call here would leak straight onto `frob check
        # --json`'s stdout (this hook runs at forkserver PRELOAD time,
        # before T-0806's per-job stdout clamp has ever run for this
        # process) -- reproduced for real while validating this fix. The
        # success path must stay silent.
        monkeypatch.setenv(FORKSERVER_ARM_PDEATHSIG_ENV, "1")
        monkeypatch.setattr(_reap, "arm_parent_death_signal", lambda sig=None: True)
        with caplog.at_level("DEBUG", logger="frob.process._reap"):
            _arm_forkserver_helper_pdeathsig_if_requested()
        assert caplog.records == []

    def test_failure_still_warns(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests tests/unit/test_process_reap.py::TestArmForkserverHelperPdeathsigIfRequested.test_failure_still_warns  # noqa: E501
        # WARNING is safe to log here even at preload time: this repo's
        # own [handlers.stderr] sink is WARNING-and-above and [handlers.
        # stdout]'s below_warning filter explicitly excludes it, so this
        # never contaminates --json stdout the way a DEBUG log would.
        monkeypatch.setenv(FORKSERVER_ARM_PDEATHSIG_ENV, "1")
        monkeypatch.setattr(_reap, "arm_parent_death_signal", lambda sig=None: False)
        with caplog.at_level("WARNING", logger="frob.process._reap"):
            _arm_forkserver_helper_pdeathsig_if_requested()
        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "WARNING"
