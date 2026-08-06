"""Unit tests for `frob.tickets._mutation_sweep_queue` (T-1518)."""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.tickets import Origin, TicketKind, new_ticket
from frob.tickets._models import TicketSpec
from frob.tickets._mutation_sweep_queue import (
    enqueue_pending_sweep,
    pending_sweep_count,
    run_pending_sweep,
)


# frob:waive WIRE001 reason="a private test-seed helper used only by this file's own \
# test methods below -- there is no production caller to wire it to by design, \
# mirroring tests/unit/test_ticket_file_flags.py's identical _make_ticket precedent" \
# follow_up="T-1592"
def _make_ticket(tmp_path: Path, *, kind: TicketKind) -> str:
    spec = TicketSpec(title="seed", kind=kind, origin=Origin.HUMAN)
    result = new_ticket(tmp_path, spec)
    assert result.is_ok
    return result.danger_ok.id


class TestEnqueuePendingSweep:
    """`enqueue_pending_sweep` appends a `pending` entry and persists it."""

    def test_enqueue_persists_entry(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_mutation_sweep_queue.py::TestEnqueuePendingSweep.test_enqueue_persists_entry  # noqa: E501
        ticket_id = _make_ticket(tmp_path, kind=TicketKind.FEATURE)
        result = enqueue_pending_sweep(tmp_path, ticket_id, "main", TicketKind.FEATURE)
        assert result.is_ok
        entry = result.danger_ok
        assert entry.ticket_id == ticket_id
        assert entry.status == "pending"
        count = pending_sweep_count(tmp_path)
        assert count.is_ok
        assert count.danger_ok == 1


class TestPendingSweepCount:
    """`pending_sweep_count` counts only `pending` entries."""

    def test_counts_only_pending_entries(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_mutation_sweep_queue.py::TestPendingSweepCount.test_counts_only_pending_entries  # noqa: E501
        ticket_a = _make_ticket(tmp_path, kind=TicketKind.FEATURE)
        ticket_b = _make_ticket(tmp_path, kind=TicketKind.FEATURE)
        enqueue_pending_sweep(tmp_path, ticket_a, "main", TicketKind.FEATURE)
        enqueue_pending_sweep(tmp_path, ticket_b, "main", TicketKind.FEATURE)
        assert pending_sweep_count(tmp_path).danger_ok == 2

        from typani.result import Ok

        import frob.tickets._mutation_evidence as mutation_evidence_mod

        monkeypatch.setattr(
            mutation_evidence_mod,
            "check_ticket_mutation_evidence",
            lambda *a, **k: Ok(()),
        )
        run_pending_sweep(tmp_path)
        assert pending_sweep_count(tmp_path).danger_ok == 0


class TestRunPendingSweep:
    """`run_pending_sweep` processes every pending entry."""

    def test_empty_queue_is_noop(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_mutation_sweep_queue.py::TestRunPendingSweep.test_empty_queue_is_noop  # noqa: E501
        result = run_pending_sweep(tmp_path)
        assert result.is_ok
        assert result.danger_ok == 0

    def test_clean_finding_marks_swept_no_ticket_filed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_mutation_sweep_queue.py::TestRunPendingSweep.test_clean_finding_marks_swept_no_ticket_filed  # noqa: E501
        ticket_id = _make_ticket(tmp_path, kind=TicketKind.FEATURE)
        enqueue_pending_sweep(tmp_path, ticket_id, "main", TicketKind.FEATURE)

        from typani.result import Ok

        import frob.tickets._mutation_evidence as mutation_evidence_mod

        monkeypatch.setattr(
            mutation_evidence_mod,
            "check_ticket_mutation_evidence",
            lambda *a, **k: Ok(()),
        )

        result = run_pending_sweep(tmp_path)
        assert result.is_ok
        assert result.danger_ok == 1
        assert pending_sweep_count(tmp_path).danger_ok == 0

    def test_bug_kind_confirmatory_finding_files_ticket(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_mutation_sweep_queue.py::TestRunPendingSweep.test_bug_kind_confirmatory_finding_files_ticket  # noqa: E501
        ticket_id = _make_ticket(tmp_path, kind=TicketKind.BUG)
        enqueue_pending_sweep(tmp_path, ticket_id, "main", TicketKind.BUG)

        from typani.result import Ok

        import frob.tickets._mutation_evidence as mutation_evidence_mod
        from frob.tickets._mutation_evidence import ConfirmatoryFinding

        finding = ConfirmatoryFinding(
            ticket_id=ticket_id,
            file="src/frob/x.py",
            tests=("t::test_x",),
            mutants_total=3,
        )
        monkeypatch.setattr(
            mutation_evidence_mod,
            "check_ticket_mutation_evidence",
            lambda *a, **k: Ok((finding,)),
        )

        before = new_ticket(
            tmp_path,
            TicketSpec(title="noop", kind=TicketKind.FEATURE, origin=Origin.HUMAN),
        )
        assert before.is_ok

        result = run_pending_sweep(tmp_path)
        assert result.is_ok
        assert result.danger_ok == 1

        from frob.tickets import load_queue

        queue = load_queue(tmp_path).danger_ok
        filed = [
            t
            for t in queue.tickets.values()
            if t.kind is TicketKind.BUG and ticket_id in t.body
        ]
        assert len(filed) == 1

    def test_non_bug_confirmatory_finding_only_warns(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_mutation_sweep_queue.py::TestRunPendingSweep.test_non_bug_confirmatory_finding_only_warns  # noqa: E501
        ticket_id = _make_ticket(tmp_path, kind=TicketKind.FEATURE)
        enqueue_pending_sweep(tmp_path, ticket_id, "main", TicketKind.FEATURE)

        from typani.result import Ok

        import frob.tickets._mutation_evidence as mutation_evidence_mod
        from frob.tickets._mutation_evidence import ConfirmatoryFinding

        finding = ConfirmatoryFinding(
            ticket_id=ticket_id,
            file="src/frob/x.py",
            tests=("t::test_x",),
            mutants_total=3,
        )
        monkeypatch.setattr(
            mutation_evidence_mod,
            "check_ticket_mutation_evidence",
            lambda *a, **k: Ok((finding,)),
        )

        from frob.tickets import load_queue

        before_count = len(load_queue(tmp_path).danger_ok.tickets)

        result = run_pending_sweep(tmp_path)
        assert result.is_ok
        assert result.danger_ok == 1

        after_count = len(load_queue(tmp_path).danger_ok.tickets)
        assert after_count == before_count
