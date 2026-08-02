"""T-1427: end-to-end regression tests proving BUG002
(`frob.gates._mutation_evidence.bug_repro_violations`, built by T-1421)
now has a live caller through the REAL `frob ticket close` entry point,
not just its own unit tests (`tests/test_gates_mutation_evidence.py`).

This is BUG002's own root-cause pattern, reconstructed one more time: a
guard function (`bug_repro_violations`) built and directly unit-tested,
but with NO caller in the real close/land path -- exactly the T-1384/
T-1391/T-1399/T-1239/T-1401/T-1422 shape BUG002 itself exists to catch,
and which BUG002 itself then reproduced by landing with no wiring (T-1421).
These tests drive the REAL `ticket_runner._close` entry point end to end;
they monkeypatch only the two genuine subprocess/external-git boundaries
(`_bug_repro_outcome_at_ref`, `check_ticket_mutation_evidence`) so no
actual `git worktree add`/mutation subprocess spawn happens during the
test, mirroring T-1410's own precedent
(`tests/unit/test_ticket_close_gate_claims_t1410.py`'s
`guarded_subprocess_run` monkeypatch) of stubbing the external-process
seam while still exercising the real wiring path."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
from typani.result import Ok

_BUG_EVIDENCE = "tests/unit/fake/test_repro.py::test_bug_repro"


def _write_bug_ticket(root: Path, ticket_id: str = "T-0901") -> None:
    """A `kind=bug` ticket, closeable on every OTHER guard (has evidence +
    Done report, no acceptance criteria to complicate D-02/T-1410), whose
    single evidence id is the BUG002 designated repro test."""
    from frob.tickets import Origin, Ticket, TicketKind, TicketState
    from frob.tickets._store import _serialize_ticket

    ticket = Ticket(
        id=ticket_id,
        title="sample bug",
        state=TicketState.IN_PROGRESS,
        kind=TicketKind.BUG,
        origin=Origin.HUMAN,
        created=date(2026, 1, 1),
        evidence=(_BUG_EVIDENCE,),
        body="## Description\nx\n\n## Done report\nDone.\n",
    )
    tickets_dir = root / "tickets"
    tickets_dir.mkdir(parents=True, exist_ok=True)
    (tickets_dir / f"{ticket_id}-sample-bug.md").write_text(
        _serialize_ticket(ticket), encoding="utf-8"
    )


def _bypass_other_close_guards(monkeypatch: pytest.MonkeyPatch, ticket_runner) -> None:  # noqa: ANN001
    """Skip every close-time guard OTHER than the mutation-evidence guard
    BUG002 now feeds into (`_close_mutation_evidence_for_ticket`),
    isolating the refusal this test suite cares about, mirroring T-1410's
    own `_bypass_other_close_guards` shape."""
    monkeypatch.setattr(
        ticket_runner, "_covers_scope_for_ticket", lambda root, ticket: None
    )
    monkeypatch.setattr(
        ticket_runner, "_reverify_evidence_for_close", lambda root, ticket: None
    )
    monkeypatch.setattr(
        ticket_runner, "_close_gate_claims_for_ticket", lambda root, ticket: None
    )
    monkeypatch.setattr(
        ticket_runner, "_close_own_obligations_for_ticket", lambda root, ticket: None
    )


def _init_repo(root: Path) -> None:
    """A minimal real git repo (BUG002's `current_branch(root)` call needs
    a genuine `HEAD`/branch to resolve, even though the actual repro
    subprocess is stubbed below)."""
    import subprocess

    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"], cwd=root, check=True
    )
    subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
    subprocess.run(["git", "checkout", "-q", "-b", "main"], cwd=root, check=True)
    _write_bug_ticket(root)
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=root, check=True)


def _no_mutation_findings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stub TEST016's own subprocess seam
    (`check_ticket_mutation_evidence`) to report no findings, so ONLY
    BUG002 can contribute an ERROR-severity violation in these tests --
    isolates the refusal to the guard this ticket wires in."""
    monkeypatch.setattr(
        "frob.gates._mutation_evidence.check_ticket_mutation_evidence",
        lambda root, ticket, base_ref: Ok(()),
    )


class TestCloseRefusesBug002ShapeEndToEnd:
    """Drives the REAL `frob ticket close` entry point
    (`ticket_runner._close`) against a `kind=bug` ticket whose designated
    evidence test PASSES at both its parent and its (simulated) fix commit
    -- the acceptance test this series exists for: BUG002 must refuse this
    through the real close path, not just its own unit tests."""

    def test_close_refuses_when_evidence_passes_at_parent(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_ticket_close_bug002_t1427.py::TestCloseRefusesBug002ShapeEndToEnd.test_close_refuses_when_evidence_passes_at_parent  # noqa: E501
        from frob.app import ticket_runner
        from frob.app.config import AppConfig
        from frob.gates._mutation_evidence import _BugReproOutcome
        from frob.tickets import TicketState, load_all

        _init_repo(tmp_path)
        _bypass_other_close_guards(monkeypatch, ticket_runner)
        _no_mutation_findings(monkeypatch)
        monkeypatch.setattr(
            "frob.gates._mutation_evidence._bug_repro_outcome_at_ref",
            lambda root, test_id, base_ref: _BugReproOutcome.PASSED_AT_PARENT,
        )
        cfg = AppConfig(ticket_id="T-0901")
        with pytest.raises(SystemExit):
            ticket_runner._close(tmp_path, cfg)
        loaded = load_all(tmp_path)
        assert loaded.is_ok
        assert loaded.danger_ok["T-0901"].state == TicketState.IN_PROGRESS

    def test_close_succeeds_when_evidence_fails_at_parent(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_ticket_close_bug002_t1427.py::TestCloseRefusesBug002ShapeEndToEnd.test_close_succeeds_when_evidence_fails_at_parent  # noqa: E501
        from frob.app import ticket_runner
        from frob.app.config import AppConfig
        from frob.gates._mutation_evidence import _BugReproOutcome
        from frob.tickets import TicketState, load_all

        _init_repo(tmp_path)
        _bypass_other_close_guards(monkeypatch, ticket_runner)
        _no_mutation_findings(monkeypatch)
        monkeypatch.setattr(
            "frob.gates._mutation_evidence._bug_repro_outcome_at_ref",
            lambda root, test_id, base_ref: _BugReproOutcome.FAILED_AT_PARENT,
        )
        cfg = AppConfig(ticket_id="T-0901")
        ticket_runner._close(tmp_path, cfg)
        loaded = load_all(tmp_path)
        assert loaded.is_ok
        assert loaded.danger_ok["T-0901"].state == TicketState.DONE
