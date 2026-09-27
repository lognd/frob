"""Tests for `frob agent brief <ticket>` (T-draft-df99eb2d): the
`frob.agent._brief.render_agent_brief` composer plus its CLI wiring
(`frob.app.agent_runner`). Ticket fixtures follow `tests/test_tickets_
brief.py`'s own pattern (`Ticket` + `_serialize_ticket`, no git/frob.toml
needed for `load_queue` against a bare `tickets/` dir)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

# frob:waive SYS003 reason="a testsuite module exercising frob.agent, an intra-cli \
# helper package the same way frob.app.agent_runner itself is -- every other test \
# module exercising a cli-owned helper carries the identical testsuite->cli edge; \
# src/frob/agent/** belongs on the cli node's code= glob list (T-draft-6d585d1b tracks \
# adding it), a bookkeeping gap, not a real architectural boundary crossing"
from frob.agent._brief import _family_wiring_convention, render_agent_brief
from frob.tickets import (
    Origin,
    Ticket,
    TicketError,
    TicketKind,
    TicketState,
    TicketTier,
)
from frob.tickets._store import _serialize_ticket

# frob:ticket T-draft-df99eb2d
_PLAYBOOK_SAMPLE = """# Agent playbook

Intro prose.

## 0. Standard dispatch contract (the whole ritual, in order)

1. Do the ritual.

## 0a. Dispatch contract addenda (moved from the coordinator scratchpad)

1. One background command at a time.

## 1. Worktree warm-up (do this FIRST, every time)

Not part of the contract.
"""


# frob:ticket T-draft-df99eb2d
def _ticket(
    *,
    ticket_id: str = "T-0001",
    scope: tuple[str, ...] = (),
    blocked_by: tuple[str, ...] = (),
    body: str = "## Description\nsomething\n",
    points: int | None = None,
    parent: str | None = None,
    milestone: str | None = None,
    sprint: str | None = None,
) -> Ticket:
    """Minimal `Ticket` fixture, mirroring `tests/test_tickets_brief.py::
    _ticket`'s own shape (that module's private helper is not imported
    directly to avoid a cross-file private-symbol dependency)."""
    return Ticket(
        id=ticket_id,
        title=f"title for {ticket_id}",
        state=TicketState.QUEUED,
        kind=TicketKind.FEATURE,
        origin=Origin.HUMAN,
        created=date(2026, 1, 1),
        blocked_by=blocked_by,
        parent=parent,
        tier=TicketTier.TICKET,
        scope=scope,
        evidence=(),
        attachments=(),
        acceptance=(),
        body=body,
        points=points,
        milestone=milestone,
        sprint=sprint,
    )


# frob:ticket T-draft-df99eb2d
def _write_ticket(root: Path, ticket: Ticket, slug: str = "sample") -> None:
    """Write `ticket` as a real `tickets/<id>-<slug>.md` ledger row
    (`_serialize_ticket`, the same real writer `frob ticket new` uses) so
    `frob.tickets.load_queue` reads it back exactly like production."""
    tickets_dir = root / "tickets"
    tickets_dir.mkdir(parents=True, exist_ok=True)
    (tickets_dir / f"{ticket.id}-{slug}.md").write_text(
        _serialize_ticket(ticket), encoding="utf-8"
    )


# frob:ticket T-draft-df99eb2d
def _write_playbook(root: Path, text: str = _PLAYBOOK_SAMPLE) -> None:
    """Write `docs/guides/agent-playbook.md` under `root` -- the doc
    `render_agent_brief` reads live, never an embedded copy."""
    guides = root / "docs" / "guides"
    guides.mkdir(parents=True, exist_ok=True)
    (guides / "agent-playbook.md").write_text(text, encoding="utf-8")


# frob:ticket T-draft-df99eb2d
class TestRenderAgentBrief:
    """`render_agent_brief`'s composition (T-draft-df99eb2d)."""

    # frob:tests \
    # tests/unit/agent/test_brief.py::TestRenderAgentBrief.test_renders_contract_section_from_playbook  # noqa: E501
    # frob:tests src/frob/agent/_brief.py::_dispatch_contract_text
    def test_renders_contract_section_from_playbook(self, tmp_path: Path) -> None:
        """Both "0" and "0a" playbook sections render verbatim; the
        unrelated "1" section (worktree warm-up) does not."""
        _write_playbook(tmp_path)
        _write_ticket(tmp_path, _ticket())
        result = render_agent_brief(tmp_path, "T-0001")
        assert result.is_ok, result.err
        text = result.danger_ok
        assert "Do the ritual." in text
        assert "One background command at a time." in text
        assert "Not part of the contract." not in text

    # frob:tests \
    # tests/unit/agent/test_brief.py::TestRenderAgentBrief.test_renders_scope_and_blocked_by_verbatim_and_excludes_other_tickets_scope  # noqa: E501
    # frob:tests src/frob/agent/_brief.py::render_agent_brief
    def test_renders_scope_and_blocked_by_verbatim_and_excludes_other_tickets_scope(
        self, tmp_path: Path
    ) -> None:
        """Positive control: a ticket with scope + blocked_by renders both
        verbatim in the brief, and never leaks a SIBLING ticket's own
        scope glob into it."""
        _write_playbook(tmp_path)
        _write_ticket(
            tmp_path,
            _ticket(
                ticket_id="T-0001",
                scope=("src/frob/widget.py", "tests/test_widget.py"),
                blocked_by=("T-0002",),
            ),
            slug="mine",
        )
        _write_ticket(
            tmp_path,
            _ticket(ticket_id="T-0002", scope=("src/frob/unrelated_other.py",)),
            slug="other",
        )
        result = render_agent_brief(tmp_path, "T-0001")
        assert result.is_ok, result.err
        text = result.danger_ok
        assert "src/frob/widget.py" in text
        assert "tests/test_widget.py" in text
        assert "blocked_by=['T-0002']" in text
        assert "src/frob/unrelated_other.py" not in text

    # frob:tests \
    # tests/unit/agent/test_brief.py::TestRenderAgentBrief.test_no_scope_ticket_prints_warning_not_blank_section  # noqa: E501
    # frob:tests src/frob/agent/_brief.py::_scope_section
    def test_no_scope_ticket_prints_warning_not_blank_section(
        self, tmp_path: Path
    ) -> None:
        """Must-stay-quiet control: a no-scope ticket prints the explicit
        no-scope warning line, never a blank "## Scope" section."""
        _write_playbook(tmp_path)
        _write_ticket(tmp_path, _ticket(scope=()))
        result = render_agent_brief(tmp_path, "T-0001")
        assert result.is_ok, result.err
        text = result.danger_ok
        assert "## Scope\nWARNING: no scope declared" in text

    # frob:tests \
    # tests/unit/agent/test_brief.py::TestRenderAgentBrief.test_renders_points_parent_milestone_sprint  # noqa: E501
    def test_renders_points_parent_milestone_sprint(self, tmp_path: Path) -> None:
        """Points/parent/milestone/sprint ledger fields all surface."""
        _write_playbook(tmp_path)
        _write_ticket(
            tmp_path,
            _ticket(
                points=5,
                parent="T-0000",
                milestone="v0.535.0",
                sprint="coord-surface",
            ),
        )
        result = render_agent_brief(tmp_path, "T-0001")
        assert result.is_ok, result.err
        text = result.danger_ok
        assert "points=5" in text
        assert "parent=T-0000" in text
        assert "milestone=v0.535.0" in text
        assert "sprint=coord-surface" in text

    # frob:tests \
    # tests/unit/agent/test_brief.py::TestRenderAgentBrief.test_family_wiring_convention_rendered_when_declared  # noqa: E501
    # frob:tests src/frob/agent/_brief.py::_family_wiring_convention
    def test_family_wiring_convention_rendered_when_declared(
        self, tmp_path: Path
    ) -> None:
        """A body `wiring:` line surfaces under its own section; a body
        with none omits the section entirely (never a blank one)."""
        _write_playbook(tmp_path)
        _write_ticket(
            tmp_path,
            _ticket(
                ticket_id="T-0001",
                body="## Description\nsomething\n\nwiring: self-contained run(argv)\n",
            ),
            slug="wired",
        )
        _write_ticket(
            tmp_path,
            _ticket(ticket_id="T-0002", body="## Description\nno convention here\n"),
            slug="unwired",
        )
        wired = render_agent_brief(tmp_path, "T-0001")
        unwired = render_agent_brief(tmp_path, "T-0002")
        assert wired.is_ok and unwired.is_ok
        assert "## Family wiring convention" in wired.danger_ok
        assert "self-contained run(argv)" in wired.danger_ok
        assert "## Family wiring convention" not in unwired.danger_ok

    # frob:tests \
    # tests/unit/agent/test_brief.py::TestRenderAgentBrief.test_unknown_ticket_not_found
    def test_unknown_ticket_not_found(self, tmp_path: Path) -> None:
        (tmp_path / "tickets").mkdir()
        result = render_agent_brief(tmp_path, "T-9999")
        assert result.is_err
        assert result.danger_err is TicketError.NotFound


# frob:ticket T-draft-df99eb2d
class TestFamilyWiringConvention:
    """`_family_wiring_convention` in isolation."""

    # frob:tests \
    # tests/unit/agent/test_brief.py::TestFamilyWiringConvention.test_none_when_absent
    def test_none_when_absent(self) -> None:
        ticket = _ticket(body="## Description\nno wiring line here\n")
        assert _family_wiring_convention(ticket) is None

    # frob:tests \
    # tests/unit/agent/test_brief.py::TestFamilyWiringConvention.test_extracts_the_line_case_insensitively  # noqa: E501
    def test_extracts_the_line_case_insensitively(self) -> None:
        ticket = _ticket(body="## Description\nsomething\n\nWiring: fooconvention\n")
        assert _family_wiring_convention(ticket) == "fooconvention"


# frob:ticket T-draft-df99eb2d
class TestCliParity:
    """`frob agent brief <ticket>` through the real argparse/dispatch
    entry (`frob.app.agent_runner`), not just the composer."""

    # frob:tests \
    # tests/unit/agent/test_brief.py::TestCliParity.test_normalize_agent_argv_never_implies_brief  # noqa: E501
    def test_normalize_agent_argv_never_implies_brief(self) -> None:
        """`brief` must always be named explicitly -- a bare `frob agent`
        keeps meaning `env` (T-4546), never `brief`."""
        from frob.app.agent_runner import _normalize_agent_argv

        assert _normalize_agent_argv(["brief", "T-0001"]) == ["brief", "T-0001"]
        assert _normalize_agent_argv(["/tmp/wt"]) == ["env", "/tmp/wt"]

    # frob:tests \
    # tests/unit/agent/test_brief.py::TestCliParity.test_parser_parses_ticket_and_path
    def test_parser_parses_ticket_and_path(self) -> None:
        from frob.app.agent_runner import _build_agent_parser, _normalize_agent_argv

        parser = _build_agent_parser()
        args = parser.parse_args(
            _normalize_agent_argv(["brief", "T-0001", "--path", "/tmp/repo"])
        )
        assert args.agent_command == "brief"
        assert args.ticket == "T-0001"
        assert args.path == "/tmp/repo"

    # frob:tests \
    # tests/unit/agent/test_brief.py::TestCliParity.test_run_brief_prints_render_agent_brief_result  # noqa: E501
    # frob:tests src/frob/app/agent_runner.py::_run_brief
    def test_run_brief_prints_render_agent_brief_result(
        self, tmp_path: Path, capsys
    ) -> None:
        """`run(["brief", <id>, "--path", <root>])` prints exactly what
        `render_agent_brief` composed -- true end-to-end CLI parity, not a
        monkeypatched stand-in."""
        import frob.app.agent_runner as agent_runner_mod

        _write_playbook(tmp_path)
        _write_ticket(tmp_path, _ticket(scope=("src/frob/widget.py",)))
        expected = render_agent_brief(tmp_path, "T-0001")
        assert expected.is_ok, expected.err

        agent_runner_mod.run(["brief", "T-0001", "--path", str(tmp_path)])
        out = capsys.readouterr().out
        assert "src/frob/widget.py" in out
        assert expected.danger_ok.strip() in out
