"""Finding-disposal and resolved-ticket-close tests for `frob.app.ticket_runner._rapid_sweep`
(T-3595 split of the former tests/unit/test_rapid_sweep.py)."""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.app.ticket_runner._rapid_sweep import (
    _close_resolved_sweep_tickets,
    _file_regression_ticket,
    _parse_sweep_ticket_identities,
    _read_baseline_commit,
    _write_baseline,
    run_deferred_post_land_sweep,
)
from tests.conftest import (
    _git,
    _git_commit,
    _init_git_repo,
    _seed_repo,
    _seed_ticket,
)


# frob:ticket T-2208
class TestAutoDisposeFiledFindings:
    """T-2208: filing a regression ticket for a quarantined finding must
    dispose that finding, with `--file-ticket` semantics, in the same
    operation -- never leave a human to hand-restate the fact via `frob
    verify dispose --file-ticket` after every red batch."""

    # frob:ticket T-2208
    def test_disposes_findings_the_ticket_covers(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_dispose.py::TestAutoDisposeFiledFindings.test_disposes_findings_the_ticket_covers  # noqa: E501
        from frob.verify import record_intent
        from frob.verify._quarantine import is_quarantined, load_quarantine

        record_intent(
            tmp_path,
            commit_sha="commitA",
            ticket_id="T-9000",
            touched_symbols=("a.py::fn",),
            profile="rapid",
        )
        filed = _file_regression_ticket(
            tmp_path,
            "T-9000",
            "deadbeef",
            frozenset({("RULE1", "a.py")}),
        )
        assert filed is not None

        # This is the ticket's own MUST-fail-against-main assertion:
        # before T-2208, filing a regression ticket never disposed the
        # quarantine record it was filed for, so quarantine stayed
        # raised until a human ran `frob verify dispose` by hand.
        assert is_quarantined(tmp_path).danger_ok is False
        record = load_quarantine(tmp_path)
        assert record.is_ok
        assert record.danger_ok is not None
        (finding,) = record.danger_ok.findings
        assert finding.disposition == "filed"
        assert finding.disposition_ref == filed

    # frob:ticket T-2208
    # frob:ticket T-2604
    def test_leaves_quarantine_raised_when_other_findings_remain_undisposed(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_dispose.py::TestAutoDisposeFiledFindings.test_leaves_quarantine_raised_when_other_findings_remain_undisposed  # noqa: E501
        """T-2604 rewrote this test's original setup: it used to lean on
        a finding attributed to an already-open ticket to construct "one
        finding in the raised record this call never touches". Exactly
        the bug T-2604 fixes means such a finding is now dropped from
        the quarantine raise entirely, before this scenario can even
        arise through `_file_regression_ticket`'s own attribution path.
        Exercising `_auto_dispose_filed_findings` directly against a
        record raised independently (simulating one left over from an
        earlier, unrelated red batch this call's `unfiled_pairs` never
        names) keeps this test's real subject -- `clear_quarantine`'s
        atomic all-or-nothing contract -- intact and independent of how
        the record came to have two findings in it."""
        from frob.app.ticket_runner._rapid_sweep import _auto_dispose_filed_findings
        from frob.verify._quarantine import (
            QuarantinedFinding,
            is_quarantined,
            load_quarantine,
            raise_quarantine,
        )

        raised = raise_quarantine(
            tmp_path,
            batch_commit_shas=("commitA",),
            findings=(
                QuarantinedFinding(rule_id="RULE1", file="a.py", line=None),
                QuarantinedFinding(rule_id="RULE2", file="b.py", line=None),
            ),
        )
        assert raised.is_ok

        # Only RULE2/b.py is covered by this filing -- RULE1/a.py is
        # left alone, exactly `_auto_dispose_filed_findings`'s own
        # documented contract for "a different, already-open ticket
        # this call never touched".
        _auto_dispose_filed_findings(tmp_path, [("RULE2", "b.py")], "T-9001")

        assert is_quarantined(tmp_path).danger_ok is True
        record = load_quarantine(tmp_path)
        assert record.danger_ok is not None
        dispositions = {
            (f.rule_id, f.file): f.disposition for f in record.danger_ok.findings
        }
        assert dispositions == {("RULE1", "a.py"): "", ("RULE2", "b.py"): ""}

    # frob:ticket T-2208
    # frob:waive DUP001 reason="100% similar to \
    # TestRaiseQuarantineForRedBatch.test_empty_queue_logs_and_skips_the_raise by \
    # construction -- both exercise the SAME no-queue/no-raise precondition, one \
    # asserting the raise never fires, the other (this one) asserting the NEW T-2208 \
    # auto-dispose call downstream of it is a no-op when there was nothing to dispose \
    # in the first place; a shared helper would hide which capability each test is \
    # pinning"
    def test_no_quarantine_raised_is_a_silent_no_op(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_dispose.py::TestAutoDisposeFiledFindings.test_no_quarantine_raised_is_a_silent_no_op  # noqa: E501
        from frob.verify._quarantine import is_quarantined

        # No verify queue -- `_raise_quarantine_for_red_batch` never
        # raises anything, so there is nothing to auto-dispose.
        filed = _file_regression_ticket(
            tmp_path, "T-9000", "deadbeef", frozenset({("RULE1", "a.py")})
        )
        assert filed is not None
        assert is_quarantined(tmp_path).danger_ok is False

    # frob:ticket T-2208
    # frob:waive DUP001 reason="95% similar to \
    # TestRaiseQuarantineForRedBatch.test_raise_failure_is_logged_not_raised by \
    # construction -- same fail-soft shape (a quarantine-module write failing must be \
    # logged and swallowed, never raised), applied to the OTHER quarantine write this \
    # ticket adds (clear_quarantine, not raise_quarantine); collapsing the two would \
    # obscure which call each test pins down"
    def test_clear_failure_is_logged_not_raised(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_dispose.py::TestAutoDisposeFiledFindings.test_clear_failure_is_logged_not_raised  # noqa: E501
        from typani.result import Err

        from frob.verify import _quarantine as quarantine_mod
        from frob.verify import record_intent
        from frob.verify._quarantine import QuarantineError

        record_intent(
            tmp_path,
            commit_sha="commitA",
            ticket_id="T-9000",
            touched_symbols=("a.py::fn",),
            profile="rapid",
        )
        monkeypatch.setattr(
            quarantine_mod,
            "clear_quarantine",
            lambda root, **kw: Err(QuarantineError.NotQuarantined),
        )
        # Must not raise or otherwise fail the caller -- the filed
        # ticket is still the durable record even if the auto-dispose
        # write itself fails for some reason.
        filed = _file_regression_ticket(
            tmp_path, "T-9000", "deadbeef", frozenset({("RULE1", "a.py")})
        )
        assert filed is not None


# frob:ticket T-1983
class TestCloseResolvedSweepTickets:
    """T-1983: a sweep-filed regression ticket whose findings stop
    reproducing must be auto-DROPPED (not closed, not left forever) the
    next time the sweep can prove it, reusing the rolling-baseline diff
    the sweep already computes for the opposite direction."""

    def test_non_sweep_ticket_returns_none(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_dispose.py::TestCloseResolvedSweepTickets.test_non_sweep_ticket_returns_none  # noqa: E501
        ticket_id = _seed_ticket(tmp_path)
        from frob.tickets import load_queue

        queue = load_queue(tmp_path)
        assert queue.is_ok
        ticket = queue.danger_ok.tickets[ticket_id]
        assert _parse_sweep_ticket_identities(ticket) is None

    def test_parses_a_sweep_titled_ticket_identity_set(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_dispose.py::TestCloseResolvedSweepTickets.test_parses_a_sweep_titled_ticket_identity_set  # noqa: E501
        findings = frozenset({("RULE1", "a.py"), ("RULE2", "b.py")})
        filed = _file_regression_ticket(tmp_path, "T-9000", "deadbeef", findings)
        assert filed is not None
        from frob.tickets import load_queue

        queue = load_queue(tmp_path)
        assert queue.is_ok
        ticket = queue.danger_ok.tickets[filed]
        assert _parse_sweep_ticket_identities(ticket) == findings

    def test_drops_a_fully_resolved_sweep_ticket(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_dispose.py::TestCloseResolvedSweepTickets.test_drops_a_fully_resolved_sweep_ticket  # noqa: E501
        findings = frozenset({("RULE1", "a.py")})
        filed = _file_regression_ticket(tmp_path, "T-9000", "deadbeef", findings)
        assert filed is not None

        dropped = _close_resolved_sweep_tickets(tmp_path, "T-9001", findings)
        assert dropped == (filed,)

        from frob.tickets import TicketState, load_queue

        queue = load_queue(tmp_path)
        assert queue.is_ok
        assert queue.danger_ok.tickets[filed].state == TicketState.DROPPED

    def test_leaves_a_partially_resolved_ticket_untouched(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_dispose.py::TestCloseResolvedSweepTickets.test_leaves_a_partially_resolved_ticket_untouched  # noqa: E501
        findings = frozenset({("RULE1", "a.py"), ("RULE2", "b.py")})
        filed = _file_regression_ticket(tmp_path, "T-9000", "deadbeef", findings)
        assert filed is not None

        # Only RULE1/a.py vanished -- RULE2/b.py still reproduces, so the
        # ticket as a whole must not be dropped.
        dropped = _close_resolved_sweep_tickets(
            tmp_path, "T-9001", frozenset({("RULE1", "a.py")})
        )
        assert dropped == ()

        from frob.tickets import TicketState, load_queue

        queue = load_queue(tmp_path)
        assert queue.is_ok
        assert queue.danger_ok.tickets[filed].state == TicketState.QUEUED

    def test_leaves_a_still_reproducing_ticket_untouched(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_dispose.py::TestCloseResolvedSweepTickets.test_leaves_a_still_reproducing_ticket_untouched  # noqa: E501
        findings = frozenset({("RULE1", "a.py")})
        filed = _file_regression_ticket(tmp_path, "T-9000", "deadbeef", findings)
        assert filed is not None

        dropped = _close_resolved_sweep_tickets(tmp_path, "T-9001", frozenset())
        assert dropped == ()

        from frob.tickets import TicketState, load_queue

        queue = load_queue(tmp_path)
        assert queue.is_ok
        assert queue.danger_ok.tickets[filed].state == TicketState.QUEUED

    # frob:ticket T-2521
    def test_absolute_recorded_identity_matches_relative_vanished_entry(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_dispose.py::TestCloseResolvedSweepTickets.test_absolute_recorded_identity_matches_relative_vanished_entry  # noqa: E501
        """T-2521 required control #3: a ticket whose body recorded an
        finding with an ABSOLUTE path (the real, historical shape T-2036
        fixed, T-2314's own 116-waiver incident of the identical class)
        must still be recognized as resolved when the fresh measurement's
        `vanished` set names the SAME file repo-relative -- end-to-end
        through the real drop path (`_close_resolved_sweep_tickets` ->
        `_maybe_drop_resolved_ticket`), not just the isolated `_normalize_
        identities` unit tests elsewhere in this file."""
        findings = frozenset({("RULE1", str(tmp_path / "a.py"))})
        filed = _file_regression_ticket(tmp_path, "T-9000", "deadbeef", findings)
        assert filed is not None

        # The fresh measurement's own vanished set, repo-relative (the
        # shape a real `frob check --json` reports).
        dropped = _close_resolved_sweep_tickets(
            tmp_path, "T-9001", frozenset({("RULE1", "a.py")})
        )
        assert dropped == (filed,)

        from frob.tickets import TicketState, load_queue

        queue = load_queue(tmp_path)
        assert queue.is_ok
        assert queue.danger_ok.tickets[filed].state == TicketState.DROPPED

    def test_in_progress_sweep_ticket_is_never_touched(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_dispose.py::TestCloseResolvedSweepTickets.test_in_progress_sweep_ticket_is_never_touched  # noqa: E501
        from frob.tickets import TicketState, transition

        findings = frozenset({("RULE1", "a.py")})
        filed = _file_regression_ticket(tmp_path, "T-9000", "deadbeef", findings)
        assert filed is not None
        planned = transition(tmp_path, filed, TicketState.PLANNED)
        assert planned.is_ok
        started = transition(tmp_path, filed, TicketState.IN_PROGRESS)
        assert started.is_ok

        dropped = _close_resolved_sweep_tickets(tmp_path, "T-9001", findings)
        assert dropped == ()

    # frob:ticket T-2030
    def test_a_done_ticket_body_is_byte_for_byte_untouched(
        self, tmp_path: Path
    ) -> None:
        """T-2030: a `done` ticket's own Done report was found silently
        REPLACED in an incident this ticket investigates -- verify the
        QUEUED/PLANNED state filter (`_close_resolved_sweep_tickets`'s
        own scan, `ticket.state not in (QUEUED, PLANNED)`) genuinely
        protects a terminal ticket's file content, byte for byte, rather
        than trusting the guard exists by reading it."""
        # frob:tests tests/unit/rapid_sweep_suite/test_dispose.py::TestCloseResolvedSweepTickets.test_a_done_ticket_body_is_byte_for_byte_untouched  # noqa: E501
        from frob.tickets import TicketState, drop_ticket, transition

        findings = frozenset({("RULE1", "a.py")})
        filed = _file_regression_ticket(tmp_path, "T-9000", "deadbeef", findings)
        assert filed is not None
        planned = transition(tmp_path, filed, TicketState.PLANNED)
        assert planned.is_ok
        started = transition(tmp_path, filed, TicketState.IN_PROGRESS)
        assert started.is_ok
        # DROPPED is the cheap way to reach a terminal state here (same
        # trick `_seed_ticket`'s own docstring above uses) -- terminal is
        # the property under test, not which terminal state.
        dropped_result = drop_ticket(tmp_path, filed, "done for this test")
        assert dropped_result.is_ok

        ticket_path = tmp_path / "tickets" / filed / "ticket.md"
        before = ticket_path.read_bytes()

        result = _close_resolved_sweep_tickets(tmp_path, "T-9001", findings)
        assert result == ()

        after = ticket_path.read_bytes()
        assert after == before

    # frob:ticket T-2034
    def test_commit_failure_restores_root_to_clean_not_left_dirty(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2034's own repro: `_maybe_drop_resolved_ticket`'s
        `drop_ticket()` write must never survive an exhausted commit retry
        uncommitted in `root` -- that is exactly the DirtyMain-blocking
        defect this ticket exists to close. Before the fix this asserted
        root DIRTY; after the fix root must be CLEAN and the ticket
        restored to QUEUED (droppable again on the next sweep, not
        silently lost)."""
        # frob:tests tests/unit/rapid_sweep_suite/test_dispose.py::TestCloseResolvedSweepTickets.test_commit_failure_restores_root_to_clean_not_left_dirty  # noqa: E501
        from typani.result import Err

        import frob.app.ticket_runner._rapid_sweep as rapid_sweep_mod
        from frob.tickets._leases import LeaseError

        repo = _seed_repo(tmp_path)
        findings = frozenset({("RULE1", "a.py")})
        filed = _file_regression_ticket(repo, "T-9000", "deadbeef", findings)
        assert filed is not None
        assert not _git(repo, "status", "--porcelain", "--", "tickets").strip()

        monkeypatch.setattr(
            "frob.tickets._leases.commit_ticket_ledger_change",
            lambda root, ticket_id, message: Err(LeaseError.LandInProgress),
        )
        monkeypatch.setattr(rapid_sweep_mod.time, "sleep", lambda _s: None)

        dropped = rapid_sweep_mod._close_resolved_sweep_tickets(
            repo, "T-9001", findings
        )
        assert dropped == ()  # commit failed -- not reported as dropped

        # THE FIX: root must be clean, never left with an uncommitted
        # drop write DirtyMain-blocking every concurrent land.
        assert not _git(repo, "status", "--porcelain", "--", "tickets").strip()

        from frob.tickets import TicketState, load_queue

        queue = load_queue(repo)
        assert queue.is_ok
        assert queue.danger_ok.tickets[filed].state == TicketState.QUEUED

    # frob:ticket T-2034
    def test_retry_after_commit_failure_does_not_duplicate_the_reason(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2034: T-2000/T-2008/T-2022 each carried the SAME
        auto-drop reason line TWICE because the never-discarded write let
        the NEXT sweep pass see the ticket as still QUEUED and drop it
        again. Restoring on discard (this test's first sweep) must leave
        the ticket genuinely droppable, and the SECOND, successful sweep
        must append the reason exactly once."""
        # frob:tests tests/unit/rapid_sweep_suite/test_dispose.py::TestCloseResolvedSweepTickets.test_retry_after_commit_failure_does_not_duplicate_the_reason  # noqa: E501
        from typani.result import Err

        import frob.app.ticket_runner._rapid_sweep as rapid_sweep_mod
        from frob.tickets._leases import LeaseError

        repo = _seed_repo(tmp_path)
        findings = frozenset({("RULE1", "a.py")})
        filed = _file_regression_ticket(repo, "T-9000", "deadbeef", findings)
        assert filed is not None

        monkeypatch.setattr(
            "frob.tickets._leases.commit_ticket_ledger_change",
            lambda root, ticket_id, message: Err(LeaseError.LandInProgress),
        )
        monkeypatch.setattr(rapid_sweep_mod.time, "sleep", lambda _s: None)
        monkeypatch.setattr(rapid_sweep_mod, "_TICKET_DROP_COMMIT_MAX_ATTEMPTS", 1)
        rapid_sweep_mod._close_resolved_sweep_tickets(repo, "T-9001", findings)
        monkeypatch.undo()

        # Second sweep, this time the commit succeeds for real.
        dropped = rapid_sweep_mod._close_resolved_sweep_tickets(
            repo, "T-9002", findings
        )
        assert dropped == (filed,)

        from frob.tickets import load_queue

        queue = load_queue(repo)
        assert queue.is_ok
        reason_count = queue.danger_ok.tickets[filed].body.count("auto-dropped by")
        assert reason_count == 1


# frob:ticket T-2038
class TestNormalizeIdentityFile:
    """T-2038 (DRIFT002 fix): `_normalize_identity_file`'s own `frob:tests`
    directives were added ahead of these tests -- filling the gap."""

    def test_absolute_under_root_becomes_relative(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_dispose.py::TestNormalizeIdentityFile.test_absolute_under_root_becomes_relative  # noqa: E501
        from frob.app.ticket_runner._rapid_sweep import _normalize_identity_file

        file = str(tmp_path / "a" / "b.py")
        assert _normalize_identity_file(tmp_path, file) == "a/b.py"

    def test_already_relative_is_unchanged(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_dispose.py::TestNormalizeIdentityFile.test_already_relative_is_unchanged  # noqa: E501
        from frob.app.ticket_runner._rapid_sweep import _normalize_identity_file

        assert _normalize_identity_file(tmp_path, "a/b.py") == "a/b.py"

    def test_absolute_outside_root_falls_back_unchanged(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_dispose.py::TestNormalizeIdentityFile.test_absolute_outside_root_falls_back_unchanged  # noqa: E501
        from frob.app.ticket_runner._rapid_sweep import _normalize_identity_file

        other = tmp_path.parent / "elsewhere" / "c.py"
        assert _normalize_identity_file(tmp_path, str(other)) == other.as_posix()


# frob:ticket T-2313
class TestNormalizeIdentities:
    """T-2313: `_normalize_identities` must drop a genuinely
    identity-less (rule, file) pair (both fields empty) rather than
    silently carrying it through into a baseline diff or a filed ticket
    body -- observed verbatim in T-2297 as a blank ``"-   "`` line."""

    def test_drops_genuinely_empty_identity_pair(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_dispose.py::TestNormalizeIdentities.test_drops_genuinely_empty_identity_pair  # noqa: E501
        import logging

        from frob.app.ticket_runner._rapid_sweep import _normalize_identities

        with caplog.at_level(logging.WARNING):
            result = _normalize_identities(
                tmp_path, frozenset({("", ""), ("E501", "a.py")})
            )
        assert result == frozenset({("E501", "a.py")})
        assert "T-2313" in caplog.text
        assert "1 genuinely identity-less" in caplog.text

    def test_leaves_well_formed_pairs_untouched(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_dispose.py::TestNormalizeIdentities.test_leaves_well_formed_pairs_untouched  # noqa: E501
        from frob.app.ticket_runner._rapid_sweep import _normalize_identities

        identities = frozenset({("E501", "a.py"), ("F841", "b.py")})
        assert _normalize_identities(tmp_path, identities) == identities

    def test_partial_identity_one_field_empty_is_kept(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_dispose.py::TestNormalizeIdentities.test_partial_identity_one_field_empty_is_kept  # noqa: E501
        # A pair with only ONE empty field is a real, if partial,
        # identity (e.g. a rule with no associated file) -- not the
        # T-2313 both-empty shape -- and must be left alone, not dropped.
        from frob.app.ticket_runner._rapid_sweep import _normalize_identities

        # _normalize_identity_file("") normalizes to "." (Path("").as_posix()),
        # pre-existing, unrelated behavior -- this test only asserts the
        # pair was NOT dropped as identity-less, not the exact file string.
        result = _normalize_identities(tmp_path, frozenset({("E501", "")}))
        assert len(result) == 1
        assert next(iter(result))[0] == "E501"


# frob:ticket T-2036
class TestAbsoluteVsRelativePathIdentityMismatch:
    """T-2036's own repro: T-2022 was auto-dropped while its
    findings were still live because the identity it was FILED with
    (absolute path, from an earlier sweep's measurement) never matched a
    LATER sweep's fresh measurement of the SAME still-broken file
    reported in repo-relative form -- a plain string-tuple diff cannot
    see these as the same identity. Watch this fail first: before the
    fix, the still-broken ticket ends up DROPPED."""

    def test_format_drift_between_sweeps_does_not_falsely_resolve_a_live_ticket(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_dispose.py::TestAbsoluteVsRelativePathIdentityMismatch.test_format_drift_between_sweeps_does_not_falsely_resolve_a_live_ticket  # noqa: E501
        _write_baseline(tmp_path, frozenset(), "c0")
        abs_path = str(tmp_path / "a.py")

        # Land 1: the tool reports an ABSOLUTE path for the broken file.
        # A ticket gets filed naming that identity.
        monkeypatch.setattr(
            "frob.app.ticket_runner._land_cmd._unscoped_error_findings",
            lambda *a, **k: frozenset({("RULE1", abs_path)}),
        )
        first = run_deferred_post_land_sweep(tmp_path, "T-1001", "c1")
        assert first.is_ok
        filed = first.danger_ok
        assert filed is not None

        # Land 2: the SAME file, SAME rule, genuinely STILL broken -- but
        # this time the tool reports it REPO-RELATIVE (format drift
        # between runs, T-2022's measured shape). The ticket must NOT
        # read as resolved just because the raw strings differ.
        monkeypatch.setattr(
            "frob.app.ticket_runner._land_cmd._unscoped_error_findings",
            lambda *a, **k: frozenset({("RULE1", "a.py")}),
        )
        second = run_deferred_post_land_sweep(tmp_path, "T-1002", "c2")
        assert second.is_ok

        from frob.tickets import TicketState, load_queue

        queue = load_queue(tmp_path)
        assert queue.is_ok
        # THE FIX: still QUEUED, never falsely auto-dropped.
        assert queue.danger_ok.tickets[filed].state == TicketState.QUEUED


# frob:ticket T-1983
class TestDeferredSweepClosesResolvedRegressions:
    """End-to-end: `run_deferred_post_land_sweep` itself closes the loop
    on a prior sweep ticket whose findings vanish, and leaves one whose
    findings still reproduce alone -- the acceptance shape T-1983 itself
    demands (first assert must FAIL before the fix)."""

    def test_resolved_finding_is_dropped_by_the_next_sweep(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_dispose.py::TestDeferredSweepClosesResolvedRegressions.test_resolved_finding_is_dropped_by_the_next_sweep  # noqa: E501
        _write_baseline(tmp_path, frozenset(), "c0")

        # Land 1: RULE1/a.py appears -- files a real regression ticket.
        monkeypatch.setattr(
            "frob.app.ticket_runner._land_cmd._unscoped_error_findings",
            lambda *a, **k: frozenset({("RULE1", "a.py")}),
        )
        first = run_deferred_post_land_sweep(tmp_path, "T-1001", "c1")
        assert first.is_ok
        filed = first.danger_ok
        assert filed is not None

        # Land 2: RULE1/a.py is fixed -- the fresh measurement no longer
        # finds it, so the sweep must drop the ticket it filed for it.
        monkeypatch.setattr(
            "frob.app.ticket_runner._land_cmd._unscoped_error_findings",
            lambda *a, **k: frozenset(),
        )
        second = run_deferred_post_land_sweep(tmp_path, "T-1002", "c2")
        assert second.is_ok

        from frob.tickets import TicketState, load_queue

        queue = load_queue(tmp_path)
        assert queue.is_ok
        assert queue.danger_ok.tickets[filed].state == TicketState.DROPPED

    def test_still_reproducing_finding_is_left_untouched(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_dispose.py::TestDeferredSweepClosesResolvedRegressions.test_still_reproducing_finding_is_left_untouched  # noqa: E501
        _write_baseline(tmp_path, frozenset(), "c0")

        monkeypatch.setattr(
            "frob.app.ticket_runner._land_cmd._unscoped_error_findings",
            lambda *a, **k: frozenset({("RULE1", "a.py")}),
        )
        first = run_deferred_post_land_sweep(tmp_path, "T-1001", "c1")
        assert first.is_ok
        filed = first.danger_ok
        assert filed is not None

        # Land 2: RULE1/a.py is STILL present -- must not be dropped.
        second = run_deferred_post_land_sweep(tmp_path, "T-1002", "c2")
        assert second.is_ok

        from frob.tickets import TicketState, load_queue

        queue = load_queue(tmp_path)
        assert queue.is_ok
        assert queue.danger_ok.tickets[filed].state == TicketState.QUEUED


class TestDeferredSweepMultiLandAttribution:
    """T-2009, end-to-end: the T-1998 measured shape -- two real lands
    happen between the previous baseline and the tree THIS sweep
    actually measures (the sweep is detached, off the land critical
    path, so other agents' lands routinely land in the window before it
    runs). The regression must be attributed to BOTH lands, never
    silently pinned on whichever one happened to spawn this sweep
    process."""

    def test_two_lands_in_the_window_are_both_named_not_just_the_spawning_one(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_dispose.py::TestDeferredSweepMultiLandAttribution.test_two_lands_in_the_window_are_both_named_not_just_the_spawning_one  # noqa: E501
        _init_git_repo(tmp_path)
        c0 = _git_commit(tmp_path, "chore: init")
        _write_baseline(tmp_path, frozenset(), c0)

        # Land T-1977 lands (this is the sweep that gets SPAWNED)...
        _git_commit(tmp_path, "fix(tickets): land T-1977 first fix")
        # ...but before its detached sweep child actually gets to run,
        # T-1995 ALSO lands (this is exactly the T-1998 incident: the
        # sweep is off the critical path on purpose, T-1684, so this is
        # normal, not a race bug). The real HEAD by the time the check
        # runs is past BOTH lands.
        real_head = _git_commit(tmp_path, "feat(tickets): land T-1995 second fix")

        # The new finding actually lives in a file T-1995 touched -- the
        # exact T-1998 shape (misattributed to T-1977, whose files were
        # never involved).
        monkeypatch.setattr(
            "frob.app.ticket_runner._land_cmd._unscoped_error_findings",
            lambda *a, **k: frozenset({("F401", "t1995_file.py")}),
        )
        # `_resolve_actual_head` reads the real git HEAD of tmp_path
        # (real_head) -- the sweep was merely SPAWNED naming T-1977 and
        # commit_sha=stale-spawn-sha (a stale value by the time it
        # actually runs).
        result = run_deferred_post_land_sweep(tmp_path, "T-1977", "stale-spawn-sha")
        assert result.is_ok
        filed = result.danger_ok
        assert filed is not None

        from frob.tickets import load_queue

        queue = load_queue(tmp_path)
        assert queue.is_ok
        ticket = queue.danger_ok.tickets[filed]
        title = ticket.title
        body = ticket.body
        # Before T-2009's fix: title/body named ONLY "T-1977" -- the land
        # that spawned the sweep, not the land whose files actually went
        # red. Both must be named now.
        assert "T-1977" in title
        assert "T-1995" in title
        assert "T-1995" in body
        # The baseline's own recorded commit must be the REAL head this
        # sweep measured, not the stale spawn-time commit_sha -- this is
        # what lets the NEXT sweep compute an honest window in turn.
        assert _read_baseline_commit(tmp_path) == real_head
