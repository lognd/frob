"""T-5137: automatic per-ticket agent token accounting mined from harness
transcript JSONL -- `frob.tickets._token_usage`'s adapter, collector, and
writer, plus `release_lease`'s best-effort call to both.
"""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from frob.tickets._leases import record_lease, release_lease
from frob.tickets._models import Origin, Ticket, TicketKind, TicketState
from frob.tickets._store import atomic_write, ledger_path, write_ticket
from frob.tickets._token_usage import (
    ClaudeCodeAdapter,
    UsageError,
    _SessionRecord,
    collect_ticket_usage,
    record_ticket_usage,
)


def _ticket(ticket_id: str = "T-0001") -> Ticket:
    return Ticket(
        id=ticket_id,
        title="sample",
        state=TicketState.IN_PROGRESS,
        kind=TicketKind.FEATURE,
        origin=Origin.HUMAN,
        created=datetime(2026, 1, 1).date(),
    )


def _write_transcript(path: Path, entries: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for entry in entries:
            fh.write(json.dumps(entry))
            fh.write("\n")


def _assistant_entry(input_tokens: int, output_tokens: int) -> dict:
    return {
        "type": "assistant",
        "message": {
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cache_creation_input_tokens": 1,
                "cache_read_input_tokens": 2,
            }
        },
    }


class TestClaudeCodeAdapterDiscoverSessions:
    # frob:tests src/frob/tickets/_token_usage.py::ClaudeCodeAdapter
    def test_filters_by_worktree_and_window(self, tmp_path: Path) -> None:
        # frob:tests \
        # src/frob/tickets/_token_usage.py::ClaudeCodeAdapter.discover_sessions
        telemetry = tmp_path / ".frob" / "telemetry.jsonl"
        telemetry.parent.mkdir(parents=True)
        in_window = "2026-01-02T00:00:00.000Z"
        out_of_window = "2026-01-10T00:00:00.000Z"
        lines = [
            {
                "kind": "dispatch",
                "event": "start",
                "dispatch_id": "sess-1",
                "worktree": str(tmp_path),
                "iso_ts": in_window,
                "transcript_path": "/tmp/sess-1.jsonl",
            },
            {
                "kind": "dispatch",
                "event": "start",
                "dispatch_id": "sess-2",
                "worktree": str(tmp_path),
                "iso_ts": out_of_window,
                "transcript_path": "/tmp/sess-2.jsonl",
            },
            {
                "kind": "dispatch",
                "event": "start",
                "dispatch_id": "sess-3",
                "worktree": "/somewhere/else",
                "iso_ts": in_window,
                "transcript_path": "/tmp/sess-3.jsonl",
            },
            {
                "kind": "dispatch",
                "event": "end",
                "dispatch_id": "sess-1",
            },
        ]
        with telemetry.open("w", encoding="utf-8") as fh:
            for line in lines:
                fh.write(json.dumps(line))
                fh.write("\n")

        window_start = datetime(2026, 1, 1, tzinfo=UTC)
        window_end = datetime(2026, 1, 5, tzinfo=UTC)
        sessions = ClaudeCodeAdapter().discover_sessions(
            tmp_path, str(tmp_path), window_start, window_end
        )
        assert [s.session_id for s in sessions] == ["sess-1"]
        assert sessions[0].transcript_path == "/tmp/sess-1.jsonl"

    def test_missing_telemetry_file_is_empty(self, tmp_path: Path) -> None:
        sessions = ClaudeCodeAdapter().discover_sessions(
            tmp_path,
            str(tmp_path),
            datetime(2026, 1, 1, tzinfo=UTC),
            datetime(2026, 1, 2, tzinfo=UTC),
        )
        assert sessions == []


class TestClaudeCodeAdapterExtractUsage:
    # frob:tests src/frob/tickets/_token_usage.py::ClaudeCodeAdapter
    def test_sums_assistant_usage_fields(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_token_usage.py::ClaudeCodeAdapter.extract_usage
        transcript = tmp_path / "t.jsonl"
        _write_transcript(
            transcript,
            [
                _assistant_entry(10, 5),
                {"type": "user", "message": {}},
                _assistant_entry(20, 8),
            ],
        )
        totals, cursor, complete = ClaudeCodeAdapter().extract_usage(transcript, None)
        assert totals == {
            "input": 30,
            "output": 13,
            "cache_creation": 2,
            "cache_read": 4,
        }
        assert complete is True
        assert cursor is not None
        assert cursor["byte_offset"] == transcript.stat().st_size

    def test_incremental_cursor_only_reads_new_bytes(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_token_usage.py::ClaudeCodeAdapter.extract_usage
        transcript = tmp_path / "t.jsonl"
        _write_transcript(transcript, [_assistant_entry(10, 5)])
        adapter = ClaudeCodeAdapter()
        totals_1, cursor_1, complete_1 = adapter.extract_usage(transcript, None)
        assert totals_1["input"] == 10
        assert complete_1 is True
        assert cursor_1 is not None

        with transcript.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(_assistant_entry(1, 1)))
            fh.write("\n")

        totals_2, cursor_2, complete_2 = adapter.extract_usage(transcript, cursor_1)
        assert totals_2["input"] == 11
        assert totals_2["output"] == 6
        assert complete_2 is True
        assert cursor_2 is not None
        assert cursor_2["byte_offset"] > cursor_1["byte_offset"]

    def test_unreadable_transcript_is_incomplete_none_cursor(
        self, tmp_path: Path
    ) -> None:
        missing = tmp_path / "nope.jsonl"
        totals, cursor, complete = ClaudeCodeAdapter().extract_usage(missing, None)
        assert totals == {"input": 0, "output": 0, "cache_creation": 0, "cache_read": 0}
        assert cursor is None
        assert complete is False

    def test_budget_exceeded_stops_early_and_reports_incomplete(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/tickets/_token_usage.py::ClaudeCodeAdapter.extract_usage
        """T-5137 acceptance [4]'s wall-clock bound, exercised directly:
        with the budget forced to 0s, even one entry is past the deadline
        and the pass must stop and report `complete=False` rather than
        block a `close`/`land` on however large the transcript is."""
        transcript = tmp_path / "big.jsonl"
        _write_transcript(transcript, [_assistant_entry(1, 1) for _ in range(50)])
        with patch("frob.tickets._token_usage._COLLECTION_BUDGET_SECONDS", 0.0):
            totals, cursor, complete = ClaudeCodeAdapter().extract_usage(
                transcript, None
            )
        assert complete is False
        assert cursor is not None
        # Stopped before consuming the whole (small, but budget=0) file.
        assert cursor["byte_offset"] < transcript.stat().st_size


class _FakeLeaseRecord:
    """Minimal stand-in for `frob.tickets._leases._LeaseRecord` -- only the
    two fields `collect_ticket_usage` reads."""

    def __init__(self, worktree: str, recorded_at: str) -> None:
        self.worktree = worktree
        self.recorded_at = recorded_at


class _FakeAdapter:
    """A `HarnessAdapter` double returning fixed sessions/usage, so
    `collect_ticket_usage`'s own orchestration is tested independent of
    real telemetry/transcript files."""

    def __init__(self, sessions, usage_by_path) -> None:  # noqa: ANN001
        self._sessions = sessions
        self._usage_by_path = usage_by_path

    def discover_sessions(self, root, worktree, window_start, window_end):  # noqa: ANN001
        return self._sessions

    def extract_usage(self, transcript_path, cursor):  # noqa: ANN001
        return self._usage_by_path[str(transcript_path)]


class TestCollectTicketUsage:
    # frob:tests src/frob/tickets/_token_usage.py::collect_ticket_usage
    # frob:tests src/frob/tickets/_token_usage.py::_sum_sessions
    def test_no_lease_returns_none(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/unit/test_token_usage.py::TestCollectTicketUsage.test_no_lease_returns_none  # noqa: E501
        with patch("frob.tickets._leases.lease_record_for_ticket", return_value=None):
            result = collect_ticket_usage(tmp_path, "T-0001")
        assert result.is_ok
        assert result.danger_ok is None

    # frob:tests src/frob/tickets/_token_usage.py::collect_ticket_usage
    # frob:tests src/frob/tickets/_token_usage.py::_sum_sessions
    # frob:tests src/frob/tickets/_token_usage.py::HarnessAdapter
    def test_sums_assistant_usage_fields(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/unit/test_token_usage.py::TestCollectTicketUsage.test_sums_assistant_usage_fields  # noqa: E501
        lease = _FakeLeaseRecord(
            worktree=str(tmp_path), recorded_at="2026-01-01T00:00:00+00:00"
        )
        sessions = [
            _SessionRecord(
                session_id="sess-1",
                transcript_path="/tmp/a.jsonl",
                iso_ts="2026-01-02T00:00:00Z",
            )
        ]
        adapter = _FakeAdapter(
            sessions,
            {
                "/tmp/a.jsonl": (
                    {"input": 5, "output": 2, "cache_creation": 0, "cache_read": 0},
                    {"byte_offset": 100},
                    True,
                )
            },
        )
        with patch("frob.tickets._leases.lease_record_for_ticket", return_value=lease):
            result = collect_ticket_usage(tmp_path, "T-0001", adapter=adapter)
        assert result.is_ok
        usage = result.danger_ok
        assert usage is not None
        assert usage.input_tokens == 5
        assert usage.output_tokens == 2
        assert usage.sessions == ("sess-1",)
        assert usage.complete is True

    def test_session_without_transcript_path_marks_incomplete(
        self, tmp_path: Path
    ) -> None:
        lease = _FakeLeaseRecord(
            worktree=str(tmp_path), recorded_at="2026-01-01T00:00:00+00:00"
        )
        sessions = [
            _SessionRecord(
                session_id="sess-1", transcript_path=None, iso_ts="2026-01-02T00:00:00Z"
            )
        ]
        adapter = _FakeAdapter(sessions, {})
        with patch("frob.tickets._leases.lease_record_for_ticket", return_value=lease):
            result = collect_ticket_usage(tmp_path, "T-0001", adapter=adapter)
        assert result.is_ok
        usage = result.danger_ok
        assert usage is not None
        assert usage.complete is False
        assert usage.input_tokens == 0


class TestRecordTicketUsage:
    # frob:tests src/frob/tickets/_token_usage.py::record_ticket_usage
    # frob:tests src/frob/tickets/_models.py::TicketUsage
    def test_writes_usage_onto_ticket(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/unit/test_token_usage.py::TestRecordTicketUsage.test_writes_usage_onto_ticket  # noqa: E501
        (tmp_path / "tickets").mkdir()
        ticket = _ticket()
        write_ticket(tmp_path, ticket)

        from frob.tickets._models import TicketUsage

        usage = TicketUsage(
            input_tokens=1,
            output_tokens=2,
            cache_creation_tokens=0,
            cache_read_tokens=0,
            sessions=("sess-1",),
            transcripts_seen=("/tmp/a.jsonl",),
            window_start="2026-01-01T00:00:00+00:00",
            window_end="2026-01-02T00:00:00+00:00",
            collected_at="2026-01-02T00:00:00+00:00",
            complete=True,
        )
        result = record_ticket_usage(tmp_path, "T-0001", usage)
        assert result.is_ok
        assert result.danger_ok.usage == usage

    # frob:tests src/frob/tickets/_token_usage.py::UsageError
    def test_unknown_ticket_is_err(self, tmp_path: Path) -> None:
        (tmp_path / "tickets").mkdir()
        result = record_ticket_usage(tmp_path, "T-9999", None)
        assert result.is_err
        assert result.danger_err is UsageError.NoTicket


def _run(argv: list[str], cwd: Path) -> None:
    """Run a git plumbing command under `cwd`, failing loudly on error --
    mirrors `test_lease_lifecycle.py`'s own helper of the same name."""
    subprocess.run(argv, cwd=str(cwd), check=True, capture_output=True, text=True)


class TestReleaseLeaseCollectsUsage:
    """T-5137: `release_lease` fires `_collect_and_record_usage_best_effort`
    before it unlinks the lease file -- the real land/close chokepoint,
    exercised here directly (not through `transition`) since `transition`
    itself is out of this ticket's declared scope."""

    # frob:tests src/frob/tickets/_leases.py::lease_record_for_ticket
    # frob:tests src/frob/tickets/_leases.py::_collect_and_record_usage_best_effort
    def test_release_records_usage(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/unit/test_token_usage.py::TestReleaseLeaseCollectsUsage.test_release_records_usage  # noqa: E501
        root = tmp_path / "repo"
        root.mkdir()
        _run(["git", "init", "-q", "-b", "main"], root)
        _run(["git", "config", "user.email", "test@example.com"], root)
        _run(["git", "config", "user.name", "Test"], root)
        atomic_write(ledger_path(root), "# Tickets\n\n")
        (root / "tickets").mkdir()
        _run(["git", "add", "-A"], root)
        _run(["git", "commit", "-q", "-m", "init"], root)

        ticket = _ticket("T-0001")
        write_ticket(root, ticket)

        recorded = record_lease(root, "T-0001", ())
        assert recorded.is_ok

        # Seed a transcript + telemetry start record inside this lease's
        # window so `collect_ticket_usage` finds real usage to sum.
        transcript = root / "transcript.jsonl"
        _write_transcript(transcript, [_assistant_entry(7, 3)])
        telemetry = root / ".frob" / "telemetry.jsonl"
        telemetry.parent.mkdir(parents=True, exist_ok=True)
        with telemetry.open("w", encoding="utf-8") as fh:
            fh.write(
                json.dumps(
                    {
                        "kind": "dispatch",
                        "event": "start",
                        "dispatch_id": "sess-1",
                        "worktree": str(root),
                        "iso_ts": datetime.now(UTC)
                        .isoformat(timespec="milliseconds")
                        .replace("+00:00", "Z"),
                        "transcript_path": str(transcript),
                    }
                )
            )
            fh.write("\n")

        result = release_lease(root, "T-0001")
        assert result.is_ok

        from frob.tickets import _load_one

        reloaded = _load_one(root, "T-0001").danger_ok
        assert reloaded.usage is not None
        assert reloaded.usage.input_tokens == 7
        assert reloaded.usage.output_tokens == 3
