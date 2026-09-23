"""Batched/rate-limited post-land sweep window tests (T-4414) for
`frob.app.ticket_runner._rapid_sweep`'s window-state machine: state I/O,
the pure registration decision, the sweep-window lock, and the
configurable window length."""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from frob.app.ticket_runner._rapid_sweep import (
    _decide_land_registration,
    _default_window_state,
    _read_window_state,
    _sweep_window_seconds,
    _window_lock,
    _write_window_state,
)


def _land(ticket_id: str = "T-0001") -> dict:
    """One fake land registration payload, shaped like the dict
    `spawn_deferred_post_land_sweep` builds from its own arguments."""
    return {
        "ticket_id": ticket_id,
        "final_id": ticket_id,
        "commit_sha": "deadbeef" * 5,
        "target_branch": None,
    }


# frob:ticket T-4414
class TestWindowStateIo:
    """`_read_window_state`/`_write_window_state` round-trip and degrade
    to the idle default on absence or corruption."""

    # frob:tests tests/unit/rapid_sweep_suite/test_window.py::TestWindowStateIo.test_missing_file_is_the_default_idle_state  # noqa: E501
    # frob:tests src/frob/app/ticket_runner/_rapid_sweep.py::_read_window_state
    def test_missing_file_is_the_default_idle_state(self, tmp_path: Path) -> None:
        assert _read_window_state(tmp_path) == _default_window_state()

    # frob:tests tests/unit/rapid_sweep_suite/test_window.py::TestWindowStateIo.test_round_trips  # noqa: E501
    # frob:tests src/frob/app/ticket_runner/_rapid_sweep.py::_read_window_state
    def test_round_trips(self, tmp_path: Path) -> None:
        state = {
            "phase": "window_open",
            "window_opened_at": 123.0,
            "worker_pid": 4242,
            "pending_lands": [_land("T-0001"), _land("T-0002")],
        }
        _write_window_state(tmp_path, state)
        assert _read_window_state(tmp_path) == state

    # frob:tests tests/unit/rapid_sweep_suite/test_window.py::TestWindowStateIo.test_corrupt_file_degrades_to_the_default_idle_state  # noqa: E501
    # frob:tests src/frob/app/ticket_runner/_rapid_sweep.py::_read_window_state
    def test_corrupt_file_degrades_to_the_default_idle_state(
        self, tmp_path: Path
    ) -> None:
        path = tmp_path / ".frob" / "rapid-sweep-window.json"
        path.parent.mkdir(parents=True)
        path.write_text("not json{{{", encoding="utf-8")
        assert _read_window_state(tmp_path) == _default_window_state()


# frob:ticket T-4414
class TestDecideLandRegistration:
    """`_decide_land_registration` -- the pure core of acceptance
    criteria 1 (one sweep covers two lands within a window) and 3 (a
    land arriving while a sweep runs never spawns a second concurrent
    sweep)."""

    # frob:tests tests/unit/rapid_sweep_suite/test_window.py::TestDecideLandRegistration.test_idle_opens_a_new_window  # noqa: E501
    # frob:tests src/frob/app/ticket_runner/_rapid_sweep.py::_decide_land_registration
    def test_idle_opens_a_new_window(self) -> None:
        action, new_state = _decide_land_registration(
            _default_window_state(), _land("T-0001"), now=100.0
        )
        assert action == "open"
        assert new_state["phase"] == "window_open"
        assert new_state["window_opened_at"] == 100.0
        assert new_state["pending_lands"] == [_land("T-0001")]
        assert new_state["worker_pid"] is None

    # frob:tests tests/unit/rapid_sweep_suite/test_window.py::TestDecideLandRegistration.test_second_land_within_window_joins_it  # noqa: E501
    # frob:tests src/frob/app/ticket_runner/_rapid_sweep.py::_decide_land_registration
    def test_second_land_within_window_joins_it(self) -> None:
        state = {
            "phase": "window_open",
            "window_opened_at": 100.0,
            "worker_pid": os.getpid(),
            "pending_lands": [_land("T-0001")],
        }
        action, new_state = _decide_land_registration(state, _land("T-0002"), now=105.0)
        assert action == "join"
        # Exactly one worker's batch now covers both lands -- criterion 1.
        assert new_state["pending_lands"] == [_land("T-0001"), _land("T-0002")]
        assert new_state["worker_pid"] == os.getpid()

    # frob:tests tests/unit/rapid_sweep_suite/test_window.py::TestDecideLandRegistration.test_land_while_sweep_running_defers_to_next_window  # noqa: E501
    # frob:tests src/frob/app/ticket_runner/_rapid_sweep.py::_decide_land_registration
    def test_land_while_sweep_running_defers_to_next_window(self) -> None:
        state = {
            "phase": "sweep_running",
            "window_opened_at": 100.0,
            "worker_pid": os.getpid(),
            "pending_lands": [],
        }
        action, new_state = _decide_land_registration(state, _land("T-0003"), now=150.0)
        assert action == "defer"
        # Never a second concurrent sweep -- criterion 3: no new worker
        # pid is introduced, the land only joins the pending batch.
        assert new_state["worker_pid"] == os.getpid()
        assert new_state["pending_lands"] == [_land("T-0003")]

    # frob:tests tests/unit/rapid_sweep_suite/test_window.py::TestDecideLandRegistration.test_dead_worker_pid_is_reaped_and_a_new_window_opens  # noqa: E501
    # frob:tests src/frob/app/ticket_runner/_rapid_sweep.py::_decide_land_registration
    def test_dead_worker_pid_is_reaped_and_a_new_window_opens(self) -> None:
        # `worker_pid=None` names no live process -- the same code path
        # a genuinely crashed worker's PID takes once `pid_alive` reports
        # it dead.
        state = {
            "phase": "sweep_running",
            "window_opened_at": 10.0,
            "worker_pid": None,
            "pending_lands": [_land("T-0001")],
        }
        action, new_state = _decide_land_registration(state, _land("T-0004"), now=200.0)
        assert action == "open"
        # The reaped land's own pending entry is REPLACED, not preserved
        # unattended -- opening a new window starts a fresh batch that
        # includes only the land that just triggered the reap. Any land
        # truly lost this way is still safe: `record_rapid_debt` (the
        # caller's own first step, unaffected by this ticket) already
        # recorded it as unswept before this decision ever runs.
        assert new_state["pending_lands"] == [_land("T-0004")]

    # frob:tests tests/unit/rapid_sweep_suite/test_window.py::TestDecideLandRegistration.test_expired_window_with_a_still_alive_worker_still_joins  # noqa: E501
    # frob:tests src/frob/app/ticket_runner/_rapid_sweep.py::_decide_land_registration
    def test_expired_window_with_a_still_alive_worker_still_joins(self) -> None:
        state = {
            "phase": "window_open",
            "window_opened_at": 0.0,
            "worker_pid": os.getpid(),
            "pending_lands": [_land("T-0001")],
        }
        # `now` is far past any plausible window length -- the live
        # worker (not a second clock racing it) is still the authority
        # on when it actually wakes.
        action, new_state = _decide_land_registration(
            state, _land("T-0005"), now=1_000_000.0
        )
        assert action == "join"
        assert new_state["pending_lands"] == [_land("T-0001"), _land("T-0005")]


# frob:ticket T-4414
class TestWindowLock:
    """`_window_lock` -- the same cross-process advisory-lock primitive
    `_baseline_lock` uses, pointed at a dedicated `.frob/` lock file."""

    # frob:tests tests/unit/rapid_sweep_suite/test_window.py::TestWindowLock.test_serializes_two_concurrent_holders  # noqa: E501
    # frob:tests src/frob/app/ticket_runner/_rapid_sweep.py::_window_lock
    def test_serializes_two_concurrent_holders(self, tmp_path: Path) -> None:
        order: list[str] = []
        with _window_lock(tmp_path, timeout=2.0):
            order.append("first-acquired")
            # A second acquire attempt with a short timeout on the SAME
            # lock file, from within the first's own critical section,
            # must degrade (log+proceed) rather than hang forever.
            start = time.monotonic()
            with _window_lock(tmp_path, timeout=0.2):
                order.append("second-degraded-without-lock")
            assert time.monotonic() - start < 5.0
        assert order == ["first-acquired", "second-degraded-without-lock"]

    # frob:tests tests/unit/rapid_sweep_suite/test_window.py::TestWindowLock.test_creates_a_dedicated_lock_file_not_the_baseline_lock  # noqa: E501
    def test_creates_a_dedicated_lock_file_not_the_baseline_lock(
        self, tmp_path: Path
    ) -> None:
        with _window_lock(tmp_path):
            pass
        assert (tmp_path / ".frob" / "rapid-sweep-window.lock").exists()
        assert not (tmp_path / ".frob" / "rapid-sweep-baseline.lock").exists()


# frob:ticket T-4414
class TestSweepWindowSeconds:
    """`_sweep_window_seconds` -- `[tool.frob]`/`frob.toml` configurable
    batching window, following `check_runner.py`'s frob.toml-read
    pattern (T-1038)."""

    # frob:tests tests/unit/rapid_sweep_suite/test_window.py::TestSweepWindowSeconds.test_default_when_no_config_present  # noqa: E501
    # frob:tests src/frob/app/ticket_runner/_rapid_sweep.py::_sweep_window_seconds
    def test_default_when_no_config_present(self, tmp_path: Path) -> None:
        from frob.app.ticket_runner._rapid_sweep import (
            _DEFAULT_SWEEP_WINDOW_SECONDS,
        )

        assert _sweep_window_seconds(tmp_path) == _DEFAULT_SWEEP_WINDOW_SECONDS

    # frob:tests tests/unit/rapid_sweep_suite/test_window.py::TestSweepWindowSeconds.test_frob_toml_sweep_section_wins  # noqa: E501
    # frob:tests src/frob/app/ticket_runner/_rapid_sweep.py::_sweep_window_seconds
    def test_frob_toml_sweep_section_wins(self, tmp_path: Path) -> None:
        (tmp_path / "frob.toml").write_text(
            "[sweep]\nwindow_seconds = 45\n", encoding="utf-8"
        )
        assert _sweep_window_seconds(tmp_path) == 45.0

    # frob:tests tests/unit/rapid_sweep_suite/test_window.py::TestSweepWindowSeconds.test_frob_toml_top_level_key_wins  # noqa: E501
    # frob:tests src/frob/app/ticket_runner/_rapid_sweep.py::_sweep_window_seconds
    def test_frob_toml_top_level_key_wins(self, tmp_path: Path) -> None:
        (tmp_path / "frob.toml").write_text(
            "rapid_sweep_window_seconds = 30\n", encoding="utf-8"
        )
        assert _sweep_window_seconds(tmp_path) == 30.0

    # frob:tests tests/unit/rapid_sweep_suite/test_window.py::TestSweepWindowSeconds.test_pyproject_tool_frob_table_is_the_fallback  # noqa: E501
    # frob:tests src/frob/app/ticket_runner/_rapid_sweep.py::_sweep_window_seconds
    def test_pyproject_tool_frob_table_is_the_fallback(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text(
            "[tool.frob]\nrapid_sweep_window_seconds = 60\n", encoding="utf-8"
        )
        assert _sweep_window_seconds(tmp_path) == 60.0

    # frob:tests tests/unit/rapid_sweep_suite/test_window.py::TestSweepWindowSeconds.test_malformed_frob_toml_falls_back_to_the_default  # noqa: E501
    def test_malformed_frob_toml_falls_back_to_the_default(
        self, tmp_path: Path
    ) -> None:
        from frob.app.ticket_runner._rapid_sweep import (
            _DEFAULT_SWEEP_WINDOW_SECONDS,
        )

        (tmp_path / "frob.toml").write_text("not [ valid toml", encoding="utf-8")
        assert _sweep_window_seconds(tmp_path) == _DEFAULT_SWEEP_WINDOW_SECONDS


# frob:ticket T-4414
class TestSpawnDeferredPostLandSweepBatches:
    """`spawn_deferred_post_land_sweep` -- integration-shaped tests
    proving acceptance criteria 1 and 3 through the PUBLIC entry point a
    land actually calls, with the detached `Popen` itself stubbed out
    (this suite never spawns a real subprocess)."""

    @pytest.fixture(autouse=True)
    def _no_debt(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "frob.tickets._evidence.record_rapid_debt", lambda *a, **k: None
        )
        monkeypatch.setattr(
            "frob.app.ticket_runner._rapid_sweep._commit_rapid_debt",
            lambda *a, **k: None,
        )
        monkeypatch.setattr("frob.process.exec_enabled", lambda: True)

    # frob:tests tests/unit/rapid_sweep_suite/test_window.py::TestSpawnDeferredPostLandSweepBatches.test_two_lands_in_one_window_spawn_exactly_one_worker  # noqa: E501
    def test_two_lands_in_one_window_spawn_exactly_one_worker(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from frob.app.ticket_runner._rapid_sweep import (
            spawn_deferred_post_land_sweep,
        )

        spawn_calls: list[int] = []

        # The fake worker pid must actually be alive for `pid_alive` to
        # agree a worker is running -- this test's own process qualifies
        # and is simplest, unlike an arbitrary literal PID that may or
        # may not exist on the machine running the suite.
        fake_worker_pid = os.getpid()

        def _fake_spawn(root, final_id, commit_sha, target_branch):  # noqa: ANN001, ANN202
            spawn_calls.append(1)
            from typani import Ok

            return Ok(fake_worker_pid)

        monkeypatch.setattr(
            "frob.app.ticket_runner._rapid_sweep._spawn_sweep_worker", _fake_spawn
        )

        first = spawn_deferred_post_land_sweep(tmp_path, "T-1001", "T-1001", "a" * 40)
        second = spawn_deferred_post_land_sweep(tmp_path, "T-1002", "T-1002", "b" * 40)

        assert first.is_ok and first.danger_ok == fake_worker_pid
        # Criterion 1: the second land within the SAME window joins
        # instead of spawning -- only one real spawn happened.
        assert second.is_ok and second.danger_ok == -1
        assert len(spawn_calls) == 1

        state = _read_window_state(tmp_path)
        assert state["phase"] == "window_open"
        assert len(state["pending_lands"]) == 2
        assert {land["ticket_id"] for land in state["pending_lands"]} == {
            "T-1001",
            "T-1002",
        }

    # frob:tests tests/unit/rapid_sweep_suite/test_window.py::TestSpawnDeferredPostLandSweepBatches.test_land_while_sweep_running_never_spawns_a_second_worker  # noqa: E501
    def test_land_while_sweep_running_never_spawns_a_second_worker(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from frob.app.ticket_runner._rapid_sweep import (
            spawn_deferred_post_land_sweep,
        )

        _write_window_state(
            tmp_path,
            {
                "phase": "sweep_running",
                "window_opened_at": time.time(),
                "worker_pid": os.getpid(),
                "pending_lands": [],
            },
        )

        def _boom(*_a, **_k):  # noqa: ANN002, ANN003, ANN202
            raise AssertionError(
                "a second concurrent sweep worker must never be spawned"
            )

        monkeypatch.setattr(
            "frob.app.ticket_runner._rapid_sweep._spawn_sweep_worker", _boom
        )

        result = spawn_deferred_post_land_sweep(tmp_path, "T-2001", "T-2001", "c" * 40)
        assert result.is_ok and result.danger_ok == -1
        state = _read_window_state(tmp_path)
        assert state["phase"] == "sweep_running"
        assert len(state["pending_lands"]) == 1

    # frob:tests tests/unit/rapid_sweep_suite/test_window.py::TestSpawnDeferredPostLandSweepBatches.test_a_failed_spawn_leaves_the_window_state_unchanged  # noqa: E501
    def test_a_failed_spawn_leaves_the_window_state_unchanged(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from frob.app.ticket_runner._rapid_sweep import (
            RapidSweepError,
            spawn_deferred_post_land_sweep,
        )

        def _fake_spawn(*_a, **_k):  # noqa: ANN002, ANN003, ANN202
            from typani import Err

            return Err(RapidSweepError.SpawnRefused)

        monkeypatch.setattr(
            "frob.app.ticket_runner._rapid_sweep._spawn_sweep_worker", _fake_spawn
        )

        result = spawn_deferred_post_land_sweep(tmp_path, "T-3001", "T-3001", "d" * 40)
        assert result.is_err
        # A phantom "worker alive" state must never be persisted for a
        # spawn that never actually started.
        state = _read_window_state(tmp_path)
        assert state == _default_window_state()


# frob:ticket T-4414
class TestRunOneSweepBatch:
    """`_run_one_sweep_batch` -- acceptance criterion 2: a repo-wide
    finding from a batched sweep is filed and attributed to the WHOLE
    batch (every land the window collected), not pinned to whichever
    land's identity happened to spawn the worker."""

    # frob:tests tests/unit/rapid_sweep_suite/test_window.py::TestRunOneSweepBatch.test_anchors_on_the_batchs_own_last_land  # noqa: E501
    def test_anchors_on_the_batchs_own_last_land(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from frob.app.ticket_runner._rapid_sweep import _run_one_sweep_batch

        calls: list[tuple] = []

        def _fake_run(root, final_id, commit_sha):  # noqa: ANN001, ANN202
            calls.append((final_id, commit_sha))
            from typani import Ok

            return Ok(None)

        monkeypatch.setattr(
            "frob.app.ticket_runner._rapid_sweep.run_deferred_post_land_sweep",
            _fake_run,
        )
        monkeypatch.setattr(
            "frob.app.ticket_runner._rapid_sweep.sweep_stale_worktrees_after_land",
            lambda *a, **k: None,
        )

        batch = [_land("T-1001"), _land("T-1002")]
        batch[1]["commit_sha"] = "b" * 40
        fallback = {"final_id": "T-9999", "commit_sha": "f" * 40}

        unmeasurable = _run_one_sweep_batch(tmp_path, batch, fallback)

        assert unmeasurable is False
        # The MOST RECENT land in the batch is the anchor a filed
        # ticket's title/commit names -- not the first (whichever land
        # happened to open the window and spawn the worker), and not
        # the fallback (only used for a genuinely empty batch).
        assert calls == [("T-1002", "b" * 40)]

    # frob:tests tests/unit/rapid_sweep_suite/test_window.py::TestRunOneSweepBatch.test_empty_batch_uses_the_fallback_land  # noqa: E501
    def test_empty_batch_uses_the_fallback_land(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from frob.app.ticket_runner._rapid_sweep import _run_one_sweep_batch

        calls: list[tuple] = []

        def _fake_run(root, final_id, commit_sha):  # noqa: ANN001, ANN202
            calls.append((final_id, commit_sha))
            from typani import Ok

            return Ok(None)

        monkeypatch.setattr(
            "frob.app.ticket_runner._rapid_sweep.run_deferred_post_land_sweep",
            _fake_run,
        )
        monkeypatch.setattr(
            "frob.app.ticket_runner._rapid_sweep.sweep_stale_worktrees_after_land",
            lambda *a, **k: None,
        )

        fallback = {"final_id": "T-9999", "commit_sha": "f" * 40}
        _run_one_sweep_batch(tmp_path, [], fallback)
        assert calls == [("T-9999", "f" * 40)]

    # frob:tests tests/unit/rapid_sweep_suite/test_window.py::TestRunOneSweepBatch.test_unmeasurable_result_is_propagated  # noqa: E501
    def test_unmeasurable_result_is_propagated(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from frob.app.ticket_runner._rapid_sweep import (
            RapidSweepError,
            _run_one_sweep_batch,
        )

        def _fake_run(root, final_id, commit_sha):  # noqa: ANN001, ANN202
            from typani import Err

            return Err(RapidSweepError.Unmeasurable)

        monkeypatch.setattr(
            "frob.app.ticket_runner._rapid_sweep.run_deferred_post_land_sweep",
            _fake_run,
        )
        monkeypatch.setattr(
            "frob.app.ticket_runner._rapid_sweep.sweep_stale_worktrees_after_land",
            lambda *a, **k: None,
        )

        fallback = {"final_id": "T-9999", "commit_sha": "f" * 40}
        unmeasurable = _run_one_sweep_batch(tmp_path, [_land("T-1001")], fallback)
        assert unmeasurable is True
