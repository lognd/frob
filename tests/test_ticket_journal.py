"""T-0456: the intent-journal side-channel (`frob.tickets._journal`) that
lets `frob ticket land` mark a multi-step operation in flight, and lets
`frob ticket reconcile` detect one that never reached its own cleanup
(crash/interrupt mid-land)."""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.tickets._journal import (
    _clear_intent,
    _journal_dir,
    _JournalError,
    _LandIntent,
    _read_all_intents,
    _write_intent,
)


class TestWriteIntent:
    def test_write_then_read_round_trips(self, tmp_path: Path) -> None:
        # frob:tests tests/test_ticket_journal.py::TestWriteIntent.test_write_then_read_round_trips  # noqa: E501
        result = _write_intent(tmp_path, "T-0001", tmp_path / "worktree")
        assert result.is_ok
        records = _read_all_intents(tmp_path)
        assert len(records) == 1
        assert records[0].ticket_id == "T-0001"
        assert records[0].worktree == str((tmp_path / "worktree").resolve())

    def test_write_failure_returns_err(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_ticket_journal.py::TestWriteIntent.test_write_failure_returns_err  # noqa: E501
        import frob.tickets._journal as journal_mod
        from frob.tickets._models import TicketError

        def _boom(path, content):  # noqa: ANN001, ANN202
            from typani.result import Err

            return Err(TicketError.WriteFailed)

        monkeypatch.setattr(journal_mod, "atomic_write", _boom)
        result = _write_intent(tmp_path, "T-0002", tmp_path)
        assert result.is_err
        assert result.danger_err == _JournalError.WriteFailed


class TestClearIntent:
    def test_clear_removes_the_file(self, tmp_path: Path) -> None:
        # frob:tests tests/test_ticket_journal.py::TestClearIntent.test_clear_removes_the_file  # noqa: E501
        _write_intent(tmp_path, "T-0003", tmp_path)
        assert len(_read_all_intents(tmp_path)) == 1
        _clear_intent(tmp_path, "T-0003")
        assert _read_all_intents(tmp_path) == ()

    def test_clear_missing_file_is_a_no_op(self, tmp_path: Path) -> None:
        # frob:tests tests/test_ticket_journal.py::TestClearIntent.test_clear_missing_file_is_a_no_op  # noqa: E501
        _clear_intent(tmp_path, "T-does-not-exist")  # must not raise


class TestReadAllIntents:
    def test_reads_every_recorded_intent(self, tmp_path: Path) -> None:
        # frob:tests tests/test_ticket_journal.py::TestReadAllIntents.test_reads_every_recorded_intent  # noqa: E501
        _write_intent(tmp_path, "T-0010", tmp_path)
        _write_intent(tmp_path, "T-0011", tmp_path)
        records = _read_all_intents(tmp_path)
        assert sorted(r.ticket_id for r in records) == ["T-0010", "T-0011"]

    def test_no_journal_dir_returns_empty(self, tmp_path: Path) -> None:
        # frob:tests tests/test_ticket_journal.py::TestReadAllIntents.test_no_journal_dir_returns_empty  # noqa: E501
        assert _read_all_intents(tmp_path) == ()

    def test_malformed_record_is_skipped_not_fatal(self, tmp_path: Path) -> None:
        # frob:tests tests/test_ticket_journal.py::TestReadAllIntents.test_malformed_record_is_skipped_not_fatal  # noqa: E501
        directory = _journal_dir(tmp_path)
        directory.mkdir(parents=True)
        (directory / "T-bad.json").write_text("not json", encoding="utf-8")
        _write_intent(tmp_path, "T-0020", tmp_path)
        records = _read_all_intents(tmp_path)
        assert [r.ticket_id for r in records] == ["T-0020"]


class TestLandIntent:
    def test_model_round_trips_via_json(self) -> None:
        # frob:tests tests/test_ticket_journal.py::TestLandIntent.test_model_round_trips_via_json  # noqa: E501
        intent = _LandIntent(
            ticket_id="T-0001",
            worktree="/tmp/x",
            started_at="2026-07-21T00:00:00+00:00",
        )
        assert _LandIntent.model_validate_json(intent.model_dump_json()) == intent
