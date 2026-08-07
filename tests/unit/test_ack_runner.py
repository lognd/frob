"""Direct-call coverage for `frob.app.ack_runner.run` (T-0160 TEST005 batch 10).

Complements `tests/test_ack_worktree_lease.py` (lease-guard branches only):
this file drives the no-refs error branch and the full success path (cache
build, lock load/write, facet-informational log), which the lease-focused
file does not exercise.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from frob.app.ack_runner import run
from frob.app.config import AppConfig


def _write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


_WIDGET_PY = '''class Widget:
    """A widget."""

    def render(self, value: int) -> str:
        """Render the widget."""
        # frob:doc docs/x.md#widget
        return str(value)
'''

# frob:ticket T-1317
# A real (non-boilerplate, non-blank) --reason for tests that need `run`
# to actually reach `acknowledge` rather than refuse at the T-1317 reason
# gate.
_REASON = "re-verified against the current render() body, still accurate"


class TestAckRunnerRun:
    def test_no_refs_exits_with_error(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests tests/unit/test_ack_runner.py::TestAckRunnerRun.test_no_refs_exits_with_error  # noqa: E501
        """`frob ack` with zero refs refuses before ever touching a graph."""
        caplog.set_level(logging.ERROR)
        cfg = AppConfig(ack_refs=[], ack_path=tmp_path)
        with pytest.raises(SystemExit):
            run(cfg)
        assert "requires at least one" in caplog.text

    def test_success_path_builds_cache_and_writes_lock(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests tests/unit/test_ack_runner.py::TestAckRunnerRun.test_success_path_builds_cache_and_writes_lock  # noqa: E501
        """No cache yet, no frob.lock yet, non-default --facet: still succeeds,
        builds the graph snapshot on the fly, and persists frob.lock."""
        caplog.set_level(logging.DEBUG)
        _write(tmp_path, "src/a.py", _WIDGET_PY)
        ref = "src/a.py::Widget.render"
        cfg = AppConfig(
            ack_refs=[ref], ack_path=tmp_path, ack_facet="body", ack_reason=_REASON
        )

        run(cfg)

        assert (tmp_path / "frob.lock").exists()
        assert f"acked {ref}" in caplog.text
        assert "is informational" in caplog.text

    def test_unresolvable_ref_exits_with_error(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests tests/unit/test_ack_runner.py::TestAckRunnerRun.test_unresolvable_ref_exits_with_error  # noqa: E501
        """A ref that resolves to nothing in the graph fails cleanly via
        `acknowledge`'s error branch, not a raised exception."""
        caplog.set_level(logging.ERROR)
        _write(tmp_path, "src/a.py", _WIDGET_PY)
        cfg = AppConfig(
            ack_refs=["src/a.py::NoSuchSymbol"], ack_path=tmp_path, ack_reason=_REASON
        )
        with pytest.raises(SystemExit):
            run(cfg)
        assert "ack failed" in caplog.text
        assert not (tmp_path / "frob.lock").exists()

    def test_graph_unavailable_after_failed_build_exits_with_error(
        self,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # frob:tests tests/unit/test_ack_runner.py::TestAckRunnerRun.test_graph_unavailable_after_failed_build_exits_with_error  # noqa: E501
        """When neither the cache load nor a fresh build succeeds, `run`
        exits loudly instead of proceeding with no snapshot."""
        import frob.graph as graph_mod
        from frob.graph import GraphError

        caplog.set_level(logging.ERROR)

        def _fail_build(root: Path, cache: Path):
            from typani import Err

            return Err(GraphError.CacheCorrupt)

        monkeypatch.setattr(graph_mod, "build_graph", _fail_build)
        cfg = AppConfig(ack_refs=["src/a.py::Widget.render"], ack_path=tmp_path)
        with pytest.raises(SystemExit):
            run(cfg)
        assert "graph unavailable" in caplog.text

    def test_malformed_lock_file_exits_with_error(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests tests/unit/test_ack_runner.py::TestAckRunnerRun.test_malformed_lock_file_exits_with_error  # noqa: E501
        """A pre-existing but malformed `frob.lock` fails the load-lock
        step before any acknowledgement is attempted."""
        caplog.set_level(logging.ERROR)
        _write(tmp_path, "src/a.py", _WIDGET_PY)
        _write(tmp_path, "frob.lock", "{not valid json")
        cfg = AppConfig(ack_refs=["src/a.py::Widget.render"], ack_path=tmp_path)
        with pytest.raises(SystemExit):
            run(cfg)
        assert "frob.lock" in caplog.text

    def test_write_lock_failure_exits_with_error(
        self,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # frob:tests tests/unit/test_ack_runner.py::TestAckRunnerRun.test_write_lock_failure_exits_with_error  # noqa: E501
        """A successful acknowledge whose lock write fails (simulated OS
        error) still exits loudly rather than silently dropping the ack."""
        import os

        caplog.set_level(logging.ERROR)
        _write(tmp_path, "src/a.py", _WIDGET_PY)
        real_replace = os.replace

        def _boom(src, dst):  # noqa: ANN001
            if str(dst).endswith("frob.lock"):
                raise OSError("simulated write failure")
            return real_replace(src, dst)

        monkeypatch.setattr(os, "replace", _boom)
        cfg = AppConfig(
            ack_refs=["src/a.py::Widget.render"], ack_path=tmp_path, ack_reason=_REASON
        )
        with pytest.raises(SystemExit):
            run(cfg)
        assert "could not write frob.lock" in caplog.text
