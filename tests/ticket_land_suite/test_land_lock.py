import json
import os
import sys
import time
from pathlib import Path

import pytest

from frob.tickets._models import (
    LandError,
)

pytestmark = pytest.mark.heavy_subprocess

# frob:ticket T-1515
# frob:ticket T-1634
class TestLandLockHolderMetadataAndTimeout:
    """T-1515: `_land_lock` now writes pid/session/start-time into
    land.lock's own content on acquisition, and refuses (raising
    `LandLockTimeout`) rather than blocking forever when a foreign holder
    does not release within its timeout -- the fix for the 2026-08-04
    incident (an orphaned background land driver queued silently against a
    new coordinator session's own `land()` call)."""

    # frob:tests \
    # tests/test_ticket_land.py::TestLandLockHolderMetadataAndTimeout.test_holder_metad\
    # ata_written_on_acquire
    # frob:ticket T-1515
    def test_holder_metadata_written_on_acquire(self, tmp_path: Path) -> None:
        import os

        from frob.tickets._land import _LAND_LOCK_REL, _land_lock

        with _land_lock(tmp_path):
            content = (tmp_path / _LAND_LOCK_REL).read_text()
        parsed = json.loads(content)
        assert parsed["pid"] == os.getpid()
        assert "session_id" in parsed
        assert "started_at" in parsed

    # frob:tests \
    # tests/test_ticket_land.py::TestLandLockHolderMetadataAndTimeout.test_lock_release\
    # d_after_context_exits
    # frob:ticket T-1515
    def test_lock_released_after_context_exits(self, tmp_path: Path) -> None:
        if sys.platform == "win32":
            pytest.skip("POSIX-only (T-3244)")
        import fcntl

        from frob.tickets._land import _LAND_LOCK_REL, _land_lock

        with _land_lock(tmp_path):
            pass

        # A fresh acquisition from a DIFFERENT fd must succeed non-
        # blocking now that the context above has released it.
        path = tmp_path / _LAND_LOCK_REL
        fd = os.open(str(path), os.O_CREAT | os.O_RDWR, 0o644)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)

    # frob:tests \
    # tests/test_ticket_land.py::TestLandLockHolderMetadataAndTimeout.test_timeout_rais\
    # es_when_a_foreign_holder_never_releases
    # frob:ticket T-1515
    def test_timeout_raises_when_a_foreign_holder_never_releases(
        self, tmp_path: Path
    ) -> None:
        if sys.platform == "win32":
            pytest.skip("POSIX-only (T-3244)")
        import fcntl

        from frob.tickets._land import (
            _LAND_LOCK_REL,
            LandLockTimeout,
            _land_lock,
        )

        path = tmp_path / _LAND_LOCK_REL
        path.parent.mkdir(parents=True, exist_ok=True)
        holder_fd = os.open(str(path), os.O_CREAT | os.O_RDWR, 0o644)
        fcntl.flock(holder_fd, fcntl.LOCK_EX)
        os.write(
            holder_fd,
            (
                json.dumps(
                    {
                        "pid": 999999,
                        "session_id": "foreign-orphan",
                        "started_at": "2026-08-04T00:00:00+00:00",
                    }
                )
                + "\n"
            ).encode("utf-8"),
        )
        try:
            with pytest.raises(LandLockTimeout) as excinfo:
                with _land_lock(tmp_path, timeout=0.2):
                    pass  # pragma: no cover -- must never be reached
            assert excinfo.value.holder is not None
            assert excinfo.value.holder["session_id"] == "foreign-orphan"
        finally:
            fcntl.flock(holder_fd, fcntl.LOCK_UN)
            os.close(holder_fd)

    # frob:tests \
    # tests/test_ticket_land.py::TestLandLockHolderMetadataAndTimeout.test_orphaned_loc\
    # k_from_a_confirmed_dead_pid_is_reclaimed_and_logged
    # frob:ticket T-1634
    def test_orphaned_lock_from_a_confirmed_dead_pid_is_reclaimed_and_logged(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """T-1634: a land.lock file naming a pid that does not correspond
        to any running process, with NO real `flock` actually held (the
        orphaned-file-only shape a killed/SIGKILLed land leaves behind --
        the OS already released the real OS-level lock the instant that
        process exited), is proceeded through IMMEDIATELY by a fresh
        `_land_lock` acquisition -- never waits, never raises
        `LandLockTimeout` -- and logs a WARNING disclosing the dead
        holder's identity, closing the 'a human has to notice and delete
        this by hand' gap T-1634 was filed against."""
        import logging

        from frob.tickets._land import _LAND_LOCK_REL, _land_lock

        dead_pid = min(os.getpid() * 7 + 999983, 2**22)
        path = tmp_path / _LAND_LOCK_REL
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "pid": dead_pid,
                    "session_id": "orphaned-session",
                    "started_at": "2026-08-04T00:00:00+00:00",
                }
            )
            + "\n"
        )

        with caplog.at_level(logging.WARNING, logger="frob.tickets._land"):
            with _land_lock(tmp_path, timeout=5.0):
                pass

        reclaim_lines = [
            r.message
            for r in caplog.records
            if "reclaiming orphaned land.lock" in r.message
        ]
        assert reclaim_lines, caplog.text
        assert str(dead_pid) in reclaim_lines[0]
        assert "orphaned-session" in reclaim_lines[0]

    # frob:tests \
    # tests/test_ticket_land.py::TestLandLockHolderMetadataAndTimeout.test_orphaned_loc\
    # k_naming_a_genuinely_live_pid_still_refuses
    # frob:ticket T-1634
    def test_orphaned_lock_naming_a_genuinely_live_pid_still_refuses(
        self, tmp_path: Path
    ) -> None:
        """T-1634's reclaim must never override a genuinely-held OS lock:
        a land.lock naming THIS test process's own (genuinely live) pid,
        with the flock ACTUALLY held via a separate fd, still times out
        exactly as before -- liveness alone is never a substitute for the
        real `flock`."""
        if sys.platform == "win32":
            pytest.skip("POSIX-only (T-3244)")
        import fcntl

        from frob.tickets._land import (
            _LAND_LOCK_REL,
            LandLockTimeout,
            _land_lock,
        )

        path = tmp_path / _LAND_LOCK_REL
        path.parent.mkdir(parents=True, exist_ok=True)
        holder_fd = os.open(str(path), os.O_CREAT | os.O_RDWR, 0o644)
        fcntl.flock(holder_fd, fcntl.LOCK_EX)
        os.write(
            holder_fd,
            (
                json.dumps(
                    {
                        "pid": os.getpid(),
                        "session_id": "genuinely-live",
                        "started_at": "2026-08-04T00:00:00+00:00",
                    }
                )
                + "\n"
            ).encode("utf-8"),
        )
        try:
            with pytest.raises(LandLockTimeout) as excinfo:
                with _land_lock(tmp_path, timeout=0.2):
                    pass  # pragma: no cover -- must never be reached
            assert excinfo.value.holder is not None
            assert excinfo.value.holder["session_id"] == "genuinely-live"
        finally:
            fcntl.flock(holder_fd, fcntl.LOCK_UN)
            os.close(holder_fd)

    # frob:tests \
    # tests/test_ticket_land.py::TestLandLockHolderMetadataAndTimeout.test_lock_timeout\
    # _stays_below_the_playbook_shell_wrapper_floor
    # frob:ticket T-2065
    def test_lock_timeout_stays_below_the_playbook_shell_wrapper_floor(self) -> None:
        """T-2065: `_LAND_LOCK_TIMEOUT_S` must sit strictly BELOW the
        agent-playbook's own mandated foreground shell-wrapper floor
        (`timeout 540`, docs/guides/agent-playbook.md section 0 item 3 /
        section 3b) -- otherwise a land queued behind a foreign holder can
        be SIGTERM'd by that outer wrapper before `_land_lock`'s own
        `LandLockTimeout` ever gets a chance to fire and print a clean,
        attributable refusal (the confirmed T-2032/T-2033 silent-death
        mechanism). Was 600.0 (above the floor) before this fix."""
        from frob.tickets._land import _LAND_LOCK_TIMEOUT_S

        playbook_shell_wrapper_floor_s = 540.0
        assert _LAND_LOCK_TIMEOUT_S < playbook_shell_wrapper_floor_s, (
            f"_LAND_LOCK_TIMEOUT_S={_LAND_LOCK_TIMEOUT_S} exceeds the "
            f"playbook's own mandated {playbook_shell_wrapper_floor_s}s "
            "shell-wrapper floor -- a land queued this long gets "
            "SIGTERM'd before LandLockTimeout can ever fire (T-2065)"
        )


# frob:ticket T-2691
class TestLandStatus:
    """T-2691: `_write_land_status` writes `root`'s land-status marker
    (`.frob/land-status.json`) -- the externally-pollable phase/lock-wait
    disclosure fixing the incident where a land killed under lock
    contention left nothing beyond a truncated stdout log for an operator
    to inspect."""

    # frob:ticket T-2691
    # frob:tests \
    # tests/test_ticket_land.py::TestLandStatus.test_phase_transitions_are_pollable
    def test_phase_transitions_are_pollable(self, tmp_path: Path) -> None:
        """Successive `_write_land_status` calls for the SAME ticket
        preserve `started_at` across phase transitions (T-2691's own
        docstring requirement -- an operator timing a land against a
        single clock, not a new one per phase) while always advancing
        `updated_at` and the recorded `phase`."""

        from frob.tickets._land import _LAND_STATUS_REL, _write_land_status

        _write_land_status(tmp_path, "T-2691", "acquiring-lock")
        first = json.loads((tmp_path / _LAND_STATUS_REL).read_text())
        assert first["ticket_id"] == "T-2691"
        assert first["phase"] == "acquiring-lock"
        assert first["pid"] == os.getpid()

        time.sleep(0.01)
        _write_land_status(tmp_path, "T-2691", "running")
        second = json.loads((tmp_path / _LAND_STATUS_REL).read_text())
        assert second["phase"] == "running"
        assert second["started_at"] == first["started_at"]
        assert second["updated_at"] != first["updated_at"]

    # frob:ticket T-2691
    # frob:tests \
    # tests/test_ticket_land.py::TestLandStatus.test_waiting_phase_records_lock_holder
    def test_waiting_phase_records_lock_holder(self, tmp_path: Path) -> None:
        """`lock_wait`, when given, is recorded verbatim under the
        marker's own `lock_wait` key -- the holder metadata a blocked
        land is currently waiting on."""

        from frob.tickets._land import _LAND_STATUS_REL, _write_land_status

        holder = {"pid": 123, "session_id": "other-session"}
        _write_land_status(tmp_path, "T-2691", "waiting-for-lock", lock_wait=holder)
        marker = json.loads((tmp_path / _LAND_STATUS_REL).read_text())
        assert marker["lock_wait"] == holder

    # frob:ticket T-2691
    # frob:tests \
    # tests/test_ticket_land.py::TestLandStatus.test_write_failure_is_best_effort_and_n\
    # ever_raises
    def test_write_failure_is_best_effort_and_never_raises(
        self, tmp_path: Path
    ) -> None:
        """A `.frob/` that cannot be created (e.g. a same-named file
        blocking the directory) makes `_write_land_status` log and return
        quietly, same as `_write_intent`'s own best-effort posture --
        this marker must never itself fail a `land()` call."""
        from frob.tickets._land import _write_land_status

        blocker = tmp_path / ".frob"
        blocker.write_text("not a directory")
        _write_land_status(tmp_path, "T-2691", "running")  # must not raise



# frob:ticket T-2934
class TestLandLockPlatformBackends:
    """T-2934/T-3506: `_land_lock`'s msvcrt (Windows) backend and its
    loud refusal (`LandLockTimeout(root, None)`) when neither `fcntl`
    nor `msvcrt` exists -- the same PLATFORM001-shaped fix T-2918
    applied to `_baseline_lock`, reusing `land()`'s own existing typed
    error rather than inventing a second exception for "no lock
    primitive at all". T-3506 moved the actual dual-path primitive to
    `frob.process._lock`, so the platform fakes here patch THAT
    module's `fcntl`/`msvcrt` bindings, not `frob.tickets._land`'s own
    (which no longer exist as module attributes)."""

    # frob:tests \
    # tests/test_ticket_land.py::TestLandLockPlatformBackends.test_no_lock_primitive_ra\
    # ises_land_lock_timeout
    def test_no_lock_primitive_raises_land_lock_timeout(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import frob.process._lock as _lock_mod
        from frob.tickets._land import LandLockTimeout, _land_lock

        monkeypatch.setattr(_lock_mod, "fcntl", None)
        monkeypatch.setattr(_lock_mod, "msvcrt", None)
        with pytest.raises(LandLockTimeout) as excinfo:
            with _land_lock(tmp_path):
                pass  # pragma: no cover -- must never be reached
        assert excinfo.value.holder is None

    # frob:tests \
    # tests/test_ticket_land.py::TestLandLockPlatformBackends.test_windows_backend_roun\
    # d_trips
    def test_windows_backend_round_trips(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The msvcrt backend is exercised on Linux CI via a fake module
        standing in for the real Windows-only `msvcrt`, backed by real
        `fcntl.flock` under the hood -- proves the control flow (byte
        seeded, acquire, holder metadata written, release) the real
        backend only ever runs for real on Windows."""
        import fcntl as _real_fcntl

        import frob.process._lock as _lock_mod
        from frob.tickets._land import _LAND_LOCK_REL, _land_lock

        class _FakeMsvcrt:
            LK_NBLCK = 1
            LK_UNLCK = 2

            @staticmethod
            def locking(fd: int, mode: int, _nbytes: int) -> None:
                if sys.platform == "win32":
                    pytest.skip("POSIX-only (T-3244)")
                if mode == _FakeMsvcrt.LK_UNLCK:
                    _real_fcntl.flock(fd, _real_fcntl.LOCK_UN)
                    return
                try:
                    _real_fcntl.flock(fd, _real_fcntl.LOCK_EX | _real_fcntl.LOCK_NB)
                except OSError as exc:
                    raise PermissionError(str(exc)) from exc

        monkeypatch.setattr(_lock_mod, "fcntl", None)
        monkeypatch.setattr(_lock_mod, "msvcrt", _FakeMsvcrt)

        entered = False
        with _land_lock(tmp_path):
            entered = True
            content = (tmp_path / _LAND_LOCK_REL).read_text()
        assert entered is True
        assert json.loads(content)["pid"] == os.getpid()

        # A second, independent acquire/release round-trip must also
        # succeed -- proves release genuinely happened.
        entered = False
        with _land_lock(tmp_path):
            entered = True
        assert entered is True


# frob:ticket T-3018
class TestProbeLandLockPidLivenessDelegatesToSharedModule:
    """T-3018: `_probe_land_lock_pid_liveness` used to run its own
    POSIX-shaped `os.kill(pid, 0)` -- the same unsafe-on-Windows shape
    T-3003 had already fixed once in `frob.mutate._journal`. It now
    delegates to `frob.process._pid_liveness.pid_alive_tristate`; faking
    that shared module's Windows backend here proves the delegation is
    real, not just a same-behavior coincidence."""

    # frob:tests \
    # tests/test_ticket_land.py::TestProbeLandLockPidLivenessDelegatesToSharedModule.te\
    # st_windows_backend_alive_pid_is_true
    def test_windows_backend_alive_pid_is_true(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from frob.process import _pid_liveness
        from frob.tickets._land import _probe_land_lock_pid_liveness

        class _FakeKernel32:
            def OpenProcess(self, _access, _inherit, _pid):
                return 1

            def GetExitCodeProcess(self, _handle, exit_code_ptr):
                exit_code_ptr._obj.value = _pid_liveness._STILL_ACTIVE
                return 1

            def CloseHandle(self, _handle):
                return 1

        monkeypatch.setattr(_pid_liveness, "_kernel32", _FakeKernel32())
        assert _probe_land_lock_pid_liveness(4242) is True

    # frob:tests \
    # tests/test_ticket_land.py::TestProbeLandLockPidLivenessDelegatesToSharedModule.te\
    # st_windows_backend_never_ambiguous
    def test_windows_backend_never_ambiguous(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The Windows query-only probe is definitive by construction --
        `_probe_land_lock_pid_liveness`'s three-state contract must never
        report `None` on that backend."""
        from frob.process import _pid_liveness
        from frob.tickets._land import _probe_land_lock_pid_liveness

        class _FakeKernel32:
            def OpenProcess(self, _access, _inherit, _pid):
                return 0  # unknown pid: OpenProcess fails

            def GetExitCodeProcess(self, _handle, _exit_code_ptr):
                raise AssertionError("must not be called for a failed OpenProcess")

            def CloseHandle(self, _handle):
                raise AssertionError("no handle to close")

        monkeypatch.setattr(_pid_liveness, "_kernel32", _FakeKernel32())
        assert _probe_land_lock_pid_liveness(999999) is False




# frob:ticket T-2774
class TestLandLockWaitBudgetFromDeclaredDeadline:
    """T-2774: `_resolve_land_lock_wait_budget_s` bounds the land.lock
    WAIT by the caller's declared `FROB_LAND_DEADLINE_S` minus the
    measured work-time estimate, instead of the flat
    `_LAND_LOCK_TIMEOUT_S` -- so a land no longer starts work it provably
    cannot finish before its outer wrapper kills it. Positive controls in
    both directions per the ticket: insufficient budget refuses
    immediately with a distinct typed error and no side effect; ample
    budget (or no declaration at all) behaves exactly as before."""

    # frob:tests \
    # tests/test_ticket_land.py::TestLandLockWaitBudgetFromDeclaredDeadline.test_no_dec\
    # laration_keeps_the_flat_timeout_unchanged
    # frob:ticket T-2774
    def test_no_declaration_keeps_the_flat_timeout_unchanged(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """No `FROB_LAND_DEADLINE_S` set (every caller before T-2774) must
        resolve to exactly `_LAND_LOCK_TIMEOUT_S`, unchanged -- the
        ticket's explicit 'absent a caller-declared budget, behavior must
        not regress' requirement."""
        from frob.tickets._land import (
            _LAND_LOCK_TIMEOUT_S,
            _resolve_land_lock_wait_budget_s,
        )

        monkeypatch.delenv("FROB_LAND_DEADLINE_S", raising=False)
        result = _resolve_land_lock_wait_budget_s(tmp_path)
        assert result.is_ok, result.err
        assert result.danger_ok == _LAND_LOCK_TIMEOUT_S

    # frob:tests \
    # tests/test_ticket_land.py::TestLandLockWaitBudgetFromDeclaredDeadline.test_ample_\
    # deadline_derives_a_wait_budget_and_proceeds
    # frob:ticket T-2774
    def test_ample_deadline_derives_a_wait_budget_and_proceeds(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Positive control (direction 2, ticket's own required shape): a
        generous declared deadline still yields a usable, positive wait
        budget bounded above by `_LAND_LOCK_TIMEOUT_S` -- a land with
        ample budget and a free lock proceeds exactly as today, it is
        NOT turned into a refusal just because it opted in."""
        from frob.tickets._land import (
            _LAND_LOCK_TIMEOUT_S,
            _resolve_land_lock_wait_budget_s,
        )

        monkeypatch.setenv("FROB_LAND_DEADLINE_S", "100000")
        result = _resolve_land_lock_wait_budget_s(tmp_path)
        assert result.is_ok, result.err
        assert 0 < result.danger_ok <= _LAND_LOCK_TIMEOUT_S

    # frob:tests \
    # tests/test_ticket_land.py::TestLandLockWaitBudgetFromDeclaredDeadline.test_insuff\
    # icient_deadline_refuses_immediately_with_no_lock_attempt
    # frob:ticket T-2774
    def test_insufficient_deadline_refuses_immediately_with_no_lock_attempt(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Positive control (direction 1): a deadline too small to cover
        even the estimated work alone refuses IMMEDIATELY with a typed
        `Err(LandError.LandLockTimeout)` -- the ticket's own text allows
        reusing this member rather than minting a new one ("or a new,
        distinct variant") -- and the log line explicitly marks this a
        declined-early refusal, never a died-mid-land timeout, which is
        the caller-visible distinction T-2774 requires: a live `Err`
        object either way, never the bare undiagnosable exit-143 the
        2026-08-21 incident produced."""
        import logging

        from frob.tickets._land import _resolve_land_lock_wait_budget_s

        monkeypatch.setenv("FROB_LAND_DEADLINE_S", "1")
        with caplog.at_level(logging.ERROR, logger="frob.tickets._land"):
            result = _resolve_land_lock_wait_budget_s(tmp_path)
        assert result.is_err, result.ok
        assert result.danger_err is LandError.LandLockTimeout
        assert any(
            "declined-early" in r.message and "NOT a died-mid-land" in r.message
            for r in caplog.records
        ), caplog.text

    # frob:tests \
    # tests/test_ticket_land.py::TestLandLockWaitBudgetFromDeclaredDeadline.test_short_\
    # wait_then_acquire_still_completes
    # frob:ticket T-2774
    def test_short_wait_then_acquire_still_completes(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Positive control (direction 3): a land that would only need to
        wait BRIEFLY for the lock, with budget to spare after that wait,
        still resolves to a positive wait budget -- a declared deadline
        must not turn every contended land into a refusal, only the ones
        that genuinely cannot fit."""
        from frob.tickets._land import (
            _land_lock,
            _resolve_land_lock_wait_budget_s,
        )

        monkeypatch.setenv("FROB_LAND_DEADLINE_S", "100000")
        result = _resolve_land_lock_wait_budget_s(tmp_path)
        assert result.is_ok, result.err
        with _land_lock(tmp_path, timeout=result.danger_ok):
            pass

    # frob:tests \
    # tests/test_ticket_land.py::TestLandLockWaitBudgetFromDeclaredDeadline.test_unpars\
    # eable_deadline_falls_back_to_the_flat_timeout
    # frob:ticket T-2774
    def test_unparseable_deadline_falls_back_to_the_flat_timeout(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A non-numeric `FROB_LAND_DEADLINE_S` is treated the same as
        absent, not as a hard error -- a malformed opt-in must not brick
        landing."""
        from frob.tickets._land import (
            _LAND_LOCK_TIMEOUT_S,
            _resolve_land_lock_wait_budget_s,
        )

        monkeypatch.setenv("FROB_LAND_DEADLINE_S", "not-a-number")
        result = _resolve_land_lock_wait_budget_s(tmp_path)
        assert result.is_ok, result.err
        assert result.danger_ok == _LAND_LOCK_TIMEOUT_S



class TestLandLockInlineWaitDefaultsNearZero:
    """T-2816: waiting OUTSIDE a land (the caller's own
    `wait_for_land_slot.py` poll loop, run before `frob ticket land` ever
    starts) is free; waiting INSIDE a land spends the exact work-time
    budget `FROB_LAND_DEADLINE_S` declared. T-2774's
    `min(_LAND_LOCK_TIMEOUT_S, deadline - estimated_work_s)` could still
    burn up to 500s of a 540s deadline queueing -- measured 2026-08-21: a
    land parked 177s elapsed at 51s CPU (29%) then was SIGKILLed once it
    finally got the lock. These tests pin the fix: the DEFAULT in-land
    wait ceiling is now near-zero, with an explicit env opt-in preserved
    for a caller that cannot poll externally (none exists in this repo
    today, per the module-level comment's own audit)."""

    # frob:tests \
    # tests/test_ticket_land.py::TestLandLockInlineWaitDefaultsNearZero.test_ample_dead\
    # line_defaults_to_the_near_zero_ceiling_not_the_flat_500s
    # frob:ticket T-2816
    def test_ample_deadline_defaults_to_the_near_zero_ceiling_not_the_flat_500s(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Positive control (direction 1): with a generous declared
        deadline and NO `FROB_LAND_INLINE_WAIT_S` opt-in, the resolved
        wait budget is the near-zero default -- not `_LAND_LOCK_TIMEOUT_S`
        -- so the vast majority of the declared deadline is left for the
        land's own work when it begins, rather than spent queueing."""
        from frob.tickets._land import (
            _LAND_LOCK_DEFAULT_INLINE_WAIT_S,
            _LAND_LOCK_TIMEOUT_S,
            _resolve_land_lock_wait_budget_s,
        )

        monkeypatch.delenv("FROB_LAND_INLINE_WAIT_S", raising=False)
        monkeypatch.setenv("FROB_LAND_DEADLINE_S", "100000")
        result = _resolve_land_lock_wait_budget_s(tmp_path)
        assert result.is_ok, result.err
        assert result.danger_ok == _LAND_LOCK_DEFAULT_INLINE_WAIT_S
        assert result.danger_ok < _LAND_LOCK_TIMEOUT_S

    # frob:tests \
    # tests/test_ticket_land.py::TestLandLockInlineWaitDefaultsNearZero.test_opt_in_env\
    # _restores_a_longer_in_land_wait
    # frob:ticket T-2816
    def test_opt_in_env_restores_a_longer_in_land_wait(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A caller that genuinely cannot poll externally is not
        foreclosed: `FROB_LAND_INLINE_WAIT_S` opts back into a longer
        in-land wait, still bounded by the flat ceiling and by the
        remaining budget."""
        from frob.tickets._land import (
            _LAND_LOCK_DEFAULT_INLINE_WAIT_S,
            _resolve_land_lock_wait_budget_s,
        )

        monkeypatch.setenv("FROB_LAND_DEADLINE_S", "100000")
        monkeypatch.setenv("FROB_LAND_INLINE_WAIT_S", "50")
        result = _resolve_land_lock_wait_budget_s(tmp_path)
        assert result.is_ok, result.err
        assert result.danger_ok == 50.0
        assert result.danger_ok > _LAND_LOCK_DEFAULT_INLINE_WAIT_S

    # frob:tests \
    # tests/test_ticket_land.py::TestLandLockInlineWaitDefaultsNearZero.test_opt_in_env\
    # _is_still_capped_by_the_remaining_budget
    # frob:ticket T-2816
    def test_opt_in_env_is_still_capped_by_the_remaining_budget(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The opt-in cannot be used to reintroduce T-2774's regression:
        even an explicit request for a long in-land wait is still capped
        by whatever budget actually remains after the work estimate, not
        granted outright."""
        from frob.app._check_chunking import _derive_post_land_sweep_budget_s
        from frob.tickets._land import _resolve_land_lock_wait_budget_s

        estimated_work_s = _derive_post_land_sweep_budget_s(tmp_path)
        tight_deadline_s = estimated_work_s + 5
        monkeypatch.setenv("FROB_LAND_DEADLINE_S", str(tight_deadline_s))
        monkeypatch.setenv("FROB_LAND_INLINE_WAIT_S", "500")
        result = _resolve_land_lock_wait_budget_s(tmp_path)
        assert result.is_ok, result.err
        assert result.danger_ok == pytest.approx(5.0)

    # frob:tests \
    # tests/test_ticket_land.py::TestLandLockInlineWaitDefaultsNearZero.test_unparseabl\
    # e_inline_wait_env_falls_back_to_the_near_zero_default
    # frob:ticket T-2816
    def test_unparseable_inline_wait_env_falls_back_to_the_near_zero_default(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A malformed `FROB_LAND_INLINE_WAIT_S` must not brick landing --
        same posture as `FROB_LAND_DEADLINE_S`'s own unparseable-value
        handling: log and fall back, never raise."""
        from frob.tickets._land import (
            _LAND_LOCK_DEFAULT_INLINE_WAIT_S,
            _resolve_land_lock_wait_budget_s,
        )

        monkeypatch.setenv("FROB_LAND_DEADLINE_S", "100000")
        monkeypatch.setenv("FROB_LAND_INLINE_WAIT_S", "not-a-number")
        result = _resolve_land_lock_wait_budget_s(tmp_path)
        assert result.is_ok, result.err
        assert result.danger_ok == _LAND_LOCK_DEFAULT_INLINE_WAIT_S

    # frob:tests \
    # tests/test_ticket_land.py::TestLandLockInlineWaitDefaultsNearZero.test_held_lock_\
    # released_quickly_leaves_almost_the_whole_deadline_for_work
    # frob:ticket T-2816
    def test_held_lock_released_quickly_leaves_almost_the_whole_deadline_for_work(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """End-to-end positive control: plant a HELD lock (a foreign
        holder), then resolve+acquire exactly as `land()` does, and
        assert on the wall-clock actually spent waiting -- it must stay
        near the near-zero ceiling, not balloon toward the deadline, even
        though a real foreign holder existed and was waited out."""
        import threading
        import time as _time

        from frob.tickets._land import _land_lock, _resolve_land_lock_wait_budget_s

        monkeypatch.delenv("FROB_LAND_INLINE_WAIT_S", raising=False)
        monkeypatch.setenv("FROB_LAND_DEADLINE_S", "100000")

        release_after_s = 2.0
        release_event = threading.Event()

        def _hold_then_release() -> None:
            with _land_lock(tmp_path):
                release_event.wait(timeout=release_after_s + 5.0)

        holder_thread = threading.Thread(target=_hold_then_release, daemon=True)
        holder_thread.start()
        _time.sleep(0.2)  # let the holder actually acquire first

        result = _resolve_land_lock_wait_budget_s(tmp_path)
        assert result.is_ok, result.err

        started_waiting = _time.monotonic()
        release_event.set()
        with _land_lock(tmp_path, timeout=result.danger_ok):
            elapsed_waiting_s = _time.monotonic() - started_waiting
        holder_thread.join(timeout=10.0)

        # The wait must complete well inside the near-zero ceiling, not
        # anywhere near the 100000s deadline -- this is the "budget
        # actually remaining when work begins" the ticket asks to prove.
        assert elapsed_waiting_s < 10.0, elapsed_waiting_s
