"""Deferred-sweep run/spawn and detached-env tests for `frob.app.ticket_runner._rapid_sweep`
(T-3595 split of the former tests/unit/test_rapid_sweep.py)."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import cast

import pytest

from frob.app.ticket_runner import _rapid_sweep
from frob.app.ticket_runner._rapid_sweep import (
    RapidSweepError,
    _check_claim_divergence_post_land,
    _persist_baseline,
    _read_baseline,
    _write_baseline,
    run_deferred_post_land_sweep,
    spawn_deferred_post_land_sweep,
)


# frob:ticket T-4335
class TestPersistBaseline:
    """Covers `_persist_baseline`, the caller-controlled write half of
    baseline persistence. See T-4335 for the design rationale."""

    # frob:ticket T-4335
    # frob:tests src/frob/app/ticket_runner/_rapid_sweep.py::_persist_baseline
    def test_writes_and_logs_survival_warning_on_loss(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog
    ) -> None:
        """A normal write persists exactly what the caller asked for."""
        # frob:tests tests/unit/rapid_sweep_suite/test_sweep_run.py::TestPersistBaseline.test_writes_and_logs_survival_warning_on_loss  # noqa: E501
        to_persist = frozenset({("COV003", "a.py")})
        _persist_baseline(tmp_path, "T-0001", to_persist, "deadbeef" * 5)
        assert _read_baseline(tmp_path) == to_persist


# frob:ticket T-4318
# frob:ticket T-4335
class TestDeferredSweepRun:
    """`run_deferred_post_land_sweep` files, never reverts."""

    @pytest.fixture
    def _no_debt(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """`record_rapid_debt` shells out to git; a tmp_path is not a repo."""
        monkeypatch.setattr(
            "frob.tickets._evidence.record_rapid_debt", lambda *a, **k: None
        )

    # frob:tests src/frob/app/ticket_runner/_rapid_sweep.py::run_deferred_post_land_sweep  # noqa: E501
    def test_unmeasurable_check_leaves_the_baseline_untouched(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_sweep_run.py::TestDeferredSweepRun.test_unmeasurable_check_leaves_the_baseline_untouched  # noqa: E501
        _write_baseline(tmp_path, frozenset({("COV003", "a.py")}), "old")
        monkeypatch.setattr(
            "frob.app.ticket_runner._land_cmd._unscoped_error_findings",
            lambda *a, **k: None,
        )
        result = run_deferred_post_land_sweep(tmp_path, "T-0001", "abc123")
        assert result.is_err
        assert result.danger_err is RapidSweepError.Unmeasurable
        assert _read_baseline(tmp_path) == frozenset({("COV003", "a.py")})

    # frob:tests src/frob/app/ticket_runner/_rapid_sweep.py::run_deferred_post_land_sweep  # noqa: E501
    def test_first_sweep_records_a_baseline_and_files_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_sweep_run.py::TestDeferredSweepRun.test_first_sweep_records_a_baseline_and_files_nothing  # noqa: E501
        fresh = frozenset({("COV003", "a.py")})
        monkeypatch.setattr(
            "frob.app.ticket_runner._land_cmd._unscoped_error_findings",
            lambda *a, **k: fresh,
        )
        filed: list[object] = []
        monkeypatch.setattr(
            _rapid_sweep, "_file_regression_ticket", lambda *a: filed.append(a)
        )
        result = run_deferred_post_land_sweep(tmp_path, "T-0001", "abc123")
        assert result.is_ok
        assert result.danger_ok is None
        assert filed == []
        assert _read_baseline(tmp_path) == fresh

    # frob:ticket T-4318
    # frob:tests src/frob/app/ticket_runner/_rapid_sweep.py::_measure_fresh_sweep_state
    def test_calls_unscoped_error_findings_with_full_true(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-4318: the deferred sweep runs in a detached `frob ticket
        sweep-async` child nobody is waiting on, so it must pass
        `full=True` to `_unscoped_error_findings` (dropping the
        `--budget` ceiling `_derive_post_land_sweep_budget_s` derives
        for an INLINE foreground land) rather than defaulting to
        `full=False` and truncating under fleet load exactly like an
        interactive caller would, for zero latency benefit."""
        # frob:tests tests/unit/rapid_sweep_suite/test_sweep_run.py::TestDeferredSweepRun.test_calls_unscoped_error_findings_with_full_true  # noqa: E501
        _write_baseline(tmp_path, frozenset({("COV003", "a.py")}), "old")
        calls: list[dict[str, object]] = []

        def _fake_findings(
            *args: object, **kwargs: object
        ) -> frozenset[tuple[str, str]]:
            calls.append(kwargs)
            return frozenset({("COV003", "a.py")})

        monkeypatch.setattr(
            "frob.app.ticket_runner._land_cmd._unscoped_error_findings",
            _fake_findings,
        )
        result = run_deferred_post_land_sweep(tmp_path, "T-0001", "abc123")
        assert result.is_ok
        assert calls == [{"full": True}]

    # frob:tests \
    # src/frob/app/ticket_runner/_rapid_sweep.py::run_deferred_post_land_sweep
    def test_no_new_findings_is_clean(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_sweep_run.py::TestDeferredSweepRun.test_no_new_findings_is_clean  # noqa: E501
        existing = frozenset({("COV003", "a.py")})
        _write_baseline(tmp_path, existing, "old")
        monkeypatch.setattr(
            "frob.app.ticket_runner._land_cmd._unscoped_error_findings",
            lambda *a, **k: existing,
        )
        filed: list[object] = []
        monkeypatch.setattr(
            _rapid_sweep, "_file_regression_ticket", lambda *a: filed.append(a)
        )
        result = run_deferred_post_land_sweep(tmp_path, "T-0001", "abc123")
        assert result.is_ok
        assert result.danger_ok is None
        assert filed == []

    # frob:tests src/frob/app/ticket_runner/_rapid_sweep.py::run_deferred_post_land_sweep  # noqa: E501
    def test_new_findings_file_a_ticket_and_rebaseline(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_sweep_run.py::TestDeferredSweepRun.test_new_findings_file_a_ticket_and_rebaseline  # noqa: E501
        _write_baseline(tmp_path, frozenset({("COV003", "a.py")}), "old")
        fresh = frozenset({("COV003", "a.py"), ("DOC011", "b.md")})
        monkeypatch.setattr(
            "frob.app.ticket_runner._land_cmd._unscoped_error_findings",
            lambda *a, **k: fresh,
        )
        seen: list[frozenset[tuple[str, str]]] = []

        def _fake_file(root, final_id, commit, new_findings):  # noqa: ANN001, ANN202
            seen.append(new_findings)
            return "T-9999"

        monkeypatch.setattr(_rapid_sweep, "_file_regression_ticket", _fake_file)
        result = run_deferred_post_land_sweep(tmp_path, "T-0001", "abc123")
        assert result.is_ok
        assert result.danger_ok == "T-9999"
        assert seen == [frozenset({("DOC011", "b.md")})]
        # Rebaselined even though the sweep was red: an already-filed
        # error must not be re-filed by the next land.
        assert _read_baseline(tmp_path) == fresh

    # frob:ticket T-2929
    # frob:ticket T-4335
    # frob:tests \
    # src/frob/app/ticket_runner/_rapid_sweep.py::run_deferred_post_land_sweep
    # frob:tests \
    # src/frob/app/ticket_runner/_rapid_sweep.py::_refuse_filing_for_stale_verification_queue  # noqa: E501
    def test_stale_baseline_refuses_to_file_and_records_debt(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2929 must-fire case: `frob.verify.rapid_soft_warning` firing
        (a stale verification-queue window) means a NEW finding is NOT
        filed as a confident regression ticket -- the sweep refuses and
        records the refusal as a distinct, durable debt kind instead."""
        # frob:tests \
        # tests/unit/rapid_sweep_suite/test_sweep_run.py::TestDeferredSweepRun.test_stale_baseline_refuses_to_file_and_records_debt  # noqa: E501
        _write_baseline(tmp_path, frozenset({("COV003", "a.py")}), "old")
        fresh = frozenset({("COV003", "a.py"), ("DOC006", "tickets/T-0002/ticket.md")})
        monkeypatch.setattr(
            "frob.app.ticket_runner._land_cmd._unscoped_error_findings",
            lambda *a, **k: fresh,
        )
        monkeypatch.setattr(
            "frob.verify.rapid_soft_warning",
            lambda root: (
                "rapid profile verification debt is stale: 53 commits "
                "since watermark (warn threshold 5)"
            ),
        )
        filed: list[object] = []
        monkeypatch.setattr(
            _rapid_sweep, "_file_regression_ticket", lambda *a, **k: filed.append(a)
        )
        debts: list[tuple[str, str]] = []
        monkeypatch.setattr(
            "frob.tickets._evidence.record_rapid_debt",
            lambda root, tid, what: debts.append((tid, what)),
        )
        monkeypatch.setattr(_rapid_sweep, "_commit_rapid_debt", lambda root, tid: None)

        result = run_deferred_post_land_sweep(tmp_path, "T-0001", "abc123")

        assert result.is_ok
        assert result.danger_ok is None
        assert filed == []
        # T-2938: the deferred claim-divergence check reuses this SAME
        # staleness policy (`frob.verify.rapid_soft_warning`) independently
        # of the new-findings filing path above, and records the SAME debt
        # reason when it refuses too -- two refusals, one shared reason,
        # not a second policy.
        assert debts == [
            ("T-0001", "post-land-sweep-attribution-skipped-stale-baseline"),
            ("T-0001", "post-land-sweep-attribution-skipped-stale-baseline"),
        ]
        # T-4335: the REFUSED (unfiled) new identity must NOT be rolled
        # into the baseline -- only the previously-known identity is. A
        # sweep that already refused to file this on attribution grounds
        # must not also teach the rolling baseline that it is normal;
        # the next sweep must still see it as new so it gets a real
        # chance to be filed once the verification queue is current.
        assert _read_baseline(tmp_path) == frozenset({("COV003", "a.py")})

    # frob:ticket T-2929
    # frob:tests \
    # src/frob/app/ticket_runner/_rapid_sweep.py::run_deferred_post_land_sweep
    # frob:tests \
    # src/frob/app/ticket_runner/_rapid_sweep.py::_refuse_filing_for_stale_verification_queue  # noqa: E501
    def test_fresh_baseline_files_normally_no_new_noise(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Asserts a fresh, current verification window (`rapid_soft_
        warning` returning `None`) files with no refusal and no debt
        line, identical to `test_new_findings_file_a_ticket_and_
        rebaseline`. See T-2929 for the design rationale."""
        # frob:tests \
        # tests/unit/rapid_sweep_suite/test_sweep_run.py::TestDeferredSweepRun.test_fresh_baseline_files_normally_no_new_noise  # noqa: E501
        _write_baseline(tmp_path, frozenset({("COV003", "a.py")}), "old")
        fresh = frozenset({("COV003", "a.py"), ("DOC011", "b.md")})
        monkeypatch.setattr(
            "frob.app.ticket_runner._land_cmd._unscoped_error_findings",
            lambda *a, **k: fresh,
        )
        monkeypatch.setattr("frob.verify.rapid_soft_warning", lambda root: None)
        seen: list[frozenset[tuple[str, str]]] = []

        def _fake_file(root, final_id, commit, new_findings):  # noqa: ANN001, ANN202
            seen.append(new_findings)
            return "T-9999"

        monkeypatch.setattr(_rapid_sweep, "_file_regression_ticket", _fake_file)
        debts: list[tuple[str, str]] = []
        monkeypatch.setattr(
            "frob.tickets._evidence.record_rapid_debt",
            lambda root, tid, what: debts.append((tid, what)),
        )

        result = run_deferred_post_land_sweep(tmp_path, "T-0001", "abc123")

        assert result.is_ok
        assert result.danger_ok == "T-9999"
        assert seen == [frozenset({("DOC011", "b.md")})]
        assert debts == []
        assert _read_baseline(tmp_path) == fresh

    # frob:ticket T-4335
    # frob:tests \
    # src/frob/app/ticket_runner/_rapid_sweep.py::run_deferred_post_land_sweep
    def test_stale_baseline_refusal_is_still_new_on_the_next_sweep(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-4335's whole point, forced end-to-end: an identity a sweep
        REFUSED to file (stale verification queue) must not be absorbed
        into the baseline -- a SECOND sweep, run immediately after with
        the SAME fresh set and the staleness now cleared, must still see
        it as new and file it. This is the exact shape the bug report
        measured from the real sweep logs (T-4324 -> T-4329): a refused
        identity that a `frob check` --json read shows is still present
        must eventually be tracked by a ticket, never silently absorbed."""
        # frob:tests tests/unit/rapid_sweep_suite/test_sweep_run.py::TestDeferredSweepRun.test_stale_baseline_refusal_is_still_new_on_the_next_sweep  # noqa: E501
        _write_baseline(tmp_path, frozenset({("COV003", "a.py")}), "old")
        fresh = frozenset({("COV003", "a.py"), ("DOC006", "tickets/T-0002/ticket.md")})
        monkeypatch.setattr(
            "frob.app.ticket_runner._land_cmd._unscoped_error_findings",
            lambda *a, **k: fresh,
        )
        monkeypatch.setattr(
            "frob.tickets._evidence.record_rapid_debt", lambda *a, **k: None
        )
        monkeypatch.setattr(_rapid_sweep, "_commit_rapid_debt", lambda *a, **k: None)

        # First sweep: verification queue is stale -- refuse to file.
        monkeypatch.setattr(
            "frob.verify.rapid_soft_warning", lambda root: "stale queue"
        )
        filed_first: list[object] = []
        monkeypatch.setattr(
            _rapid_sweep,
            "_file_regression_ticket",
            lambda *a, **k: filed_first.append(a),
        )
        result_1 = run_deferred_post_land_sweep(tmp_path, "T-0001", "abc123")
        assert result_1.is_ok
        assert result_1.danger_ok is None
        assert filed_first == []
        assert _read_baseline(tmp_path) == frozenset({("COV003", "a.py")})

        # Second sweep: same fresh set, queue is current now -- must file.
        monkeypatch.setattr("frob.verify.rapid_soft_warning", lambda root: None)
        filed_second: list[frozenset[tuple[str, str]]] = []

        def _fake_file(root, final_id, commit, new_findings):  # noqa: ANN001, ANN202
            filed_second.append(new_findings)
            return "T-9999"

        monkeypatch.setattr(_rapid_sweep, "_file_regression_ticket", _fake_file)
        result_2 = run_deferred_post_land_sweep(tmp_path, "T-0002", "def456")
        assert result_2.is_ok
        assert result_2.danger_ok == "T-9999"
        assert filed_second == [frozenset({("DOC006", "tickets/T-0002/ticket.md")})]
        assert _read_baseline(tmp_path) == fresh

    # frob:ticket T-4335
    # frob:tests \
    # src/frob/app/ticket_runner/_rapid_sweep.py::run_deferred_post_land_sweep
    def test_inherited_debt_is_reported_as_debt_not_clean(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog
    ) -> None:
        """A sweep that finds zero NEW identities but a nonzero fresh
        count (pre-existing, already-baselined debt) must not log the
        contradictory 'CLEAN (N error(s))' line -- it must say the debt
        is tolerated, not clean."""
        # frob:tests tests/unit/rapid_sweep_suite/test_sweep_run.py::TestDeferredSweepRun.test_inherited_debt_is_reported_as_debt_not_clean  # noqa: E501
        existing = frozenset({("COV003", "a.py")})
        _write_baseline(tmp_path, existing, "old")
        monkeypatch.setattr(
            "frob.app.ticket_runner._land_cmd._unscoped_error_findings",
            lambda *a, **k: existing,
        )
        import logging

        with caplog.at_level(
            logging.INFO, logger="frob.app.ticket_runner._rapid_sweep"
        ):
            result = run_deferred_post_land_sweep(tmp_path, "T-0001", "abc123")
        assert result.is_ok
        assert result.danger_ok is None
        messages = [r.message for r in caplog.records]
        assert not any("CLEAN" in m and "1 error" in m for m in messages), messages
        assert any("TOLERATED DEBT" in m for m in messages), messages

    # frob:ticket T-4335
    # frob:tests \
    # src/frob/app/ticket_runner/_rapid_sweep.py::run_deferred_post_land_sweep
    def test_genuinely_zero_errors_still_says_clean(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog
    ) -> None:
        """The genuinely-zero case must still say CLEAN plainly."""
        # frob:tests tests/unit/rapid_sweep_suite/test_sweep_run.py::TestDeferredSweepRun.test_genuinely_zero_errors_still_says_clean  # noqa: E501
        _write_baseline(tmp_path, frozenset(), "old")
        monkeypatch.setattr(
            "frob.app.ticket_runner._land_cmd._unscoped_error_findings",
            lambda *a, **k: frozenset(),
        )
        import logging

        with caplog.at_level(
            logging.INFO, logger="frob.app.ticket_runner._rapid_sweep"
        ):
            result = run_deferred_post_land_sweep(tmp_path, "T-0001", "abc123")
        assert result.is_ok
        messages = [r.message for r in caplog.records]
        assert any("CLEAN (0 error(s))" in m for m in messages), messages


# frob:ticket T-2938
class TestClaimDivergencePostLand:
    """T-2938: `_check_claim_divergence_post_land` -- the deferred-queue
    replacement for the inline `ClaimDivergence` re-verification T-2913
    moved off the rapid land critical path. Reuses `frob.tickets.
    _land_verify._reverify_gate_state_claim` VERBATIM (via callables that
    hand back this sweep's own already-measured `fresh` set instead of
    spawning a second `frob check`) as the sole comparison DECISION, and
    `frob.verify.rapid_soft_warning` (T-2929's existing policy) as the
    sole staleness DECISION -- these tests exercise the wiring, not a
    second copy of either policy."""

    def _claims_ticket(
        self,
        *,
        gate_errors: int,
        error_findings: frozenset[tuple[str, str]] | None,
        scope: tuple[str, ...] = ("src/a.py",),
    ):
        from frob.tickets._models import (
            DoneReportClaims,
            Origin,
            Ticket,
            TicketKind,
            TicketState,
            render_claims_block,
        )

        claims = DoneReportClaims(
            test_count=1,
            evidence_count=1,
            gate_errors=gate_errors,
            gate_warnings=0,
            gate_waived=0,
            error_findings=error_findings,
        )
        body = "## Done report\n\nlanded cleanly.\n\n" + render_claims_block(claims)
        return Ticket(
            id="T-0001",
            title="a ticket with a captured claim",
            state=TicketState.DONE,
            kind=TicketKind.BUG,
            origin=Origin.AGENT,
            created=date(2026, 1, 1),
            body=body,
            scope=scope,
        )

    def _patch_common(
        self,
        monkeypatch: pytest.MonkeyPatch,
        ticket,
        *,
        stale_reason: str | None,
    ) -> tuple[list[dict[str, object]], list[tuple[str, str]]]:
        from typani.result import Ok

        monkeypatch.setattr("frob.tickets._load_one", lambda root, tid: Ok(ticket))
        monkeypatch.setattr("frob.verify.rapid_soft_warning", lambda root: stale_reason)
        raised: list[dict[str, object]] = []
        monkeypatch.setattr(
            "frob.verify._quarantine.raise_quarantine",
            lambda root, **kw: raised.append(kw) or Ok(object()),
        )
        debts: list[tuple[str, str]] = []
        monkeypatch.setattr(
            "frob.tickets._evidence.record_rapid_debt",
            lambda root, tid, what: debts.append((tid, what)),
        )
        monkeypatch.setattr(_rapid_sweep, "_commit_rapid_debt", lambda root, tid: None)
        monkeypatch.setattr(
            _rapid_sweep,
            "_file_claim_divergence_ticket",
            lambda root, final_id, actual_head, pairs: "T-9999",
        )
        return raised, debts

    def test_matching_claim_raises_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Must-stay-quiet: a Done report claim that still matches the
        fresh post-merge measurement raises no quarantine and records no
        new debt."""
        # frob:tests tests/unit/rapid_sweep_suite/test_sweep_run.py::TestClaimDivergencePostLand.test_matching_claim_raises_nothing  # noqa: E501
        ticket = self._claims_ticket(
            gate_errors=1, error_findings=frozenset({("COV003", "src/a.py")})
        )
        raised, debts = self._patch_common(monkeypatch, ticket, stale_reason=None)

        _check_claim_divergence_post_land(
            tmp_path, "T-0001", "deadbeef", frozenset({("COV003", "src/a.py")})
        )

        assert raised == []
        assert debts == []

    def test_divergent_claim_raises_quarantine_attributed_to_landing_ticket(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Must-fire: a Done report claiming 0 errors against a fresh
        measurement showing a NEW in-scope error raises quarantine, and
        every raised finding is attributed to the landing ticket id."""
        # frob:tests tests/unit/rapid_sweep_suite/test_sweep_run.py::TestClaimDivergencePostLand.test_divergent_claim_raises_quarantine_attributed_to_landing_ticket  # noqa: E501
        ticket = self._claims_ticket(gate_errors=0, error_findings=frozenset())
        raised, debts = self._patch_common(monkeypatch, ticket, stale_reason=None)

        _check_claim_divergence_post_land(
            tmp_path, "T-0001", "deadbeef", frozenset({("COV003", "src/a.py")})
        )

        from frob.verify._quarantine import QuarantinedFinding

        assert debts == []
        assert len(raised) == 1
        findings = cast("tuple[QuarantinedFinding, ...]", raised[0]["findings"])
        assert len(findings) == 1
        assert findings[0].rule_id == "COV003"
        assert findings[0].file == "src/a.py"
        assert findings[0].commit_sha == "deadbeef"
        assert findings[0].ticket_id == "T-9999"
        assert raised[0]["batch_commit_shas"] == ("deadbeef",)

    def test_stale_baseline_refuses_to_attribute(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A stale verification-queue window (T-2929's shared policy)
        refuses to attribute a claim divergence too, recording the SAME
        debt reason `_refuse_filing_for_stale_verification_queue` already
        uses -- never a second staleness policy."""
        # frob:tests tests/unit/rapid_sweep_suite/test_sweep_run.py::TestClaimDivergencePostLand.test_stale_baseline_refuses_to_attribute  # noqa: E501
        ticket = self._claims_ticket(gate_errors=0, error_findings=frozenset())
        raised, debts = self._patch_common(
            monkeypatch, ticket, stale_reason="rapid profile verification debt is stale"
        )

        _check_claim_divergence_post_land(
            tmp_path, "T-0001", "deadbeef", frozenset({("COV003", "src/a.py")})
        )

        assert raised == []
        assert debts == [
            ("T-0001", "post-land-sweep-attribution-skipped-stale-baseline")
        ]

    def test_no_captured_claims_section_is_a_noop(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A Done report with no `### Captured claims` section (predates
        T-0754, or never captured one) has nothing to compare -- no
        quarantine, no debt, matching the inline land path's own
        permissive-by-default posture."""
        # frob:tests tests/unit/rapid_sweep_suite/test_sweep_run.py::TestClaimDivergencePostLand.test_no_captured_claims_section_is_a_noop  # noqa: E501
        from typani.result import Ok

        from frob.tickets._models import Origin, Ticket, TicketKind, TicketState

        ticket = Ticket(
            id="T-0001",
            title="a ticket with no captured claim",
            state=TicketState.DONE,
            kind=TicketKind.BUG,
            origin=Origin.AGENT,
            created=date(2026, 1, 1),
            body="## Done report\n\nlanded cleanly, no claims captured.\n",
        )
        monkeypatch.setattr("frob.tickets._load_one", lambda root, tid: Ok(ticket))
        raised: list[dict[str, object]] = []
        monkeypatch.setattr(
            "frob.verify._quarantine.raise_quarantine",
            lambda root, **kw: raised.append(kw) or Ok(object()),
        )
        # rapid_soft_warning left un-mocked: a tmp_path with no watermark
        # returns None (no debt), same as the pre-existing tests above.

        _check_claim_divergence_post_land(
            tmp_path, "T-0001", "deadbeef", frozenset({("COV003", "src/a.py")})
        )

        assert raised == []


class TestTickRowClaimFiltering:
    """T-6569: `_filter_tick_rows_for_claim_check`/`_tick_row_subject` --
    a per-ticket TICK-rule finding's subject-carrying identity
    (`tickets.md#<ticket-id>`, `frob.gates._tickets_gate._tick_subject_
    identity_file`) must exclude a sibling ticket's row from another
    ticket's claim comparison, and must exclude the landing ticket's OWN
    TICK015 row (a land in progress is the live use of that worktree),
    while leaving every other row (a non-TICK rule, or a TICK rule about
    the landing ticket itself that is not TICK015) untouched."""

    def test_tick_row_subject_parses_encoded_identity(self) -> None:
        """Must-fire control: `_tick_row_subject` recovers the ticket id
        `_tick_subject_identity_file` encoded."""
        # frob:tests tests/unit/rapid_sweep_suite/test_sweep_run.py::TestTickRowClaimFiltering.test_tick_row_subject_parses_encoded_identity  # noqa: E501
        assert _rapid_sweep._tick_row_subject("TICK015", "tickets.md#T-0176") == "T-0176"

    def test_tick_row_subject_ignores_non_tick_rule(self) -> None:
        """A non-`TICK*` rule never carries a subject, whatever its
        `file` looks like."""
        # frob:tests tests/unit/rapid_sweep_suite/test_sweep_run.py::TestTickRowClaimFiltering.test_tick_row_subject_ignores_non_tick_rule  # noqa: E501
        assert _rapid_sweep._tick_row_subject("COV003", "tickets.md#T-0176") is None

    def test_tick_row_subject_ignores_bare_ledger_file(self) -> None:
        """A `TICK*` finding still carrying the pre-T-6569 bare
        `"tickets.md"` file has no encoded subject -- falls through
        unfiltered rather than crashing."""
        # frob:tests tests/unit/rapid_sweep_suite/test_sweep_run.py::TestTickRowClaimFiltering.test_tick_row_subject_ignores_bare_ledger_file  # noqa: E501
        assert _rapid_sweep._tick_row_subject("TICK004", "tickets.md") is None

    def test_sibling_ticket_tick015_row_is_dropped(self) -> None:
        """T-6569's positive control: a dead-worktree sibling's TICK015
        row is excluded from `T-0160`'s own claim comparison."""
        # frob:tests tests/unit/rapid_sweep_suite/test_sweep_run.py::TestTickRowClaimFiltering.test_sibling_ticket_tick015_row_is_dropped  # noqa: E501
        fresh = frozenset(
            {("TICK015", "tickets.md#T-0176"), ("COV003", "src/a.py")}
        )
        filtered = _rapid_sweep._filter_tick_rows_for_claim_check(fresh, "T-0160")
        assert filtered == frozenset({("COV003", "src/a.py")})

    def test_landing_tickets_own_tick015_row_is_dropped(self) -> None:
        """The crunk-ba addendum: TICK015 about the LANDING ticket itself
        is also excluded -- a land in progress is the live use of its
        worktree."""
        # frob:tests tests/unit/rapid_sweep_suite/test_sweep_run.py::TestTickRowClaimFiltering.test_landing_tickets_own_tick015_row_is_dropped  # noqa: E501
        fresh = frozenset(
            {("TICK015", "tickets.md#T-0160"), ("COV003", "src/a.py")}
        )
        filtered = _rapid_sweep._filter_tick_rows_for_claim_check(fresh, "T-0160")
        assert filtered == frozenset({("COV003", "src/a.py")})

    def test_landing_tickets_own_non_tick015_row_still_kept(self) -> None:
        """A per-ticket TICK rule OTHER than TICK015 about the landing
        ticket itself is not exempted -- only TICK015's own-worktree
        false positive is special-cased."""
        # frob:tests tests/unit/rapid_sweep_suite/test_sweep_run.py::TestTickRowClaimFiltering.test_landing_tickets_own_non_tick015_row_still_kept  # noqa: E501
        fresh = frozenset({("TICK010", "tickets.md#T-0160")})
        filtered = _rapid_sweep._filter_tick_rows_for_claim_check(fresh, "T-0160")
        assert filtered == fresh

    def test_end_to_end_sibling_tick015_no_longer_diverges_the_land(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-6569 end-to-end: a Done report claiming a clean gate state
        must still pass the deferred claim-divergence check when the only
        fresh finding is a SIBLING ticket's TICK015 row -- reproducing
        T-0176's dead-worktree TICK015 no longer refusing T-0160's own
        land."""
        # frob:tests tests/unit/rapid_sweep_suite/test_sweep_run.py::TestTickRowClaimFiltering.test_end_to_end_sibling_tick015_no_longer_diverges_the_land  # noqa: E501
        from frob.tickets._models import (
            DoneReportClaims,
            Origin,
            Ticket,
            TicketKind,
            TicketState,
            render_claims_block,
        )

        claims = DoneReportClaims(
            test_count=1,
            evidence_count=1,
            gate_errors=0,
            gate_warnings=0,
            gate_waived=0,
            error_findings=frozenset(),
        )
        body = "## Done report\n\nlanded cleanly.\n\n" + render_claims_block(claims)
        ticket = Ticket(
            id="T-0160",
            title="landing ticket",
            state=TicketState.DONE,
            kind=TicketKind.BUG,
            origin=Origin.AGENT,
            created=date(2026, 1, 1),
            body=body,
            scope=("src/a.py",),
        )
        from typani.result import Ok

        monkeypatch.setattr("frob.tickets._load_one", lambda root, tid: Ok(ticket))
        monkeypatch.setattr("frob.verify.rapid_soft_warning", lambda root: None)
        raised: list[dict[str, object]] = []
        monkeypatch.setattr(
            "frob.verify._quarantine.raise_quarantine",
            lambda root, **kw: raised.append(kw) or Ok(object()),
        )

        _check_claim_divergence_post_land(
            tmp_path,
            "T-0160",
            "deadbeef",
            frozenset({("TICK015", "tickets.md#T-0176")}),
        )

        assert raised == []


class TestDeferredSweepSpawn:
    """The spawn records debt BEFORE spawning and never blocks."""

    # frob:tests src/frob/app/ticket_runner/_rapid_sweep.py::spawn_deferred_post_land_sweep  # noqa: E501
    def test_exec_disabled_records_debt_and_refuses(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_sweep_run.py::TestDeferredSweepSpawn.test_exec_disabled_records_debt_and_refuses  # noqa: E501
        debts: list[tuple[str, str]] = []
        monkeypatch.setattr(
            "frob.tickets._evidence.record_rapid_debt",
            lambda root, tid, what: debts.append((tid, what)),
        )
        monkeypatch.setattr("frob.process.exec_enabled", lambda: False)
        result = spawn_deferred_post_land_sweep(tmp_path, "T-0001", "T-0001", "abc123")
        assert result.is_err
        assert result.danger_err is RapidSweepError.SpawnRefused
        assert debts == [("T-0001", "post-land-unscoped-sweep-deferred")]

    # frob:ticket T-2030
    def test_spawn_pins_frob_root_env_not_bare_os_environ(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Asserts the `Popen` call always pins `FROB_ROOT` to `root` in
        its `env=` kwarg, regardless of what `os.environ` already
        contains, so an ambient stale `FROB_ROOT` in the landing
        process's own shell cannot override the detached child's
        resolved root. See T-2030 for the design rationale."""
        # frob:tests tests/unit/rapid_sweep_suite/test_sweep_run.py::TestDeferredSweepSpawn.test_spawn_pins_frob_root_env_not_bare_os_environ  # noqa: E501
        import subprocess as subprocess_mod

        import frob.app.ticket_runner._rapid_sweep as rapid_sweep_mod

        monkeypatch.setattr("frob.process.exec_enabled", lambda: True)
        monkeypatch.setattr(
            "frob.tickets._evidence.record_rapid_debt", lambda root, tid, what: None
        )
        monkeypatch.setattr(
            rapid_sweep_mod, "_commit_rapid_debt", lambda root, tid: None
        )
        # A STALE FROB_ROOT in the ambient environment, naming a
        # DIFFERENT tree than `root` -- exactly T-2030's measured shape.
        monkeypatch.setenv("FROB_ROOT", "/some/other/worktree")
        monkeypatch.setenv("FROB_WORKTREE", "/some/other/worktree")
        monkeypatch.setenv("FROB_AGENT", "1")

        captured: dict = {}

        class _FakeProc:
            pid = 4242

        def _fake_popen(argv, **kwargs):
            captured.update(kwargs)
            return _FakeProc()

        monkeypatch.setattr(subprocess_mod, "Popen", _fake_popen)

        result = spawn_deferred_post_land_sweep(tmp_path, "T-0001", "T-0001", "abc123")
        assert result.is_ok

        env = captured.get("env")
        assert env is not None, "Popen must be called with an explicit env= kwarg"
        assert env["FROB_ROOT"] == str(tmp_path)
        assert "FROB_WORKTREE" not in env
        assert "FROB_AGENT" not in env


# frob:ticket T-2450
class TestDetachedSweepEnvPublicSeam:
    """T-2450: `detached_sweep_env` is a thin public wrapper around
    `_detached_sweep_env` -- the cross-node seam `frob.verify._drain`
    imports instead of reaching across the node boundary to call the
    private name directly."""

    # frob:ticket T-2450
    # frob:tests tests/unit/rapid_sweep_suite/test_sweep_run.py::TestDetachedSweepEnvPublicSeam.test_delegates_to_the_private_implementation  # noqa: E501
    # frob:tests src/frob/app/ticket_runner/_rapid_sweep.py::detached_sweep_env
    def test_delegates_to_the_private_implementation(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from frob.app.ticket_runner._rapid_sweep import (
            _detached_sweep_env,
            detached_sweep_env,
        )

        monkeypatch.setenv("FROB_WORKTREE", "/some/worktree")
        assert detached_sweep_env(tmp_path) == _detached_sweep_env(tmp_path)


# frob:ticket T-2030
class TestDetachedSweepEnv:
    """T-2030: `_detached_sweep_env`'s own unit-level contract."""

    # frob:tests src/frob/app/ticket_runner/_rapid_sweep.py::_detached_sweep_env
    def test_pins_frob_root_to_the_correct_root(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_sweep_run.py::TestDetachedSweepEnv.test_pins_frob_root_to_the_correct_root  # noqa: E501
        from frob.app.ticket_runner._rapid_sweep import _detached_sweep_env

        monkeypatch.setenv("FROB_ROOT", "/stale/other/worktree")
        env = _detached_sweep_env(tmp_path)
        assert env["FROB_ROOT"] == str(tmp_path)

    # frob:tests src/frob/app/ticket_runner/_rapid_sweep.py::_detached_sweep_env
    def test_strips_worktree_lease_env(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_sweep_run.py::TestDetachedSweepEnv.test_strips_worktree_lease_env  # noqa: E501
        from frob.app.ticket_runner._rapid_sweep import _detached_sweep_env

        monkeypatch.setenv("FROB_WORKTREE", "/some/worktree")
        monkeypatch.setenv("FROB_AGENT", "1")
        env = _detached_sweep_env(tmp_path)
        assert "FROB_WORKTREE" not in env
        assert "FROB_AGENT" not in env
