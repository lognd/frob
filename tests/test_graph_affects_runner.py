"""Direct-call coverage for `frob graph affects` (T-0628, `frob.app.graph_runner._run_affects`):
the CLI counterpart to `frob.graph.affects.affects` that T-0325 cut as out
of scope (docs/modules/graph.md#affects). Same rationale as
`tests/unit/test_app_runners_batch6.py`'s `TestGraphRunner`: call `run(cfg)`
directly against a hand-built `AppConfig` rather than spawning a subprocess.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.app.config import AppConfig
from frob.app.graph_runner import run as graph_run


def _make_contract_project(tmp_path: Path) -> Path:
    """A tiny two-file Python project where `mod.py::root` has a real
    doc/test edge and `dep.py::dependent` declares `frob:uses-contract
    mod.py::root`, so `affects()` returns a non-empty closure."""
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text("")
    (tmp_path / "pkg" / "mod.py").write_text(
        "# frob:doc docs/x.md#root\n"
        "def root():\n"
        "    '''Root contract.'''\n"
        "    return 1\n"
    )
    (tmp_path / "pkg" / "dep.py").write_text(
        "# frob:uses-contract pkg/mod.py::root\n"
        "def dependent():\n"
        "    '''Depends on root's contract.'''\n"
        "    return 2\n"
    )
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "x.md").write_text("# X\n\n## root\n\ntext\n")
    return tmp_path


class TestGraphAffectsRunner:
    """`frob graph affects <ref>` -- human and `--json` modes, truncation."""

    def test_affects_requires_ref(self, tmp_path: Path) -> None:
        # frob:tests src/frob/app/graph_runner.py::_run_affects
        cfg = AppConfig(graph_command="affects", graph_path=tmp_path)
        with pytest.raises(SystemExit) as exc:
            graph_run(cfg)
        assert exc.value.code == 1

    def test_affects_unresolvable_ref_exits_1(self, tmp_path: Path) -> None:
        # frob:tests src/frob/app/graph_runner.py::_run_affects
        _make_contract_project(tmp_path)
        cfg = AppConfig(
            graph_command="affects", graph_path=tmp_path, graph_ref="pkg/mod.py::ghost"
        )
        with pytest.raises(SystemExit) as exc:
            graph_run(cfg)
        assert exc.value.code == 1

    def test_human_mode_reports_dependents_docs_tests(
        self, tmp_path: Path, caplog
    ) -> None:
        # frob:tests src/frob/app/graph_runner.py::_run_affects
        _make_contract_project(tmp_path)
        cfg = AppConfig(
            graph_command="affects", graph_path=tmp_path, graph_ref="pkg/mod.py::root"
        )
        with caplog.at_level("INFO"):
            graph_run(cfg)
        assert "affects: pkg/mod.py::root" in caplog.text
        assert "pkg/dep.py::dependent" in caplog.text
        assert "docs/x.md#root" in caplog.text

    def test_json_mode_payload(self, tmp_path: Path, caplog) -> None:
        # frob:tests src/frob/app/graph_runner.py::_run_affects
        _make_contract_project(tmp_path)
        cfg = AppConfig(
            graph_command="affects",
            graph_path=tmp_path,
            graph_ref="pkg/mod.py::root",
            graph_json=True,
        )
        with caplog.at_level("INFO"):
            graph_run(cfg)
        assert '"root": "pkg/mod.py::root"' in caplog.text
        assert '"pkg/dep.py::dependent"' in caplog.text

    def test_truncated_closure_flagged(self, tmp_path: Path, caplog) -> None:
        # frob:tests src/frob/app/graph_runner.py::_run_affects
        _make_contract_project(tmp_path)
        cfg = AppConfig(
            graph_command="affects",
            graph_path=tmp_path,
            graph_ref="pkg/mod.py::root",
            graph_max_depth=0,
        )
        with caplog.at_level("INFO"):
            graph_run(cfg)
        assert "[TRUNCATED]" in caplog.text
