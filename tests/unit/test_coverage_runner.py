"""T-1525: `frob.app.coverage_runner`'s CLI-facing exit-code behavior for
`frob coverage`."""

from __future__ import annotations

from pathlib import Path

import pytest
from typani import Err, Ok
from typani.unit import Unit

from frob.app import coverage_runner
from frob.app.config import AppConfig


# frob:ticket T-1525
class TestCoverageRunner:
    """`frob coverage`'s default (touched-set) path delegates to
    `run_coverage_wait`; `--full` calls `native_coverage_refresh` directly."""

    def _cfg(self, tmp_path: Path, *, full: bool = False) -> AppConfig:
        return AppConfig(coverage_path=tmp_path, coverage_full=full)

    def test_default_delegates_to_run_coverage_wait(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/app/coverage_runner.py::run kind="unit"
        import frob.testing._coverage_wait as wait_module

        calls: list[Path] = []

        def _fake_wait(root: Path, *, base: str = "HEAD", **kw):  # noqa: ANN202 -- test stub
            calls.append(root)
            return Ok(wait_module.CoverageWaitOutcome(ran=True, duration_s=1.5))

        monkeypatch.setattr(wait_module, "run_coverage_wait", _fake_wait)
        coverage_runner.run(self._cfg(tmp_path))  # must not raise
        assert calls == [tmp_path]

    # frob:ticket T-1572
    def test_base_threads_through_to_run_coverage_wait(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`--base` (T-1572) reaches `run_coverage_wait` as its own `base`
        kwarg -- default `AppConfig.coverage_base=None` becomes `"HEAD"`."""
        import frob.testing._coverage_wait as wait_module

        seen: dict = {}

        def _fake_wait(root: Path, *, base: str = "HEAD", **kw):  # noqa: ANN202
            seen["base"] = base
            return Ok(wait_module.CoverageWaitOutcome(ran=False, duration_s=0.0))

        monkeypatch.setattr(wait_module, "run_coverage_wait", _fake_wait)

        coverage_runner.run(self._cfg(tmp_path))
        assert seen["base"] == "HEAD"

        coverage_runner.run(
            AppConfig(coverage_path=tmp_path, coverage_base="origin/main")
        )
        assert seen["base"] == "origin/main"

    def test_full_calls_native_refresh_directly(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/app/coverage_runner.py::run kind="unit"
        import frob.graph as graph_module
        import frob.testing._coverage_refresh as refresh_module

        snapshot = object()
        monkeypatch.setattr(graph_module, "load_graph", lambda cache: Ok(snapshot))
        seen: dict = {}

        def _fake_refresh(root, snap, *, full=False, **kw):  # noqa: ANN001, ANN202
            seen["root"] = root
            seen["snapshot"] = snap
            seen["full"] = full
            return Ok(Unit())

        monkeypatch.setattr(refresh_module, "native_coverage_refresh", _fake_refresh)
        coverage_runner.run(self._cfg(tmp_path, full=True))  # must not raise
        assert seen == {"root": tmp_path, "snapshot": snapshot, "full": True}

    def test_run_failure_exits_nonzero(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/app/coverage_runner.py::run kind="unit"
        import frob.testing._coverage_wait as wait_module

        monkeypatch.setattr(
            wait_module,
            "run_coverage_wait",
            lambda root, **kw: Err(wait_module.CoverageWaitError.RunFailed),
        )
        with pytest.raises(SystemExit) as exc:
            coverage_runner.run(self._cfg(tmp_path))
        assert exc.value.code == 1


# frob:ticket T-3748
class TestCoverageFailOnDegraded:
    """`--fail-on-degraded` turns a RED suite (pytest exit != 0 that is NOT
    an xdist worker-crash) into a non-zero exit, so one `frob coverage
    --full --fail-on-degraded` can be CI's combined pass/fail + coverage
    run; a worker-crash (an environment abort the refresh recovers from) is
    NOT a real regression and must not fail the gate."""

    def _write_prov(self, root: Path, *, degraded: bool, worker_crash: bool) -> None:
        import json

        from frob.testing._coverage_refresh import _RUN_PROVENANCE_REL

        path = root / _RUN_PROVENANCE_REL
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "degraded": degraded,
                    "worker_crash": worker_crash,
                    "pytest_exit_code": 1 if degraded else 0,
                    "pytest_ran": True,
                    "aborted": False,
                    "abort_reason": None,
                }
            )
        )

    def test_red_suite_exits_nonzero(self, tmp_path: Path) -> None:
        # frob:tests src/frob/app/coverage_runner.py::_fail_if_suite_degraded kind="unit"  # noqa: E501
        self._write_prov(tmp_path, degraded=True, worker_crash=False)
        with pytest.raises(SystemExit) as exc:
            coverage_runner._fail_if_suite_degraded(tmp_path)
        assert exc.value.code == 1

    def test_worker_crash_does_not_fail(self, tmp_path: Path) -> None:
        # frob:tests src/frob/app/coverage_runner.py::_fail_if_suite_degraded kind="unit"  # noqa: E501
        # A killed xdist worker is degraded=True but worker_crash=True -- an
        # environment artifact the refresh recovers from serially, NOT a red
        # suite, so the gate must let it pass.
        self._write_prov(tmp_path, degraded=True, worker_crash=True)
        coverage_runner._fail_if_suite_degraded(tmp_path)  # must not raise

    def test_green_suite_returns(self, tmp_path: Path) -> None:
        # frob:tests src/frob/app/coverage_runner.py::_fail_if_suite_degraded kind="unit"  # noqa: E501
        self._write_prov(tmp_path, degraded=False, worker_crash=False)
        coverage_runner._fail_if_suite_degraded(tmp_path)  # must not raise

    def test_missing_provenance_fails_closed(self, tmp_path: Path) -> None:
        # frob:tests src/frob/app/coverage_runner.py::_fail_if_suite_degraded kind="unit"  # noqa: E501
        # No provenance file at all: cannot confirm the suite passed, so the
        # gate fails closed rather than green.
        with pytest.raises(SystemExit) as exc:
            coverage_runner._fail_if_suite_degraded(tmp_path)
        assert exc.value.code == 1
