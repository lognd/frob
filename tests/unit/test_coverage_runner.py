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
