"""Tests for `frob ticket brief` (T-0568): playbook-heading parsing,
inferred verify commands, gate-baseline summary, and the full briefing
composition + CLI wiring (docs/modules/tickets.md#frob-ticket-brief)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from frob.app.config import AppConfig
from frob.app.ticket_runner import _brief
from frob.tickets import (
    Origin,
    Ticket,
    TicketError,
    TicketKind,
    TicketState,
    brief_ticket,
)
from frob.tickets._brief import (
    current_version,
    gate_baseline_summary,
    infer_verify_commands,
    load_playbook_sections,
    parse_playbook_sections,
)
from frob.tickets._store import _serialize_ticket

# frob:ticket T-0568
_PLAYBOOK_SAMPLE = """# Agent playbook

Intro prose, not a section.

## 1. Worktree warm-up (do this FIRST, every time)

Step one. Step two.

## 1b. NEVER `git stash` in a worktree

Do not stash.

## See also

- some link
"""


# frob:ticket T-0568
def _ticket(
    *,
    ticket_id: str = "T-0001",
    scope: tuple[str, ...] = (),
    acceptance: tuple[str, ...] = (),
    state: TicketState = TicketState.QUEUED,
    body: str = "## Description\nsomething\n",
) -> Ticket:
    return Ticket(
        id=ticket_id,
        title="Sample ticket",
        state=state,
        kind=TicketKind.FEATURE,
        origin=Origin.HUMAN,
        created=date(2026, 1, 1),
        blocked_by=(),
        parent=None,
        scope=scope,
        evidence=(),
        attachments=(),
        # Plain-string acceptance items (this helper's pre-T-0572 shape,
        # kept for its callers' brevity) -- Ticket's own `_coerce_acceptance`
        # validator wraps each at runtime; see frob.tickets._models.
        acceptance=acceptance,  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]
        body=body,
    )


# frob:ticket T-0568
def _write(root: Path, ticket: Ticket, slug: str = "sample-ticket") -> Path:
    tickets_dir = root / "tickets"
    tickets_dir.mkdir(parents=True, exist_ok=True)
    path = tickets_dir / f"{ticket.id}-{slug}.md"
    path.write_text(_serialize_ticket(ticket), encoding="utf-8")
    return path


# frob:ticket T-0568
class TestParsePlaybookSections:
    # frob:ticket T-0568
    def test_parses_numbered_headings_only(self) -> None:
        # frob:tests tests/test_tickets_brief.py::TestParsePlaybookSections.test_parses_numbered_headings_only  # noqa: E501
        sections = parse_playbook_sections(_PLAYBOOK_SAMPLE)
        assert [s.number for s in sections] == ["1", "1b"]
        assert sections[0].title == "Worktree warm-up (do this FIRST, every time)"
        assert "Step one" in sections[0].body

    # frob:ticket T-0568
    def test_body_stops_at_next_heading_numbered_or_not(self) -> None:
        sections = parse_playbook_sections(_PLAYBOOK_SAMPLE)
        assert "some link" not in sections[1].body

    # frob:ticket T-0568
    def test_empty_text_yields_no_sections(self) -> None:
        assert parse_playbook_sections("") == ()


# frob:ticket T-0568
class TestLoadPlaybookSections:
    # frob:ticket T-0568
    def test_missing_file_returns_empty(self, tmp_path: Path) -> None:
        assert load_playbook_sections(tmp_path) == ()

    # frob:ticket T-0568
    def test_reads_real_file(self, tmp_path: Path) -> None:
        playbook = tmp_path / "docs" / "guides"
        playbook.mkdir(parents=True)
        (playbook / "agent-playbook.md").write_text(_PLAYBOOK_SAMPLE, encoding="utf-8")
        sections = load_playbook_sections(tmp_path)
        assert [s.number for s in sections] == ["1", "1b"]


# frob:ticket T-0568
class TestInferVerifyCommands:
    # frob:ticket T-0568
    def test_scope_naming_tests_dir_is_used_directly(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_brief.py::TestInferVerifyCommands.test_scope_naming_tests_dir_is_used_directly  # noqa: E501
        ticket = _ticket(scope=("tests/test_foo.py",))
        commands = infer_verify_commands(tmp_path, ticket)
        assert any("uv run frob check --ticket" in c for c in commands)
        assert any("pytest tests/test_foo.py" in c for c in commands)

    # frob:ticket T-0568
    def test_matches_test_file_by_stem(self, tmp_path: Path) -> None:
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_widget.py").write_text("", encoding="utf-8")
        ticket = _ticket(scope=("src/frob/widget.py",))
        commands = infer_verify_commands(tmp_path, ticket)
        assert any("tests/test_widget.py" in c for c in commands)

    # frob:ticket T-0568
    def test_no_scope_yields_only_check_command(self, tmp_path: Path) -> None:
        ticket = _ticket(scope=())
        commands = infer_verify_commands(tmp_path, ticket)
        assert len(commands) == 1
        assert "frob check --ticket" in commands[0]


# frob:ticket T-0568
class TestGateBaselineSummary:
    # frob:ticket T-0568
    def test_missing_baseline(self, tmp_path: Path) -> None:
        assert "no baseline stamped" in gate_baseline_summary(tmp_path)

    # frob:ticket T-0568
    def test_present_baseline(self, tmp_path: Path) -> None:
        frob_dir = tmp_path / ".frob"
        frob_dir.mkdir()
        (frob_dir / "baseline").write_text("{}", encoding="utf-8")
        assert "--delta" in gate_baseline_summary(tmp_path)


# frob:ticket T-0568
class TestCurrentVersion:
    # frob:ticket T-0568
    def test_missing_pyproject_is_none(self, tmp_path: Path) -> None:
        assert current_version(tmp_path) is None

    # frob:ticket T-0568
    def test_reads_project_version(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "x"\nversion = "1.2.3"\n', encoding="utf-8"
        )
        assert current_version(tmp_path) == "1.2.3"


# frob:ticket T-0568
class TestBriefTicket:
    # frob:ticket T-0568
    def test_composes_full_briefing(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_brief.py::TestBriefTicket.test_composes_full_briefing  # noqa: E501
        _write(
            tmp_path,
            _ticket(
                scope=("tests/test_foo.py",),
                acceptance=("does the thing",),
                body="## Description\ndo the thing\n",
            ),
        )
        result = brief_ticket(tmp_path, "T-0001")
        assert result.is_ok, result.err
        text = result.danger_ok
        assert "T-0001" in text
        assert "do the thing" in text
        assert "does the thing" in text
        assert "tests/test_foo.py" in text
        assert "frob check --ticket T-0001" in text
        assert "no baseline stamped" in text

    # frob:ticket T-0568
    def test_unknown_ticket_not_found(self, tmp_path: Path) -> None:
        (tmp_path / "tickets").mkdir()
        result = brief_ticket(tmp_path, "T-9999")
        assert result.is_err
        assert result.danger_err is TicketError.NotFound


# frob:ticket T-0568
class TestBriefCli:
    # frob:ticket T-0568
    def test_cli_prints_briefing(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests tests/test_tickets_brief.py::TestBriefCli.test_cli_prints_briefing
        _write(tmp_path, _ticket())
        cfg = AppConfig(
            ticket_command="brief", ticket_id="T-0001", ticket_path=tmp_path
        )
        with caplog.at_level("INFO"):
            _brief(tmp_path, cfg)
        assert any("Mission briefing" in rec.message for rec in caplog.records)

    # frob:ticket T-0568
    def test_cli_requires_id(self, tmp_path: Path) -> None:
        cfg = AppConfig(ticket_command="brief", ticket_path=tmp_path)
        with pytest.raises(SystemExit) as exc_info:
            _brief(tmp_path, cfg)
        assert exc_info.value.code == 1
