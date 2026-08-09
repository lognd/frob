"""Unit tests for T-0215: the non-pytest evidence channel (`--evidence-cmd`)
for docs-kind tickets, the InvalidTransition/MissingEvidence CLI hints, and
(review round 2) the COV003 gate + close/land kind-consistency checks that
keep a `cmd:` evidence entry honest end to end (docs/modules/tickets.md).
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
from typani.result import Err, Result

from frob.app.config import AppConfig
from frob.app.ticket_runner import _close, _evidence, _start
from frob.gates import coverage_gate
from frob.gitio import Diff
from frob.graph import build_graph
from frob.testing import CollectedTests
from frob.tickets import (
    Origin,
    Ticket,
    TicketError,
    TicketKind,
    TicketState,
    is_cmd_evidence,
    load_queue,
    new_ticket,
    run_cmd_evidence,
    transition,
)
from frob.tickets._land_merge import _validate_closeable
from frob.tickets._models import TicketSpec
from frob.tickets._store import write_ticket


def _seed_ticket(
    tmp_path: Path, *, kind: TicketKind, state: TicketState = TicketState.IN_PROGRESS
) -> None:
    """Create T-0001 of `kind`, optionally transitioned up to `state`."""
    new_ticket(
        tmp_path,
        TicketSpec(
            title="cmd evidence subject",
            kind=kind,
            origin=Origin.AGENT,
            body="## Description\nx\n\n## Done report\nAll good.\n",
        ),
    )
    if state in (TicketState.PLANNED, TicketState.IN_PROGRESS):
        transition(tmp_path, "T-0001", TicketState.PLANNED)
    if state == TicketState.IN_PROGRESS:
        transition(tmp_path, "T-0001", TicketState.IN_PROGRESS)


class TestIsCmdEvidence:
    """`is_cmd_evidence` -- the shared shape check (T-0215 review round 2)."""

    def test_shapes(self) -> None:
        # frob:tests src/frob/tickets/_models.py::is_cmd_evidence
        assert is_cmd_evidence("cmd:printf ok exit=0 sha256=aaaaaaaaaaaa")
        assert not is_cmd_evidence("cmd:printf ok exit=0 sha256=short")
        assert not is_cmd_evidence("tests/test_x.py::test_a")
        assert not is_cmd_evidence("")


class TestCmdEvidence:
    """`run_cmd_evidence` -- the raw run-and-digest primitive.

    frob:ticket T-1152
    """

    def test_exit_zero(self) -> None:
        # frob:tests src/frob/tickets/_evidence.py::run_cmd_evidence
        # frob:ticket T-1152
        result = run_cmd_evidence("printf hello")
        assert result.is_ok
        entry = result.danger_ok
        assert entry.startswith("cmd:printf hello exit=0 sha256=")

    def test_nonzero_exit(self) -> None:
        # frob:tests src/frob/tickets/_evidence.py::run_cmd_evidence
        # frob:ticket T-1152
        result = run_cmd_evidence("false")
        assert result.is_err
        assert result.danger_err == TicketError.EvidenceCmdFailed

    def test_same_output_is_deterministic(self) -> None:
        first = run_cmd_evidence("printf hello")
        second = run_cmd_evidence("printf hello")
        assert first.danger_ok == second.danger_ok


class TestSilentCmdEvidenceRefused:
    """(T-1892) a zero-exit command with empty captured stdout+stderr is
    refused, not recorded with the empty-string sha256 -- MEASURED
    2026-08-09 closing T-1644: `grep -q` (silent by design) recorded
    `sha256=e3b0c44298fc` (the digest of ""), a digest `true`/`: `/`cd .`
    would all collide on identically, carrying zero information about
    what was actually verified."""

    def test_silent_zero_exit_command_is_refused(self) -> None:
        # frob:tests src/frob/tickets/_evidence.py::run_cmd_evidence
        # frob:ticket T-1892
        result = run_cmd_evidence("true")
        assert result.is_err
        assert result.danger_err == TicketError.EvidenceCmdSilent

    def test_grep_q_silent_match_is_refused(self) -> None:
        # frob:tests src/frob/tickets/_evidence.py::run_cmd_evidence
        # frob:ticket T-1892
        # the exact T-1892 incident shape: a silent `grep -q` on a real,
        # existing match still produces empty stdout+stderr.
        result = run_cmd_evidence("grep -q run_cmd_evidence tests/test_tickets_cmd_evidence.py")
        assert result.is_err
        assert result.danger_err == TicketError.EvidenceCmdSilent

    def test_chatty_zero_exit_command_is_accepted(self) -> None:
        # frob:tests src/frob/tickets/_evidence.py::run_cmd_evidence
        # frob:ticket T-1892
        # the sanctioned fix: `grep -c` (chatty, emits the count) over
        # `grep -q` (silent) for the exact same underlying check.
        result = run_cmd_evidence("grep -c run_cmd_evidence tests/test_tickets_cmd_evidence.py")
        assert result.is_ok
        assert result.danger_ok.startswith("cmd:grep -c run_cmd_evidence")


class TestKindGate:
    """Only docs-kind tickets may close on `--evidence-cmd` alone (T-0215).

    frob:ticket T-1152
    """

    def test_bug_kind_rejected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_evidence.py::add_cmd_evidence
        # frob:ticket T-1152
        _seed_ticket(tmp_path, kind=TicketKind.BUG)
        cfg = AppConfig(
            ticket_command="close",
            ticket_id="T-0001",
            ticket_path=tmp_path,
            ticket_evidence_cmd="printf ok",
        )
        with pytest.raises(SystemExit) as exc:
            _close(tmp_path, cfg)
        assert exc.value.code != 0

        queue = load_queue(tmp_path).danger_ok
        ticket = queue.tickets["T-0001"]
        assert ticket.state == TicketState.IN_PROGRESS
        assert ticket.evidence == ()

    def test_bug_kind_ticket_cannot_close_on_cmd_evidence_alone(
        self, tmp_path: Path
    ) -> None:
        # Explicit precedent test per T-0215's plan: a bug-kind ticket must
        # never reach DONE off cmd evidence, even if the command succeeds.
        _seed_ticket(tmp_path, kind=TicketKind.BUG)
        cfg = AppConfig(
            ticket_command="close",
            ticket_id="T-0001",
            ticket_path=tmp_path,
            ticket_evidence_cmd="true",
        )
        with pytest.raises(SystemExit):
            _close(tmp_path, cfg)
        queue = load_queue(tmp_path).danger_ok
        assert queue.tickets["T-0001"].state != TicketState.DONE

    def test_feature_kind_ticket_rejected(self, tmp_path: Path) -> None:
        _seed_ticket(tmp_path, kind=TicketKind.FEATURE)
        cfg = AppConfig(
            ticket_command="close",
            ticket_id="T-0001",
            ticket_path=tmp_path,
            ticket_evidence_cmd="printf ok",
        )
        with pytest.raises(SystemExit):
            _close(tmp_path, cfg)
        queue = load_queue(tmp_path).danger_ok
        assert queue.tickets["T-0001"].evidence == ()

    def test_security_kind_ticket_rejected(self, tmp_path: Path) -> None:
        _seed_ticket(tmp_path, kind=TicketKind.SECURITY)
        cfg = AppConfig(
            ticket_command="close",
            ticket_id="T-0001",
            ticket_path=tmp_path,
            ticket_evidence_cmd="printf ok",
        )
        with pytest.raises(SystemExit):
            _close(tmp_path, cfg)
        queue = load_queue(tmp_path).danger_ok
        assert queue.tickets["T-0001"].evidence == ()

    def test_docs_kind_closes(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_evidence.py::add_cmd_evidence
        # frob:ticket T-1152
        _seed_ticket(tmp_path, kind=TicketKind.DOCS)
        cfg = AppConfig(
            ticket_command="close",
            ticket_id="T-0001",
            ticket_path=tmp_path,
            ticket_evidence_cmd="printf ok",
        )
        _close(tmp_path, cfg)

        queue = load_queue(tmp_path).danger_ok
        ticket = queue.tickets["T-0001"]
        assert ticket.state == TicketState.DONE
        assert len(ticket.evidence) == 1
        assert ticket.evidence[0].startswith("cmd:printf ok exit=0 sha256=")

    def test_docs_kind_ticket_failing_cmd_blocks_close(self, tmp_path: Path) -> None:
        _seed_ticket(tmp_path, kind=TicketKind.DOCS)
        cfg = AppConfig(
            ticket_command="close",
            ticket_id="T-0001",
            ticket_path=tmp_path,
            ticket_evidence_cmd="false",
        )
        with pytest.raises(SystemExit):
            _close(tmp_path, cfg)
        queue = load_queue(tmp_path).danger_ok
        ticket = queue.tickets["T-0001"]
        assert ticket.state == TicketState.IN_PROGRESS
        assert ticket.evidence == ()


class TestEvidenceCmdViaEvidenceSubcommand:
    """`frob ticket evidence <id> --evidence-cmd '<command>'`."""

    def test_records_cmd_evidence_on_docs_ticket(self, tmp_path: Path) -> None:
        _seed_ticket(tmp_path, kind=TicketKind.DOCS)
        cfg = AppConfig(
            ticket_command="evidence",
            ticket_id="T-0001",
            ticket_path=tmp_path,
            ticket_evidence_cmd="printf ok",
        )
        _evidence(tmp_path, cfg)
        queue = load_queue(tmp_path).danger_ok
        assert len(queue.tickets["T-0001"].evidence) == 1

    def test_requires_ids_or_cmd(self, tmp_path: Path) -> None:
        _seed_ticket(tmp_path, kind=TicketKind.DOCS)
        cfg = AppConfig(
            ticket_command="evidence", ticket_id="T-0001", ticket_path=tmp_path
        )
        with pytest.raises(SystemExit) as exc:
            _evidence(tmp_path, cfg)
        assert exc.value.code != 0


class TestCloseFromQueuedHint:
    """`frob ticket close` on a queued ticket names the `start` remedy (T-0215)."""

    def test_close_on_queued_exits_nonzero(self, tmp_path: Path) -> None:
        _seed_ticket(tmp_path, kind=TicketKind.FEATURE, state=TicketState.QUEUED)
        cfg = AppConfig(
            ticket_command="close", ticket_id="T-0001", ticket_path=tmp_path
        )
        with pytest.raises(SystemExit) as exc:
            _close(tmp_path, cfg)
        assert exc.value.code != 0

        queue = load_queue(tmp_path).danger_ok
        assert queue.tickets["T-0001"].state == TicketState.QUEUED

    def test_close_on_queued_hint_names_start(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        import logging

        _seed_ticket(tmp_path, kind=TicketKind.FEATURE, state=TicketState.QUEUED)
        cfg = AppConfig(
            ticket_command="close", ticket_id="T-0001", ticket_path=tmp_path
        )
        with caplog.at_level(logging.ERROR):
            with pytest.raises(SystemExit):
                _close(tmp_path, cfg)
        assert "frob ticket start T-0001" in caplog.text


class TestMissingEvidenceHint:
    """`MissingEvidence` close failures name where the Done report lives."""

    def test_missing_evidence_hint_names_tickets_md(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        import logging

        new_ticket(
            tmp_path,
            TicketSpec(
                title="no evidence yet",
                kind=TicketKind.FEATURE,
                origin=Origin.AGENT,
                body="## Description\nx\n",
            ),
        )
        transition(tmp_path, "T-0001", TicketState.PLANNED)
        transition(tmp_path, "T-0001", TicketState.IN_PROGRESS)

        cfg = AppConfig(
            ticket_command="close", ticket_id="T-0001", ticket_path=tmp_path
        )
        with caplog.at_level(logging.ERROR):
            with pytest.raises(SystemExit) as exc:
                _close(tmp_path, cfg)
        assert exc.value.code != 0
        assert "tickets.md" in caplog.text
        assert "## Done report" in caplog.text


class TestStartOnInProgress:
    """`frob ticket start` on an already-in-progress ticket (T-0215)."""

    def test_hints_at_sweep_and_exits_nonzero(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        import logging

        _seed_ticket(tmp_path, kind=TicketKind.FEATURE, state=TicketState.IN_PROGRESS)
        cfg = AppConfig(
            ticket_command="start", ticket_id="T-0001", ticket_path=tmp_path
        )
        with caplog.at_level(logging.ERROR):
            with pytest.raises(SystemExit) as exc:
                _start(tmp_path, cfg)
        assert exc.value.code != 0
        assert "frob ticket sweep T-0001" in caplog.text

        # state is untouched by the rejected re-start
        queue = load_queue(tmp_path).danger_ok
        assert queue.tickets["T-0001"].state == TicketState.IN_PROGRESS


def _snapshot(root: Path):
    """Cheap empty-repo graph snapshot -- COV003 only needs `queue`/`tests`,
    but `coverage_gate` takes a snapshot for the sibling COV001/002/004/
    TODO001 checks it also runs; an empty tree is enough for them to no-op."""
    cache = root / ".frob" / "cache.db"
    return build_graph(root, cache).danger_ok


def _raw_ticket(
    *, ticket_id: str = "T-0001", kind: TicketKind, evidence: tuple[str, ...]
) -> Ticket:
    """A DONE ticket built directly (bypassing `transition`/`add_cmd_evidence`
    entirely) so a hand-pasted or kind-flipped `cmd:` evidence entry can
    reach a gate/land check the same way a hand-edited ledger file would --
    proving THAT check's own defense, independent of the write-time guard
    in `add_cmd_evidence`/`_transition_guard`."""
    return Ticket(
        id=ticket_id,
        title="raw",
        state=TicketState.DONE,
        kind=kind,
        origin=Origin.HUMAN,
        created=date(2026, 1, 1),
        evidence=evidence,
        body="## Description\nx\n\n## Done report\ndone\n",
    )


class TestCov003CmdEvidence:
    """COV003 (`frob.gates.coverage_gate`) must format+kind check `cmd:`
    evidence, not silently fail every docs ticket closed via
    `--evidence-cmd` (T-0215 review round 2 -- the reviewer reproduced this
    end to end: `_evidence_collected` never matches a `cmd:` string, so
    every such close used to trip an unconditional COV003 ERROR)."""

    def test_docs_ticket_closed_via_evidence_cmd_is_gate_clean(
        self, tmp_path: Path
    ) -> None:
        # The real record -> close -> gate path: seed a docs ticket, close
        # it through the CLI with --evidence-cmd (which calls
        # add_cmd_evidence + transition exactly like a real session would),
        # then run coverage_gate/COV003 against the resulting ledger and
        # assert it is clean -- no pytest node ids involved anywhere.
        _seed_ticket(tmp_path, kind=TicketKind.DOCS)
        cfg = AppConfig(
            ticket_command="close",
            ticket_id="T-0001",
            ticket_path=tmp_path,
            ticket_evidence_cmd="printf ok",
        )
        _close(tmp_path, cfg)

        queue = load_queue(tmp_path).danger_ok
        assert queue.tickets["T-0001"].state == TicketState.DONE
        snap = _snapshot(tmp_path)
        diff = Diff(base="x", hunks=())
        tests = CollectedTests(node_ids=frozenset())
        violations = coverage_gate(tmp_path, snap, queue, diff, tests)
        assert not any(v.rule == "COV003" for v in violations)

    def test_bug_kind_ticket_with_hand_pasted_cmd_entry_fails_cov003(
        self, tmp_path: Path
    ) -> None:
        # Doubles as the kind-flip/hand-paste protection T-0215's review
        # asked for: this ticket never went through add_cmd_evidence at
        # all (state=DONE, evidence set directly) -- exactly what a
        # hand-edited ledger, or a docs ticket whose kind was changed to
        # bug AFTER cmd: evidence was recorded, would look like on disk.
        entry = "cmd:printf ok exit=0 sha256=aaaaaaaaaaaa"
        assert is_cmd_evidence(entry)
        ticket = _raw_ticket(kind=TicketKind.BUG, evidence=(entry,))
        write_ticket(tmp_path, ticket)

        queue = load_queue(tmp_path).danger_ok
        snap = _snapshot(tmp_path)
        diff = Diff(base="x", hunks=())
        tests = CollectedTests(node_ids=frozenset())
        violations = coverage_gate(tmp_path, snap, queue, diff, tests)
        cov003 = [v for v in violations if v.rule == "COV003"]
        assert len(cov003) == 1
        assert "cmd:" in cov003[0].message

    def test_docs_ticket_with_malformed_cmd_entry_fails_cov003(
        self, tmp_path: Path
    ) -> None:
        # Format check: a docs-kind ticket (kind-permitted) with a
        # malformed cmd: entry (wrong digest length) must still fail --
        # kind alone is not enough, the shape has to match too.
        entry = "cmd:printf ok exit=0 sha256=short"
        assert not is_cmd_evidence(entry)
        ticket = _raw_ticket(kind=TicketKind.DOCS, evidence=(entry,))
        write_ticket(tmp_path, ticket)

        queue = load_queue(tmp_path).danger_ok
        snap = _snapshot(tmp_path)
        diff = Diff(base="x", hunks=())
        tests = CollectedTests(node_ids=frozenset())
        violations = coverage_gate(tmp_path, snap, queue, diff, tests)
        assert any(v.rule == "COV003" for v in violations)


class TestKindConsistencyAtClose:
    """A non-docs ticket carrying a `cmd:` evidence entry must never reach
    DONE, whether the entry arrived via a kind hand-edit after recording or
    a direct hand-paste (T-0215 review round 2)."""

    def test_transition_refuses_close_when_kind_flipped_after_recording(
        self, tmp_path: Path
    ) -> None:
        # Record cmd evidence on a docs ticket (legitimate), then hand-edit
        # the kind to bug BEFORE closing -- transition(..., DONE) must
        # refuse even though evidence + Done report are both present.
        _seed_ticket(tmp_path, kind=TicketKind.DOCS)
        cfg = AppConfig(
            ticket_command="evidence",
            ticket_id="T-0001",
            ticket_path=tmp_path,
            ticket_evidence_cmd="printf ok",
        )
        _evidence(tmp_path, cfg)

        queue = load_queue(tmp_path).danger_ok
        ticket = queue.tickets["T-0001"]
        flipped = ticket.model_copy(update={"kind": TicketKind.BUG})
        write_ticket(tmp_path, flipped)

        result = transition(tmp_path, "T-0001", TicketState.DONE)
        assert result.is_err
        assert result.danger_err == TicketError.EvidenceKindNotAllowed

        queue = load_queue(tmp_path).danger_ok
        assert queue.tickets["T-0001"].state == TicketState.IN_PROGRESS

    def test_land_validate_closeable_refuses_hand_pasted_cmd_entry(self) -> None:
        entry = "cmd:printf ok exit=0 sha256=aaaaaaaaaaaa"
        ticket = _raw_ticket(kind=TicketKind.SECURITY, evidence=(entry,))
        result = _validate_closeable(ticket)
        assert result.is_err
        assert result.danger_err.name == "NotCloseable"

    def test_land_validate_closeable_accepts_docs_cmd_entry(self) -> None:
        entry = "cmd:printf ok exit=0 sha256=aaaaaaaaaaaa"
        ticket = _raw_ticket(kind=TicketKind.DOCS, evidence=(entry,))
        result = _validate_closeable(ticket)
        assert result.is_ok


class TestRunCmdEvidenceLaunchFailure:
    """`run_cmd_evidence`'s OSError branch: a command that fails to launch
    entirely (not just a nonzero exit) also folds to EvidenceCmdFailed.

    frob:ticket T-1152
    """

    def test_oserror_on_launch_is_evidence_cmd_failed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/tickets/_evidence.py::run_cmd_evidence
        # frob:ticket T-1152
        import frob.tickets as tickets_mod

        def _raise(*_args: object, **_kwargs: object) -> None:
            raise OSError("exec format error")

        monkeypatch.setattr(tickets_mod.subprocess, "run", _raise)
        result = run_cmd_evidence("whatever")
        assert result.is_err
        assert result.danger_err == TicketError.EvidenceCmdFailed


class TestAddCmdEvidenceLoadAndWriteFailures:
    """`add_cmd_evidence`'s error propagation paths that don't depend on
    the kind gate or the command itself: ticket-not-found on load, and a
    downstream write failure after a successful command run.

    frob:ticket T-1152
    """

    def test_ticket_not_found_propagates_load_error(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_evidence.py::add_cmd_evidence
        # frob:ticket T-1152
        from frob.tickets import add_cmd_evidence

        result = add_cmd_evidence(tmp_path, "T-9999", "printf ok")
        assert result.is_err
        assert result.danger_err == TicketError.NotFound

    def test_write_failure_propagates(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/tickets/_evidence.py::add_cmd_evidence
        # frob:ticket T-1152
        import frob.tickets as tickets_mod
        from frob.tickets import add_cmd_evidence

        _seed_ticket(tmp_path, kind=TicketKind.DOCS)

        def _fail_write(
            *_args: object, **_kwargs: object
        ) -> Result[object, TicketError]:
            return Err(TicketError.WriteFailed)

        monkeypatch.setattr(tickets_mod, "write_ticket", _fail_write)
        result = add_cmd_evidence(tmp_path, "T-0001", "printf ok")
        assert result.is_err
        assert result.danger_err == TicketError.WriteFailed
