"""Unit tests for `frob.verify._drain` (T-2310): the rapid profile's
automatic watermark drain -- spawn machinery plus the detached child's
own run body, gated on "no land in progress", advancing the watermark in
bounded, resumable rounds, never blocking a land.

`run_drain_async` deferred-imports `frob.tickets._leases._probe_land_once`
and `frob.verify._worker.run_coalesced_verification` INSIDE its own body
(matching `frob.app.ticket_runner._land_cmd`'s existing deferred-import
convention for `frob.verify`, and `tests/unit/test_land_cmd_backpressure.
py`'s own precedent for testing it), so every test here monkeypatches
those two names directly on their OWNING module objects -- patching
`frob.verify._drain`'s own namespace would have no effect, since the
`from ... import ...` statement re-reads the owning module's attributes
at CALL time, not at `frob.verify._drain` import time."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from typani.result import Err, Ok

import frob.tickets._leases as leases_mod
import frob.verify._worker as worker_mod
from frob.tickets._leases import LeaseError
from frob.verify._drain import (
    DrainError,
    run_drain_async,
    spawn_deferred_drain,
)
from frob.verify._watermark import (
    advance_watermark,
    load_watermark,
    record_intent,
)
from frob.verify._worker import WorkerOutcome


class TestRunDrainAsync:
    """`run_drain_async`: the detached `drain-async` child's own body --
    T-2310's constraints 3 (idle-fleet-only) and 4 (bounded, resumable)."""

    def test_declines_while_a_land_is_in_progress(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/verify/_drain.py::run_drain_async kind="unit"
        # Must-still-refuse (T-2406): a GENUINELY different land (no
        # exclude_pid given, so nothing is exempted) still declines to
        # run concurrently -- and never falls through to
        # run_coalesced_verification at all. wait_timeout_s=0 keeps the
        # test fast: the bounded wait/retry itself is exercised by
        # `refuse_if_land_in_progress`'s own test suite, not re-tested
        # here.
        monkeypatch.setattr(
            leases_mod,
            "_probe_land_once",
            lambda root, *, quiet, **kw: Err(LeaseError.LandInProgress),
        )
        calls: list[Path] = []
        monkeypatch.setattr(
            worker_mod,
            "run_coalesced_verification",
            lambda root, **kw: calls.append(root) or Ok(WorkerOutcome(status="empty")),
        )
        result = run_drain_async(tmp_path, land_ticket_id="T-9001", wait_timeout_s=0.0)
        assert result.is_err
        assert result.danger_err is DrainError.LandInProgress
        assert calls == []

    def test_a_genuinely_different_land_is_recorded_not_discarded(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/verify/_drain.py::run_drain_async kind="unit"
        # T-2406 criterion 1/4: a refusal caused by a genuinely different
        # land is OBSERVABLE afterward via `load_drain_refusal`, never
        # silently discarded the way the pre-fix "not queuing, not
        # retrying" log line was.
        from frob.verify._drain import load_drain_refusal

        monkeypatch.setattr(
            leases_mod,
            "_probe_land_once",
            lambda root, *, quiet, **kw: Err(LeaseError.LandInProgress),
        )
        assert load_drain_refusal(tmp_path) is None

        result = run_drain_async(tmp_path, land_ticket_id="T-9001", wait_timeout_s=0.0)
        assert result.is_err

        refusal = load_drain_refusal(tmp_path)
        assert refusal is not None
        assert refusal.refused_since_watermark == 1
        assert refusal.last_refused_ticket_id == "T-9001"

        # A second refusal increments the SAME record rather than
        # overwriting it with a fresh count of 1.
        run_drain_async(tmp_path, land_ticket_id="T-9001", wait_timeout_s=0.0)
        refusal = load_drain_refusal(tmp_path)
        assert refusal is not None
        assert refusal.refused_since_watermark == 2

    def test_excludes_its_own_originating_land_pid(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/verify/_drain.py::run_drain_async kind="unit"
        # Must-now-run (T-2406): a drain spawned BY its own land (the
        # SAME pid the process scan would otherwise find still running,
        # e.g. mid-cleanup) must run rather than self-refuse, once that
        # pid is passed as `exclude_pid`. This proves the exemption is
        # scoped to the ONE pid given, not "any land": the fake probe
        # below still refuses for every OTHER pid.
        seen_exclude_pids: list[int | None] = []

        def _fake_probe(root, *, quiet, exclude_pid=None):  # noqa: ANN001, ANN201
            seen_exclude_pids.append(exclude_pid)
            if exclude_pid == 424242:
                return Ok(None)
            return Err(LeaseError.LandInProgress)

        monkeypatch.setattr(leases_mod, "_probe_land_once", _fake_probe)
        calls: list[Path] = []
        monkeypatch.setattr(
            worker_mod,
            "run_coalesced_verification",
            lambda root, **kw: calls.append(root) or Ok(WorkerOutcome(status="empty")),
        )

        result = run_drain_async(tmp_path, exclude_pid=424242)
        assert result.is_ok
        assert len(calls) == 1
        assert 424242 in seen_exclude_pids

        # A DIFFERENT exclude_pid (a genuinely different land, not this
        # drain's own originating one) still refuses.
        result_other = run_drain_async(
            tmp_path, exclude_pid=999, wait_timeout_s=0.0
        )
        assert result_other.is_err

    def test_never_blocks_or_loops_over_the_backlog(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/verify/_drain.py::run_drain_async kind="unit"
        # Must-still-pass (4): run_coalesced_verification is called
        # EXACTLY ONCE per run_drain_async invocation -- never a loop.
        monkeypatch.setattr(
            leases_mod, "_probe_land_once", lambda root, *, quiet, **kw: Ok(None)
        )
        calls: list[Path] = []

        def _fake(root, **kw):  # noqa: ANN001, ANN201
            calls.append(root)
            return Ok(WorkerOutcome(status="empty"))

        monkeypatch.setattr(worker_mod, "run_coalesced_verification", _fake)
        result = run_drain_async(tmp_path)
        assert result.is_ok
        assert len(calls) == 1


class TestSpawnDeferredDrain:
    """`spawn_deferred_drain`: the land-side detached spawn -- T-2310
    constraint 1 (never blocks the caller)."""

    def test_spawns_a_detached_child(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/verify/_drain.py::spawn_deferred_drain kind="unit"
        monkeypatch.setattr("frob.process.exec_enabled", lambda: True, raising=False)

        class _FakeProc:
            pid = 4242

        calls: list[list[str]] = []

        def _fake_popen(argv, **kw):  # noqa: ANN001, ANN201
            calls.append(argv)
            return _FakeProc()

        monkeypatch.setattr(subprocess, "Popen", _fake_popen)
        result = spawn_deferred_drain(tmp_path, "T-9000")
        assert result.is_ok
        assert result.danger_ok == 4242
        assert len(calls) == 1
        assert "drain-async" in calls[0]

    def test_exec_disabled_refuses_without_spawning(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/verify/_drain.py::spawn_deferred_drain kind="unit"
        monkeypatch.setattr("frob.process.exec_enabled", lambda: False, raising=False)
        calls: list[object] = []
        monkeypatch.setattr(
            subprocess, "Popen", lambda *a, **kw: calls.append(1) or object()
        )
        result = spawn_deferred_drain(tmp_path, "T-9000")
        assert result.is_err
        assert result.danger_err is DrainError.SpawnRefused
        assert calls == []


class TestDrainAdvancesWatermarkEndToEnd:
    """T-2310 positive control (1) and (3), exercised through the real
    (non-monkeypatched) `run_coalesced_verification` -- proves the
    watermark genuinely advances, and that a killed/unmeasurable round
    leaves it valid rather than corrupt."""

    def test_green_round_advances_watermark_a_subsequent_round_sees(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/verify/_drain.py::run_drain_async kind="unit"
        monkeypatch.setattr(
            leases_mod, "_probe_land_once", lambda root, *, quiet, **kw: Ok(None)
        )
        record_intent(
            tmp_path,
            commit_sha="c1",
            ticket_id="T-0001",
            touched_symbols=("a.py::fn",),
            profile="rapid",
        )
        from frob.app.ticket_runner import _rapid_sweep

        _rapid_sweep._write_baseline(tmp_path, frozenset({("RULE1", "a.py")}), "seed")

        real_run = worker_mod.run_coalesced_verification

        def _green(root, **kw):  # noqa: ANN001, ANN201
            return real_run(
                root, verify_fn=lambda r, sha: frozenset({("RULE1", "a.py")})
            )

        monkeypatch.setattr(worker_mod, "run_coalesced_verification", _green)

        result = run_drain_async(tmp_path)
        assert result.is_ok
        assert result.danger_ok.status == "green"
        assert result.danger_ok.advanced_watermark is True

        # Positive control (1): a SUBSEQUENT sweep/status read baselines
        # against the FRESH watermark, not the old one.
        watermark = load_watermark(tmp_path)
        assert watermark.is_ok
        assert watermark.danger_ok is not None
        assert watermark.danger_ok.commit_sha == "c1"

    def test_a_round_that_runs_clears_a_prior_refusal_record(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/verify/_drain.py::run_drain_async kind="unit"
        # T-2406 criterion 4's complement: once a drain actually RUNS
        # (the "genuinely blocked" state is resolved), the refused-
        # since-watermark counter resets to zero rather than staying
        # stuck reporting a stale count forever.
        from frob.verify._drain import load_drain_refusal, record_drain_refusal

        record_drain_refusal(tmp_path, ticket_id="T-8999")
        seeded = load_drain_refusal(tmp_path)
        assert seeded is not None
        assert seeded.refused_since_watermark == 1

        monkeypatch.setattr(
            leases_mod, "_probe_land_once", lambda root, *, quiet, **kw: Ok(None)
        )
        record_intent(
            tmp_path,
            commit_sha="c1",
            ticket_id="T-0001",
            touched_symbols=("a.py::fn",),
            profile="rapid",
        )
        from frob.app.ticket_runner import _rapid_sweep

        _rapid_sweep._write_baseline(tmp_path, frozenset({("RULE1", "a.py")}), "seed")

        real_run = worker_mod.run_coalesced_verification

        def _green(root, **kw):  # noqa: ANN001, ANN201
            return real_run(
                root, verify_fn=lambda r, sha: frozenset({("RULE1", "a.py")})
            )

        monkeypatch.setattr(worker_mod, "run_coalesced_verification", _green)

        result = run_drain_async(tmp_path)
        assert result.is_ok

        refusal = load_drain_refusal(tmp_path)
        assert refusal is not None
        assert refusal.refused_since_watermark == 0

    def test_unmeasurable_round_leaves_watermark_untouched_not_corrupt(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/verify/_drain.py::run_drain_async kind="unit"
        # Positive control (3): a round that cannot complete (the
        # closest reachable proxy for "interrupted mid-batch" without
        # actually killing a process) leaves a VALID watermark -- here,
        # a pre-existing one is untouched, never rolled back or torn.
        monkeypatch.setattr(
            leases_mod, "_probe_land_once", lambda root, *, quiet, **kw: Ok(None)
        )
        advance_watermark(
            tmp_path, commit_sha="c0", run_id="seed-run", baseline_digest="seed"
        )
        record_intent(
            tmp_path,
            commit_sha="c1",
            ticket_id="T-0001",
            touched_symbols=("a.py::fn",),
            profile="rapid",
        )

        real_run = worker_mod.run_coalesced_verification

        def _unmeasurable(root, **kw):  # noqa: ANN001, ANN201
            return real_run(root, verify_fn=lambda r, sha: None)

        monkeypatch.setattr(worker_mod, "run_coalesced_verification", _unmeasurable)

        result = run_drain_async(tmp_path)
        assert result.is_err

        watermark = load_watermark(tmp_path)
        assert watermark.is_ok
        assert watermark.danger_ok is not None
        assert watermark.danger_ok.commit_sha == "c0"  # untouched, still valid
