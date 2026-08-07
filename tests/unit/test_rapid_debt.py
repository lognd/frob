# frob:ticket T-1684
"""Unit tests for `frob.tickets._evidence.record_rapid_debt` (T-1681):
the machine-readable record of every check the `rapid` profile skipped."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from frob.tickets._evidence import record_rapid_debt


class TestRecordRapidDebt:
    """One self-contained JSON line per skipped check, TRACKED (not under
    `.frob/`), and never able to fail its caller."""

    def test_appends_one_json_line_per_call(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_debt.py::TestRecordRapidDebt.test_appends_one_json_line_per_call  # noqa: E501
        record_rapid_debt(tmp_path, "T-0001", "test016")
        record_rapid_debt(tmp_path, "T-0002", "rel001")
        lines = (tmp_path / "rapid-debt.jsonl").read_text(encoding="utf-8").splitlines()
        assert len(lines) == 2
        entries = [json.loads(line) for line in lines]
        assert [entry["ticket"] for entry in entries] == ["T-0001", "T-0002"]
        assert [entry["skipped"] for entry in entries] == ["test016", "rel001"]

    def test_records_a_commit_field_even_outside_a_git_repo(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/test_rapid_debt.py::TestRecordRapidDebt.test_records_a_commit_field_even_outside_a_git_repo  # noqa: E501
        # tmp_path is not a repo: rev-parse fails, and the entry must
        # still be written (with an explicit "unknown"), never dropped --
        # an unrecorded relaxation is the one unrecoverable outcome.
        record_rapid_debt(tmp_path, "T-0003", "sweep")
        entry = json.loads(
            (tmp_path / "rapid-debt.jsonl").read_text(encoding="utf-8").strip()
        )
        assert entry["commit"] == "unknown"

    def test_is_tracked_not_under_dot_frob(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_debt.py::TestRecordRapidDebt.test_is_tracked_not_under_dot_frob  # noqa: E501
        record_rapid_debt(tmp_path, "T-0004", "sweep")
        assert (tmp_path / "rapid-debt.jsonl").exists()
        assert not (tmp_path / ".frob" / "rapid-debt.jsonl").exists()

    def test_an_unwritable_path_never_raises(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_debt.py::TestRecordRapidDebt.test_an_unwritable_path_never_raises  # noqa: E501
        # A directory where the file should be makes open() raise; the
        # recorder is best-effort and must not fail its caller's close.
        (tmp_path / "rapid-debt.jsonl").mkdir()
        record_rapid_debt(tmp_path, "T-0005", "sweep")
