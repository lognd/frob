"""T-0412: `frob debt` CLI wiring (`frob.app.debt_runner`) -- lists
outstanding `frob:debt` entries via `frob.gates.list_debt`, JSON and
human-readable modes, no mutation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from frob.app.config import AppConfig
from frob.app.debt_runner import run


def _write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


class TestDebtRunner:
    def test_json_mode_lists_debt_entries(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        # frob:tests tests/test_debt_runner.py::TestDebtRunner.test_json_mode_lists_debt_entries
        _write(
            tmp_path,
            "src/a.py",
            "def helper(x):\n"
            '    # frob:debt TEST005 reason="coverage gap" ticket="T-0001" '
            'until="2099-01-01"\n'
            "    return x\n",
        )
        cfg = AppConfig(debt_path=tmp_path, debt_json=True)
        run(cfg)
        out = json.loads(capsys.readouterr().out)
        assert len(out) == 1
        assert out[0]["rule"] == "TEST005"
        assert out[0]["ticket"] == "T-0001"
        assert out[0]["expired"] is False

    def test_no_debt_logs_clean_message(self, tmp_path: Path, caplog) -> None:
        # frob:tests tests/test_debt_runner.py::TestDebtRunner.test_no_debt_logs_clean_message
        _write(tmp_path, "src/a.py", "def helper(x):\n    return x\n")
        cfg = AppConfig(debt_path=tmp_path, debt_json=False)
        run(cfg)
        assert "no outstanding frob:debt entries" in caplog.text

    def test_human_mode_reports_expired_flag(self, tmp_path: Path, caplog) -> None:
        # frob:tests tests/test_debt_runner.py::TestDebtRunner.test_human_mode_reports_expired_flag
        _write(
            tmp_path,
            "src/a.py",
            "def helper(x):\n"
            '    # frob:debt TEST005 reason="coverage gap" ticket="T-0001" '
            'until="2000-01-01"\n'
            "    return x\n",
        )
        cfg = AppConfig(debt_path=tmp_path, debt_json=False)
        run(cfg)
        assert "EXPIRED" in caplog.text
        assert "TEST005" in caplog.text
