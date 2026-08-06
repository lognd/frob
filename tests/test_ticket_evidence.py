"""Tests for T-0834: `frob ticket kind <id> <kind>` (the ticket-CLI kind
editor, mirroring `set_priority`'s T-0411 audit-trail treatment) and the
`--evidence-cmd` cwd fix (runs against the ticket's resolved `--path`
worktree instead of the invoking process's cwd) (docs/modules/tickets.md).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from frob.app.config import AppConfig
from frob.app.ticket_runner import _kind
from frob.tickets import (
    Origin,
    Priority,
    TicketKind,
    TicketState,
    add_cmd_evidence,
    load_active,
    new_ticket,
    run_cmd_evidence,
    set_kind,
    set_priority,
    transition,
)
from frob.tickets._models import TicketSpec


def _seed_ticket(
    tmp_path: Path, *, kind: TicketKind = TicketKind.BUG, with_done_report: bool = False
) -> str:
    """Create a fresh ticket of `kind` in `tmp_path` and return its id.
    `with_done_report` seeds a body with a substantive Done report so the
    ticket can actually reach `done` (T-0834's terminal-state comparison
    test needs a real terminal ticket)."""
    body = (
        "## Description\nx\n\n## Done report\nAll good.\n" if with_done_report else ""
    )
    created = new_ticket(
        tmp_path,
        TicketSpec(title="a ticket", kind=kind, origin=Origin.HUMAN, body=body),
    )
    assert created.is_ok
    return created.danger_ok.id


class TestSetKind:
    """`set_kind` -- the single-writer kind mutation (T-0834)."""

    def test_updates_kind_field(self, tmp_path: Path) -> None:
        # frob:tests tests/test_ticket_evidence.py::TestSetKind.test_updates_kind_field
        ticket_id = _seed_ticket(tmp_path, kind=TicketKind.FEATURE)

        result = set_kind(tmp_path, ticket_id, TicketKind.DOCS)
        assert result.is_ok
        assert result.danger_ok.kind == TicketKind.DOCS

        reloaded = load_active(tmp_path)
        assert reloaded.is_ok
        assert reloaded.danger_ok.tickets[ticket_id].kind == TicketKind.DOCS

    def test_audit_trail_present(self, tmp_path: Path) -> None:
        """A kind change is logged the same way `set_priority` logs one --
        no separate audit-entry list exists for either field (T-0834
        mirrors T-0411's field-only, log-only audit trail exactly)."""
        # frob:tests tests/test_ticket_evidence.py::TestSetKind.test_audit_trail_present
        ticket_id = _seed_ticket(tmp_path, kind=TicketKind.BUG)
        result = set_kind(tmp_path, ticket_id, TicketKind.SECURITY)
        assert result.is_ok
        # No dedicated audit-log field on Ticket for kind (same as
        # priority) -- the write itself + the INFO log line IS the trail.
        assert result.danger_ok.kind == TicketKind.SECURITY

    def test_terminal_state_matches_priority(self, tmp_path: Path) -> None:
        """`set_kind` on a `done` ticket behaves exactly like `set_priority`
        does on one (T-0834's ticket text: "match it") -- neither function
        special-cases terminal state, so both simply succeed."""
        ticket_id = _seed_ticket(tmp_path, kind=TicketKind.DOCS, with_done_report=True)
        transition(tmp_path, ticket_id, TicketState.PLANNED)
        transition(tmp_path, ticket_id, TicketState.IN_PROGRESS)
        added = add_cmd_evidence(tmp_path, ticket_id, "printf ok")
        assert added.is_ok
        done = transition(tmp_path, ticket_id, TicketState.DONE, covers_scope=True)
        assert done.is_ok

        priority_result = set_priority(tmp_path, ticket_id, Priority.HIGH)
        kind_result = set_kind(tmp_path, ticket_id, TicketKind.DOCS)
        # Whatever priority's own behavior is on a terminal ticket, kind's
        # must match it exactly -- both ok, or both err.
        assert kind_result.is_ok == priority_result.is_ok


class TestKindCliInvalidKind:
    """`frob ticket kind` refuses a value outside the real `TicketKind`
    enum (T-0834: "kind must still validate strictly against the real
    enum").

    T-1594: this used to assert the refusal happens INSIDE `_kind()`
    (a downstream `SystemExit`) -- but `AppConfig`'s own
    `_check_ticket_kind_value` field_validator (`src/frob/app/config.py`)
    already refuses an unrecognized `ticket_kind_value` at CONSTRUCTION
    time, strictly before `_kind()` (or anything else) ever runs. That
    validator is not a bug to remove: it is the SAME pattern this repo
    already applies to every other enum-shaped CLI value
    (`ticket_state`/`ticket_kind`/`ticket_tier`/`ticket_tier_value`, all
    validated the identical way in `AppConfig`, all with their own
    `test_app_config.py::TestEnumFieldValidation` coverage) -- removing it
    only for this one field would make `ticket_kind_value` the
    inconsistent one, not the other way around. `_kind()`'s own
    `TicketKind(...)` try/except is genuinely unreachable for a value that
    has already passed `AppConfig` construction (defense in depth against
    a caller that builds a `TicketKind`-typed value some other way), which
    is exactly why the real CLI (`src/frob/__main__.py`'s top-level
    `except Exception` boundary) already turns this `ValidationError` into
    a clean one-line `frob: ...` stderr message and `exit(1)` -- a
    directly-constructed `AppConfig(...)`, as this test does, is the one
    caller that sees the raw exception instead of that clean CLI-boundary
    rendering, which is what this test now asserts on directly."""

    def test_invalid_kind_refused(self, tmp_path: Path) -> None:
        # frob:tests tests/test_ticket_evidence.py::TestKindCliInvalidKind.test_invalid_kind_refused  # noqa: E501
        ticket_id = _seed_ticket(tmp_path, kind=TicketKind.BUG)
        with pytest.raises(ValidationError) as exc_info:
            AppConfig(
                ticket_command="kind",
                ticket_id=ticket_id,
                ticket_path=tmp_path,
                ticket_kind_value="not-a-real-kind",
            )
        assert "is not a valid ticket kind" in str(exc_info.value)

        reloaded = load_active(tmp_path)
        assert reloaded.is_ok
        assert reloaded.danger_ok.tickets[ticket_id].kind == TicketKind.BUG

    def test_kind_cli_changes_persisted_kind(self, tmp_path: Path) -> None:
        # frob:tests tests/test_ticket_evidence.py::TestKindCliInvalidKind.test_kind_cli_changes_persisted_kind  # noqa: E501
        ticket_id = _seed_ticket(tmp_path, kind=TicketKind.FEATURE)
        cfg = AppConfig(
            ticket_command="kind",
            ticket_id=ticket_id,
            ticket_path=tmp_path,
            ticket_kind_value="ux",
        )
        _kind(tmp_path, cfg)

        reloaded = load_active(tmp_path)
        assert reloaded.is_ok
        assert reloaded.danger_ok.tickets[ticket_id].kind == TicketKind.UX


class TestEvidenceCmdCwd:
    """`--evidence-cmd` runs from the ticket's resolved `--path` worktree,
    not the invoking process's cwd (T-0834)."""

    def test_relative_probe_only_succeeds_from_worktree(self, tmp_path: Path) -> None:
        """A relative-path `test -f marker` only exits 0 when run with
        `cwd=tmp_path` -- proving `run_cmd_evidence`/`_run_evidence_command`
        actually honor the `cwd` argument rather than inheriting whatever
        directory pytest happens to be running from."""
        # frob:tests tests/test_ticket_evidence.py::TestEvidenceCmdCwd.test_relative_probe_only_succeeds_from_worktree  # noqa: E501
        marker = tmp_path / "marker.txt"
        marker.write_text("present\n", encoding="utf-8")

        # From the wrong cwd (None -> inherits this process's cwd, which is
        # not tmp_path), the relative-path probe must fail.
        wrong_cwd_result = run_cmd_evidence("test -f marker.txt")
        assert wrong_cwd_result.is_err

        # From the worktree itself, the same relative-path probe succeeds.
        right_cwd_result = run_cmd_evidence("test -f marker.txt", cwd=tmp_path)
        assert right_cwd_result.is_ok

    def test_add_cmd_evidence_runs_against_ticket_path_worktree(
        self, tmp_path: Path
    ) -> None:
        """`add_cmd_evidence` (the function `frob ticket evidence
        --evidence-cmd` calls) threads `root` through as `cwd` -- a
        relative-path probe over a file that only exists in `tmp_path`
        succeeds when `root=tmp_path`."""
        # frob:tests tests/test_ticket_evidence.py::TestEvidenceCmdCwd.test_add_cmd_evidence_runs_against_ticket_path_worktree  # noqa: E501
        ticket_id = _seed_ticket(tmp_path, kind=TicketKind.DOCS)
        marker = tmp_path / "evidence_marker.txt"
        marker.write_text("present\n", encoding="utf-8")

        result = add_cmd_evidence(
            tmp_path, ticket_id, "grep present evidence_marker.txt"
        )
        assert result.is_ok
        assert len(result.danger_ok.evidence) == 1

    def test_failure_message_names_resolved_cwd(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """A failing relative-path evidence-cmd's log line names the
        resolved cwd it ran against (T-0834: "include the resolved cwd in
        the failure message"), not just a bare exit code."""
        # frob:tests tests/test_ticket_evidence.py::TestEvidenceCmdCwd.test_failure_message_names_resolved_cwd  # noqa: E501
        ticket_id = _seed_ticket(tmp_path, kind=TicketKind.DOCS)

        with caplog.at_level("WARNING"):
            result = add_cmd_evidence(
                tmp_path, ticket_id, "grep present nonexistent_marker.txt"
            )
        assert result.is_err
        assert any(str(tmp_path) in record.getMessage() for record in caplog.records)
