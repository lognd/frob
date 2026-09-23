"""T-4494: `frob ticket land` never installed the SIGUSR1 stack-dump
handler at all outside `frob serve`'s own daemon -- a silent, CPU-bound
phase (T-4408's measured 21-minute incident) had no `py-spy` access
(root-only on the incident box) and `kill -USR1` on the wedged land just
killed it (exit 138) instead of producing a diagnostic. This module
covers both fixes: `install_stackdump_handler(force=True)` (unconditional
install, `frob.testing._stackdump`) and the silent-phase self-dump
watchdog (`_land_cmd.py`'s `_land_silent_phase_watchdog` family).
"""

from __future__ import annotations

import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

if sys.platform == "win32":  # pragma: no cover - POSIX-only feature
    pytest.skip("SIGUSR1 is POSIX-only", allow_module_level=True)

import signal

from frob.app.ticket_runner import _land_cmd
from frob.testing._stackdump import STACKDUMP_ENV, write_stack_dump


class TestWriteStackDump:
    """`write_stack_dump` (T-4494): the non-signal-handler-shaped core
    `dump_all_thread_stacks` and the land watchdog both call."""

    # frob:tests tests/unit/test_land_stackdump.py::TestWriteStackDump.test_writes_and_returns_dump_path  # noqa: E501
    # frob:tests src/frob/testing/_stackdump.py::write_stack_dump
    def test_writes_and_returns_dump_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Writes `.frob/stackdumps/pid-<pid>.txt` under the CURRENT
        working directory, returns that same path, and the file's
        content carries the given header plus this process's pid."""
        monkeypatch.chdir(tmp_path)
        dump_path = write_stack_dump("unit-test header")
        assert dump_path == Path(".frob") / "stackdumps" / f"pid-{_pid()}.txt"
        assert (tmp_path / dump_path).is_file()
        content = dump_path.read_text(encoding="utf-8")
        assert "unit-test header" in content
        assert str(_pid()) in content


def _pid() -> int:
    """This process's pid -- `os.getpid()` inlined once so every
    assertion in this module reads identically without re-importing
    `os` at call sites that only need this one value."""
    import os

    return os.getpid()


class TestInstallStackdumpHandlerForce:
    """`install_stackdump_handler(force=True)` (T-4494): bypasses
    `STACKDUMP_ENV` entirely, unlike the pre-existing opt-in-only
    default every other caller keeps."""

    # frob:tests tests/unit/test_land_stackdump.py::TestInstallStackdumpHandlerForce.test_force_installs_regardless_of_env  # noqa: E501
    # frob:tests src/frob/testing/_stackdump.py::install_stackdump_handler
    def test_force_installs_regardless_of_env(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """With `STACKDUMP_ENV` unset (the ordinary opt-in-only default
        would be a no-op here), `force=True` still installs the handler
        -- a `SIGUSR1` sent in-process writes a dump file instead of
        falling through to the default disposition."""
        from frob.testing._stackdump import install_stackdump_handler

        monkeypatch.delenv(STACKDUMP_ENV, raising=False)
        monkeypatch.chdir(tmp_path)
        previous = signal.getsignal(signal.SIGUSR1)
        try:
            install_stackdump_handler(force=True)
            import os

            os.kill(os.getpid(), signal.SIGUSR1)
            dump_path = tmp_path / ".frob" / "stackdumps" / f"pid-{os.getpid()}.txt"
            assert dump_path.is_file()
            assert "SIGUSR1 stack dump" in dump_path.read_text(encoding="utf-8")
        finally:
            signal.signal(signal.SIGUSR1, previous)


# frob:ticket T-4494
_LAND_LIKE_SURVIVES_SRC = """
import sys
import time
from frob.testing._stackdump import install_stackdump_handler
install_stackdump_handler(force=True)
time.sleep(6)
sys.stdout.write("survived\\n")
sys.stdout.flush()
"""

# frob:ticket T-4494
_LAND_LIKE_DIES_SRC = """
import sys
import time
time.sleep(6)
sys.stdout.write("survived\\n")
sys.stdout.flush()
"""


def _spawn_and_signal(tmp_path: Path, script: str) -> tuple[int | None, str, str, Path]:
    """Exec-via-list entry (mirrors `tests/system/test_ci_hang_guard_
    positive_control.py`'s `_run_under_watcher` shape, T-4494): launch
    `script` as a genuine `sys.executable -c` subprocess with `cwd=
    tmp_path` (so its own `.frob/stackdumps/` resolves under the test's
    isolated directory), give it time to reach its own `time.sleep`,
    send it a real `SIGUSR1`, then wait out its full sleep so a survivor
    has time to print and exit 0. Returns `(returncode, stdout, stderr,
    dump_path)` -- `returncode` is `None` if the process never exits
    within the wait budget (killed and reported as such by the caller)."""
    proc = subprocess.Popen(
        [sys.executable, "-c", script],
        cwd=tmp_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    time.sleep(1.0)
    proc.send_signal(signal.SIGUSR1)
    dump_path = tmp_path / ".frob" / "stackdumps" / f"pid-{proc.pid}.txt"
    try:
        stdout, stderr = proc.communicate(timeout=15)
        returncode: int | None = proc.returncode
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, stderr = proc.communicate()
        returncode = None
    return returncode, stdout, stderr, dump_path


class TestLandLikeSubprocessSigusr1:
    """BUG002 repro (T-4494): a land-like subprocess sent `SIGUSR1` at
    the PARENT commit (no forced handler install existed at all -- the
    `install_stackdump_handler(force=True)` call this test's "survives"
    half depends on is this ticket's own fix) dies; after the fix, the
    SAME signal delivered to a process that installed the handler with
    `force=True` leaves it running and produces a dump file."""

    # frob:tests tests/unit/test_land_stackdump.py::TestLandLikeSubprocessSigusr1.test_dies_without_the_handler  # noqa: E501
    def test_dies_without_the_handler(self, tmp_path: Path) -> None:
        """A subprocess that never installs a `SIGUSR1` handler (the
        pre-T-4494 `frob ticket land` shape) is killed by the signal: on
        POSIX, `Popen.returncode` is the negative signal number
        (`-signal.SIGUSR1`) -- the same underlying condition a shell
        reports as exit 138 (128 + `SIGUSR1`'s value 10)."""
        returncode, _stdout, _stderr, dump_path = _spawn_and_signal(
            tmp_path, _LAND_LIKE_DIES_SRC
        )
        assert returncode == -signal.SIGUSR1, (returncode, _stdout, _stderr)
        assert not dump_path.exists()

    # frob:tests tests/unit/test_land_stackdump.py::TestLandLikeSubprocessSigusr1.test_survives_with_a_dump_after_the_fix  # noqa: E501
    def test_survives_with_a_dump_after_the_fix(self, tmp_path: Path) -> None:
        """FAILS AT PARENT (BUG002 repro): before T-4494,
        `install_stackdump_handler` has no `force` parameter at all, so
        this subprocess raises `TypeError` immediately and never reaches
        its own `time.sleep`/survives-the-signal/writes-a-dump behavior
        this assertion requires. After the fix, the subprocess installs
        the handler unconditionally, survives `SIGUSR1` (exits 0, prints
        "survived"), and leaves a dump file behind -- the exact
        `frob ticket land` behavior this ticket adds."""
        returncode, stdout, _stderr, dump_path = _spawn_and_signal(
            tmp_path, _LAND_LIKE_SURVIVES_SRC
        )
        assert returncode == 0, (returncode, stdout, _stderr)
        assert "survived" in stdout
        assert dump_path.is_file(), _stderr
        assert "SIGUSR1 stack dump" in dump_path.read_text(encoding="utf-8")


class TestSilentPhaseDumpThreshold:
    """`_land_silent_phase_dump_threshold_s` (T-4494): reads `[tool.frob]
    land_silent_phase_dump_s` from `root/pyproject.toml`, defaulting to
    600.0 seconds."""

    # frob:tests tests/unit/test_land_stackdump.py::TestSilentPhaseDumpThreshold.test_default_when_key_absent  # noqa: E501
    # frob:tests src/frob/app/ticket_runner/_land_cmd.py::_land_silent_phase_dump_threshold_s  # noqa: E501
    def test_default_when_key_absent(self, tmp_path: Path) -> None:
        """No `pyproject.toml` at all -> the documented 600.0s default."""
        assert _land_cmd._land_silent_phase_dump_threshold_s(tmp_path) == 600.0

    # frob:tests tests/unit/test_land_stackdump.py::TestSilentPhaseDumpThreshold.test_reads_configured_value  # noqa: E501
    # frob:tests src/frob/app/ticket_runner/_land_cmd.py::_land_silent_phase_dump_threshold_s  # noqa: E501
    def test_reads_configured_value(self, tmp_path: Path) -> None:
        """A configured `[tool.frob] land_silent_phase_dump_s` value is
        read back exactly, as a float."""
        (tmp_path / "pyproject.toml").write_text(
            "[tool.frob]\nland_silent_phase_dump_s = 45\n", encoding="utf-8"
        )
        assert _land_cmd._land_silent_phase_dump_threshold_s(tmp_path) == 45.0

    # frob:tests tests/unit/test_land_stackdump.py::TestSilentPhaseDumpThreshold.test_malformed_toml_degrades_to_default  # noqa: E501
    def test_malformed_toml_degrades_to_default(self, tmp_path: Path) -> None:
        """A `pyproject.toml` that fails to parse degrades to the same
        600.0s default as a missing file -- never a raised exception."""
        (tmp_path / "pyproject.toml").write_text("not [ valid toml", encoding="utf-8")
        assert _land_cmd._land_silent_phase_dump_threshold_s(tmp_path) == 600.0


class TestSilentPhaseWatchdog:
    """`_land_silent_phase_watchdog` (T-4494): self-dumps once per silence
    episode once no phase log line has fired for the given threshold."""

    def setup_method(self) -> None:
        """Each test gets its own clock state -- these are the same
        module globals `_LandPhaseElapsedFilter` writes during a real
        land, and must never leak between tests (same posture
        `tests/unit/test_land_phase_elapsed_logging.py` already takes
        for `_land_phase_timer_start`)."""
        _land_cmd._land_phase_timer_start = None
        _land_cmd._land_last_phase_log_at = None

    def teardown_method(self) -> None:
        """Leave no timer state behind for tests outside this module."""
        _land_cmd._land_phase_timer_start = None
        _land_cmd._land_last_phase_log_at = None

    # frob:tests tests/unit/test_land_stackdump.py::TestSilentPhaseWatchdog.test_fires_once_after_threshold_then_waits_for_next_episode  # noqa: E501
    # frob:tests src/frob/app/ticket_runner/_land_cmd.py::_land_silent_phase_watchdog
    def test_fires_once_after_threshold_then_waits_for_next_episode(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """With a tiny threshold and a fast poll, the watchdog dumps
        exactly once while the silence continues (never once per poll
        tick), then dumps AGAIN only once a fresh phase log line resets
        the episode and the silence threshold passes a second time."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(_land_cmd, "_LAND_SILENT_PHASE_WATCHDOG_POLL_S", 0.05)
        _land_cmd._land_phase_timer_start = time.perf_counter()

        stop_event = threading.Event()
        thread = threading.Thread(
            target=_land_cmd._land_silent_phase_watchdog,
            args=(0.15, stop_event),
            daemon=True,
        )
        thread.start()
        try:
            time.sleep(0.5)
            dump_path = tmp_path / ".frob" / "stackdumps" / f"pid-{_pid()}.txt"
            assert dump_path.is_file()
            first_dump_count = dump_path.read_text(encoding="utf-8").count(
                "silent-phase watchdog self-dump"
            )
            assert first_dump_count == 1, "must dump once, not once per poll tick"

            time.sleep(0.3)
            assert (
                dump_path.read_text(encoding="utf-8").count(
                    "silent-phase watchdog self-dump"
                )
                == 1
            ), "must stay quiet for the rest of the SAME silence episode"

            # A fresh phase line starts a new episode.
            _land_cmd._land_last_phase_log_at = time.perf_counter()
            time.sleep(0.5)
            second_dump_count = dump_path.read_text(encoding="utf-8").count(
                "silent-phase watchdog self-dump"
            )
            assert second_dump_count == 2, "a new episode must dump again"
        finally:
            stop_event.set()
            thread.join(timeout=5)

    # frob:tests tests/unit/test_land_stackdump.py::TestSilentPhaseWatchdog.test_never_fires_while_phase_lines_keep_arriving  # noqa: E501
    # frob:tests src/frob/app/ticket_runner/_land_cmd.py::_land_silent_phase_watchdog
    def test_never_fires_while_phase_lines_keep_arriving(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A land that keeps emitting phase lines faster than the
        threshold never trips the watchdog at all -- no dump file is
        ever written."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(_land_cmd, "_LAND_SILENT_PHASE_WATCHDOG_POLL_S", 0.05)
        _land_cmd._land_phase_timer_start = time.perf_counter()
        _land_cmd._land_last_phase_log_at = time.perf_counter()

        stop_event = threading.Event()
        thread = threading.Thread(
            target=_land_cmd._land_silent_phase_watchdog,
            args=(0.3, stop_event),
            daemon=True,
        )
        thread.start()
        try:
            deadline = time.perf_counter() + 0.6
            while time.perf_counter() < deadline:
                time.sleep(0.05)
                _land_cmd._land_last_phase_log_at = time.perf_counter()
            dump_path = tmp_path / ".frob" / "stackdumps" / f"pid-{_pid()}.txt"
            assert not dump_path.exists()
        finally:
            stop_event.set()
            thread.join(timeout=5)


class TestStartLandSilentPhaseWatchdog:
    """`_start_land_silent_phase_watchdog` (T-4494): the daemon-thread
    starter `_land` calls."""

    # frob:tests tests/unit/test_land_stackdump.py::TestStartLandSilentPhaseWatchdog.test_returns_a_started_daemon_thread_and_stop_event  # noqa: E501
    def test_returns_a_started_daemon_thread_and_stop_event(
        self, tmp_path: Path
    ) -> None:
        """Returns an already-`start()`-ed daemon `Thread` plus the
        `Event` that stops it; setting the event and joining leaves no
        thread running."""
        thread, stop_event = _land_cmd._start_land_silent_phase_watchdog(tmp_path)
        try:
            assert thread.daemon is True
            assert thread.is_alive()
        finally:
            stop_event.set()
            thread.join(timeout=5)
        assert not thread.is_alive()
