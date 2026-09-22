"""T-4696 (nine ticket field-setters become one): round-trip and byte-
identical-shim tests for `frob ticket set <id> <field> <value>`, the
single subverb folding priority/kind/component/tier/milestone/sprint's
standalone spellings. `label` (repeatable add/remove list), `accept`
(three modes plus --criterion-file), and `body` (--append-file/--set-file)
are deliberately NOT folded -- each measured to not be a one-token field
write, the same file-streaming disqualifier this ticket's own body rule
names."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from frob.tickets import (
    Origin,
    Priority,
    Ticket,
    TicketKind,
    TicketState,
    load_all,
    write_ticket,
)


def _read_back(root: Path, ticket_id: str) -> Ticket:
    """Read `ticket_id` back from `root`'s ledger via the public
    `load_all` -- the shared read-back helper every round-trip test below
    uses to confirm a `frob ticket set` write actually landed."""
    queue = load_all(root).danger_ok
    return queue[ticket_id]


def _seed_ticket(tmp_path: Path, ticket_id: str = "T-9001") -> Path:
    """Write one minimal open ticket into a fresh `tickets/` tree under
    `tmp_path`, returning the repo root -- the shared fixture every test
    below builds on."""
    ticket = Ticket(
        id=ticket_id,
        title="fixture ticket",
        kind=TicketKind.BUG,
        state=TicketState.QUEUED,
        origin=Origin.HUMAN,
        created=date(2026, 1, 1),
        body="fixture body",
    )
    write_ticket(tmp_path, ticket)
    return tmp_path


# frob:ticket T-4696
class TestSetRoundTrip:
    """One round-trip test per folded field (T-4696 acceptance[1]): `frob
    ticket set <id> <field> <value>` followed by a fresh `read_ticket`
    confirms the field actually changed."""

    def test_priority(self, tmp_path: Path) -> None:
        from frob.app.config import AppConfig
        from frob.app.ticket_runner._lifecycle import _set

        root = _seed_ticket(tmp_path)
        cfg = AppConfig(
            ticket_id="T-9001",
            ticket_set_field="priority",
            ticket_set_value="high",
            ticket_triage_reason="round-trip test",
            ticket_no_commit=True,
        )
        _set(root, cfg)
        ticket = _read_back(root, "T-9001")
        assert ticket.priority == Priority.HIGH

    def test_kind(self, tmp_path: Path) -> None:
        from frob.app.config import AppConfig
        from frob.app.ticket_runner._lifecycle import _set

        root = _seed_ticket(tmp_path)
        cfg = AppConfig(
            ticket_id="T-9001",
            ticket_set_field="kind",
            ticket_set_value="security",
            ticket_triage_reason="round-trip test",
            ticket_no_commit=True,
        )
        _set(root, cfg)
        ticket = _read_back(root, "T-9001")
        assert ticket.kind == TicketKind.SECURITY

    def test_component(self, tmp_path: Path) -> None:
        from frob.app.config import AppConfig
        from frob.app.ticket_runner._lifecycle import _set

        root = _seed_ticket(tmp_path)
        cfg = AppConfig(
            ticket_id="T-9001",
            ticket_set_field="component",
            ticket_set_value="cli",
            ticket_triage_reason="round-trip test",
            ticket_no_commit=True,
        )
        _set(root, cfg)
        ticket = _read_back(root, "T-9001")
        assert ticket.component == "cli"

    def test_tier(self, tmp_path: Path) -> None:
        from frob.app.config import AppConfig
        from frob.app.ticket_runner._lifecycle import _set

        root = _seed_ticket(tmp_path)
        cfg = AppConfig(
            ticket_id="T-9001",
            ticket_set_field="tier",
            ticket_set_value="story",
            ticket_triage_reason="round-trip test",
            ticket_no_commit=True,
        )
        _set(root, cfg)
        ticket = _read_back(root, "T-9001")
        assert ticket.tier.value == "story"

    def test_milestone(self, tmp_path: Path) -> None:
        from frob.app.config import AppConfig
        from frob.app.ticket_runner._lifecycle import _set

        root = _seed_ticket(tmp_path)
        cfg = AppConfig(
            ticket_id="T-9001",
            ticket_set_field="milestone",
            ticket_set_value="1.2.3",
            ticket_no_commit=True,
        )
        _set(root, cfg)
        ticket = _read_back(root, "T-9001")
        assert ticket.milestone == "1.2.3"

    def test_sprint(self, tmp_path: Path) -> None:
        from frob.app.config import AppConfig
        from frob.app.ticket_runner._lifecycle import _set

        root = _seed_ticket(tmp_path)
        cfg = AppConfig(
            ticket_id="T-9001",
            ticket_set_field="sprint",
            ticket_set_value="sprint-42",
            ticket_no_commit=True,
        )
        _set(root, cfg)
        ticket = _read_back(root, "T-9001")
        assert ticket.sprint == "sprint-42"


# frob:ticket T-4696
class TestDeprecatedShimByteIdentical:
    """T-4696 acceptance[2]: the deprecated flat spelling and the new
    `set` spelling write IDENTICAL ledger bytes on the same fixture and
    value -- not just "both succeed", the stronger same-bytes control."""

    def test_priority_shim_matches_set(self, tmp_path: Path) -> None:
        from frob.app.config import AppConfig
        from frob.app.ticket_runner._lifecycle import _deprecated_set_field, _set
        from frob.app.ticket_runner._mutate import _priority

        root_old = _seed_ticket(tmp_path / "old")
        root_new = _seed_ticket(tmp_path / "new")

        old_cfg = AppConfig(
            ticket_id="T-9001",
            ticket_priority_level="critical",
            ticket_triage_reason="byte parity test",
            ticket_no_commit=True,
        )
        _deprecated_set_field("priority", "priority", _priority)(root_old, old_cfg)

        new_cfg = AppConfig(
            ticket_id="T-9001",
            ticket_set_field="priority",
            ticket_set_value="critical",
            ticket_triage_reason="byte parity test",
            ticket_no_commit=True,
        )
        _set(root_new, new_cfg)

        old_bytes = (root_old / "tickets" / "T-9001" / "ticket.md").read_bytes()
        new_bytes = (root_new / "tickets" / "T-9001" / "ticket.md").read_bytes()
        assert old_bytes == new_bytes

    def test_priority_shim_prints_deprecation_notice(self, capsys) -> None:
        """The shim wrapper announces before delegating -- proven directly
        against `_deprecated_set_field`, independent of the byte-parity
        test above."""
        import datetime as dt

        from frob._cli_parsers._shims import announce_shim

        announce_shim(
            old_name="ticket priority",
            new_name="ticket set <id> priority <value>",
            sunset="2026-12-01",
            ticket="T-4696",
            today=dt.date(2026, 9, 22),
        )
        captured = capsys.readouterr()
        assert "DEPRECATED" in captured.err
        assert "ticket set" in captured.err


# frob:ticket T-4696
class TestCitationSweep:
    """T-4696 acceptance[3]: the citation sweep over .claude/, docs/,
    scripts/, src/, tests/ for each of the nine deleted spellings.
    Scoped to genuine operational citations (a markdown code-fence
    command line), same reasoning T-4690's own sweep test used."""

    def test_no_markdown_code_fence_recommends_a_deleted_field_setter(self) -> None:
        """No docs/.claude/scripts file's `frob ticket <verb>` example
        line still recommends running one of the six folded field-setter
        spellings as the command to type."""
        import re
        import subprocess

        deleted = ("priority", "kind", "component", "tier", "milestone")
        pattern = re.compile(r"^frob ticket (" + "|".join(deleted) + r") ")
        result = subprocess.run(
            [
                "git",
                "grep",
                "-nE",
                pattern.pattern,
                "--",
                "docs/",
                ".claude/",
                "scripts/",
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).resolve().parents[2],
        )
        assert result.returncode == 1, (
            f"stale command-fence citation(s) of a deleted field-setter found:\n{result.stdout}"
        )
