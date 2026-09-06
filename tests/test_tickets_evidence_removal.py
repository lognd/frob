"""Tests for T-4000 (F-215): the evidence-removal retraction path
(`frob ticket evidence <id> --remove EVIDENCE-ID --reason TEXT`) and the
`--evidence-cmd --cwd DIR` fix that removes the pressure toward shell-ish
workarounds (`cd DIR && cmd`, `npx --prefix DIR <tool>`) which manufactured
a false empty-output evidence entry in the first place
(docs/modules/tickets.md).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.app.config import AppConfig
from frob.app.ticket_runner import _evidence
from frob.tickets import (
    Origin,
    TicketError,
    TicketKind,
    TicketState,
    add_cmd_evidence,
    load_queue,
    new_ticket,
    transition,
)
from frob.tickets._evidence import remove_evidence
from frob.tickets._models import TicketSpec


def _seed_docs_ticket(tmp_path: Path) -> str:
    """Create T-0001, a docs-kind ticket In-progress, and return its id."""
    new_ticket(
        tmp_path,
        TicketSpec(
            title="evidence removal subject",
            kind=TicketKind.DOCS,
            origin=Origin.AGENT,
            body="## Description\nx\n\n## Done report\nAll good.\n",
        ),
    )
    transition(tmp_path, "T-0001", TicketState.PLANNED)
    transition(tmp_path, "T-0001", TicketState.IN_PROGRESS)
    return "T-0001"


class TestRemoveEvidence:
    """`remove_evidence` -- the no-exit retraction path a false/no-op
    `cmd:` entry needed and `--replace` structurally cannot provide (its
    replacement id must itself resolve/pass, which a false claim has
    nothing legitimate to satisfy)."""

    def test_remove_drops_id_from_flat_list_and_acceptance(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/tickets/_evidence.py::remove_evidence
        # frob:ticket T-4000
        ticket_id = _seed_docs_ticket(tmp_path)
        recorded = add_cmd_evidence(tmp_path, ticket_id, "printf ok")
        assert recorded.is_ok
        entry = recorded.danger_ok.evidence[0]

        removed = remove_evidence(tmp_path, ticket_id, entry, reason="was a false claim")
        assert removed.is_ok
        ticket = removed.danger_ok
        assert entry not in ticket.evidence
        assert all(entry not in c.evidence for c in ticket.acceptance)
        assert ticket.evidence_changes[-1].old_node == entry
        assert ticket.evidence_changes[-1].new_node == ""
        assert ticket.evidence_changes[-1].reason == "was a false claim"

    def test_remove_not_found_is_err(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_evidence.py::remove_evidence
        # frob:ticket T-4000
        ticket_id = _seed_docs_ticket(tmp_path)
        result = remove_evidence(
            tmp_path, ticket_id, "cmd:nope exit=0 sha256=aaaaaaaaaaaa", reason="x"
        )
        assert result.is_err
        assert result.danger_err == TicketError.EvidenceReplaceNotFound

    def test_remove_requires_reason(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_evidence.py::remove_evidence
        # frob:ticket T-4000
        ticket_id = _seed_docs_ticket(tmp_path)
        recorded = add_cmd_evidence(tmp_path, ticket_id, "printf ok")
        assert recorded.is_ok
        entry = recorded.danger_ok.evidence[0]

        result = remove_evidence(tmp_path, ticket_id, entry, reason="   ")
        assert result.is_err
        assert result.danger_err == TicketError.EvidenceReplaceReasonMissing


class TestEvidenceRemoveCli:
    """`frob ticket evidence <id> --remove EVIDENCE-ID --reason TEXT`."""

    def test_cli_remove_channel(self, tmp_path: Path) -> None:
        # frob:tests src/frob/app/ticket_runner/_verify.py::_evidence_apply_remove
        # frob:ticket T-4000
        ticket_id = _seed_docs_ticket(tmp_path)
        recorded = add_cmd_evidence(tmp_path, ticket_id, "printf ok")
        assert recorded.is_ok
        entry = recorded.danger_ok.evidence[0]

        cfg = AppConfig(
            ticket_command="evidence",
            ticket_id=ticket_id,
            ticket_path=tmp_path,
            ticket_evidence_remove=entry,
            ticket_evidence_replace_reason="false evidence, correcting",
        )
        _evidence(tmp_path, cfg)

        queue = load_queue(tmp_path).danger_ok
        assert entry not in queue.tickets[ticket_id].evidence

    def test_cli_remove_without_reason_exits_nonzero(self, tmp_path: Path) -> None:
        # frob:tests src/frob/app/ticket_runner/_verify.py::_evidence_apply_remove
        # frob:ticket T-4000
        ticket_id = _seed_docs_ticket(tmp_path)
        recorded = add_cmd_evidence(tmp_path, ticket_id, "printf ok")
        assert recorded.is_ok
        entry = recorded.danger_ok.evidence[0]

        cfg = AppConfig(
            ticket_command="evidence",
            ticket_id=ticket_id,
            ticket_path=tmp_path,
            ticket_evidence_remove=entry,
        )
        with pytest.raises(SystemExit) as exc:
            _evidence(tmp_path, cfg)
        assert exc.value.code != 0


class TestEvidenceCmdCwdFlag:
    """`--evidence-cmd --cwd DIR` (T-4000, F-215): the documented answer
    to "run this in that subdirectory" that removes the pressure toward
    `cd DIR && cmd` (fails loudly, honest) / `npx --prefix DIR <tool>`
    (the shape that manufactured an empty-output false-evidence entry
    against a non-npm binary)."""

    def test_cwd_runs_against_named_subdirectory(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_evidence.py::add_cmd_evidence
        # frob:ticket T-4000
        ticket_id = _seed_docs_ticket(tmp_path)
        sub = tmp_path / "frontend"
        sub.mkdir()
        (sub / "marker.txt").write_text("present\n", encoding="utf-8")

        # Without --cwd, a relative-path probe against the subdirectory's
        # file fails: the default cwd is root, not root/frontend.
        wrong = add_cmd_evidence(tmp_path, ticket_id, "grep -c present marker.txt")
        assert wrong.is_err

        right = add_cmd_evidence(
            tmp_path, ticket_id, "grep -c present marker.txt", cwd="frontend"
        )
        assert right.is_ok

    def test_cwd_escape_attempt_is_refused(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_evidence.py::add_cmd_evidence
        # frob:ticket T-4000
        ticket_id = _seed_docs_ticket(tmp_path)
        result = add_cmd_evidence(tmp_path, ticket_id, "printf ok", cwd="..")
        assert result.is_err
        assert result.danger_err == TicketError.EvidenceCmdFailed

    def test_cli_cwd_channel(self, tmp_path: Path) -> None:
        # frob:tests src/frob/app/ticket_runner/_verify.py::_evidence_apply_cmd
        # frob:ticket T-4000
        ticket_id = _seed_docs_ticket(tmp_path)
        sub = tmp_path / "frontend"
        sub.mkdir()
        (sub / "marker.txt").write_text("present\n", encoding="utf-8")

        cfg = AppConfig(
            ticket_command="evidence",
            ticket_id=ticket_id,
            ticket_path=tmp_path,
            ticket_evidence_cmd="grep -c present marker.txt",
            ticket_evidence_cwd="frontend",
        )
        _evidence(tmp_path, cfg)

        queue = load_queue(tmp_path).danger_ok
        assert len(queue.tickets[ticket_id].evidence) == 1
