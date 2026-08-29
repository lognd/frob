"""Test for `scripts/measure_evidence_reach.py` (T-3046)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest


def _load_measure_evidence_reach() -> ModuleType:
    """Load `scripts/measure_evidence_reach.py` by file path (it is a
    standalone script, not an importable package member) -- avoids a
    `sys.path` mutation entirely, so no E402/unresolved-import suppression
    pairing is needed at the call site."""
    path = Path(__file__).resolve().parents[1] / "scripts" / "measure_evidence_reach.py"
    spec = importlib.util.spec_from_file_location("measure_evidence_reach", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


measure_evidence_reach_main = _load_measure_evidence_reach().measure_evidence_reach_main


class TestMeasureEvidenceReachMain:
    """`scripts.measure_evidence_reach.measure_evidence_reach_main`."""

    def test_runs_clean_over_a_minimal_ticket_ledger(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        # frob:tests scripts/measure_evidence_reach.py::measure_evidence_reach_main
        (tmp_path / "pkg").mkdir()
        (tmp_path / "pkg" / "impl.py").write_text("def _target():\n    return 1\n")
        (tmp_path / "pkg" / "test_impl.py").write_text(
            "from pkg.impl import _target\n\n\ndef test_x():\n    _target()\n"
        )
        (tmp_path / "tickets" / "T-0001").mkdir(parents=True)
        (tmp_path / "tickets" / "T-0001" / "ticket.md").write_text(
            "---\n"
            "id: T-0001\n"
            "title: minimal fixture ticket\n"
            "state: done\n"
            "kind: feature\n"
            "origin: human\n"
            'created: "2026-01-01"\n'
            "scope:\n"
            "- pkg/impl.py\n"
            "evidence:\n"
            "- pkg/test_impl.py::test_x\n"
            "---\n"
        )
        monkeypatch.setattr(
            sys, "argv", ["measure_evidence_reach.py", "--root", str(tmp_path)]
        )
        exit_code = measure_evidence_reach_main()
        assert exit_code == 0
        out = capsys.readouterr().out
        assert "total classified: 1" in out
        assert "reaches: 1" in out
