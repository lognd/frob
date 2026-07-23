"""T-0754: captured Done-report claims -- test count and gate state
populated from REAL command output (via injected `run_tests`/`check_gates`
callables) at `set_done_report` time, never hand-typed, and round-trippable
back out of the rendered `### Captured claims` section.

Review round 2 additions: `gate_errors`/`gate_warnings`/`gate_waived` are
now structured ints (never a free-text summary line whose timing blob is
nondeterministic -- see `tests/test_ticket_land.py`'s
`TestClaimDivergencePostMerge` for the land-side FATAL this closes), and
`parse_claims_from_done_report` is anchored to the `### Captured claims`
heading so a free-prose narrative line elsewhere can never masquerade as a
captured claim.
"""

from __future__ import annotations

from pathlib import Path

from frob.tickets import Origin, TicketKind, TicketSpec, new_ticket, set_done_report
from frob.tickets._models import DoneReportClaims, parse_claims_from_done_report
from frob.tickets._store import load_all, write_ticket


def _spec(title: str) -> TicketSpec:
    return TicketSpec(title=title, kind=TicketKind.FEATURE, origin=Origin.AGENT)


class TestDoneReportClaimsModel:
    """Round-trip of `render_claims_block`/`parse_claims_from_done_report`
    via `DoneReportClaims`, independent of `set_done_report`."""

    def test_round_trips_through_a_done_report_body(self) -> None:
        # frob:tests tests/test_ticket_done_report_claims.py::TestDoneReportClaimsModel.test_round_trips_through_a_done_report_body  # noqa: E501
        from frob.tickets._models import render_claims_block

        claims = DoneReportClaims(
            test_count=4,
            evidence_count=5,
            gate_errors=0,
            gate_warnings=12,
            gate_waived=3,
        )
        block = render_claims_block(claims)
        body = f"## Done report\n\nwhy\n\n### Evidence\n(none)\n\n{block}\n"
        assert parse_claims_from_done_report(body) == claims

    # frob:ticket T-0846
    # frob:tests tests/test_ticket_done_report_claims.py::TestDoneReportClaimsModel.test_error_findings_round_trips_through_a_done_report_body  # noqa: E501
    def test_error_findings_round_trips_through_a_done_report_body(self) -> None:
        """T-0846: a claim carrying a real (possibly-empty) `error_findings`
        identity set round-trips distinctly from one carrying `None` (no
        identity capture supplied at all) -- `_reverify_done_report_claims_
        post_merge` branches on that distinction to decide whether the
        identity-based or count-only comparison applies."""
        from frob.tickets._models import render_claims_block

        claims = DoneReportClaims(
            test_count=1,
            evidence_count=1,
            gate_errors=2,
            gate_warnings=0,
            gate_waived=0,
            error_findings=frozenset(
                {("SCOPE001", "src/a.py"), ("COV002", "src/b.py")}
            ),
        )
        block = render_claims_block(claims)
        body = f"## Done report\n\nwhy\n\n### Evidence\n(none)\n\n{block}\n"
        assert parse_claims_from_done_report(body) == claims

    # frob:ticket T-0846
    # frob:tests tests/test_ticket_done_report_claims.py::TestDoneReportClaimsModel.test_measured_empty_error_findings_differs_from_none  # noqa: E501
    def test_measured_empty_error_findings_differs_from_none(self) -> None:
        """A MEASURED-but-empty `error_findings` set (a real check ran and
        found zero errors) must round-trip as `frozenset()`, never as
        `None` (which means no identity capture was supplied at all) --
        the same "measured vs unmeasured" distinction T-0832 established
        for `gate_errors` itself, one level down."""
        from frob.tickets._models import render_claims_block

        claims = DoneReportClaims(
            test_count=1,
            evidence_count=1,
            gate_errors=0,
            gate_warnings=0,
            gate_waived=0,
            error_findings=frozenset(),
        )
        block = render_claims_block(claims)
        assert "- error-findings: none (measured, zero errors)" in block
        body = f"## Done report\n\nwhy\n\n### Evidence\n(none)\n\n{block}\n"
        parsed = parse_claims_from_done_report(body)
        assert parsed is not None
        assert parsed.error_findings == frozenset()
        assert parsed.error_findings is not None

    def test_missing_section_returns_none(self) -> None:
        # frob:tests tests/test_ticket_done_report_claims.py::TestDoneReportClaimsModel.test_missing_section_returns_none  # noqa: E501
        body = "## Done report\n\nwhy\n\n### Evidence\n(none)\n"
        assert parse_claims_from_done_report(body) is None

    def test_free_prose_elsewhere_never_masquerades_as_claims(self) -> None:
        # frob:tests tests/test_ticket_done_report_claims.py::TestDoneReportClaimsModel.test_free_prose_elsewhere_never_masquerades_as_claims  # noqa: E501
        """Security property (T-0754 review round 2 fix #5): a narrative
        line that happens to match the claims regex shape, sitting OUTSIDE
        any `### Captured claims` heading, must never parse as a real
        captured claim -- only lines strictly inside that heading's own
        block count."""
        body = (
            "## Done report\n\n"
            "why: manually verified this by hand.\n"
            "- tests: 999 passed (from 999 evidence id(s))\n"
            "- gates: 0 errors, 0 warnings, 0 waived\n\n"
            "### Evidence\n(none)\n"
        )
        assert parse_claims_from_done_report(body) is None

    def test_only_lines_inside_the_claims_heading_count(self) -> None:
        # frob:tests tests/test_ticket_done_report_claims.py::TestDoneReportClaimsModel.test_only_lines_inside_the_claims_heading_count  # noqa: E501
        """A REAL Captured claims section is still recovered even when a
        look-alike narrative line (see the sibling masquerade test)
        precedes it elsewhere in the same Done report."""
        body = (
            "## Done report\n\n"
            "- tests: 999 passed (from 999 evidence id(s))\n\n"
            "### Evidence\n(none)\n\n"
            "### Captured claims\n"
            "- tests: 2 passed (from 2 evidence id(s))\n"
            "- gates: 0 error(s), 1 warning(s), 0 waived\n"
        )
        claims = parse_claims_from_done_report(body)
        assert claims == DoneReportClaims(
            test_count=2,
            evidence_count=2,
            gate_errors=0,
            gate_warnings=1,
            gate_waived=0,
        )


class TestSetDoneReportClaims:
    def test_claims_omitted_when_no_callables_supplied(self, tmp_path: Path) -> None:
        # frob:tests tests/test_ticket_done_report_claims.py::TestSetDoneReportClaims.test_claims_omitted_when_no_callables_supplied  # noqa: E501
        """Backward compat (T-0458 callers unaffected): omitting
        `run_tests`/`check_gates` writes no `### Captured claims` section
        at all."""
        created = new_ticket(tmp_path, _spec("No capture"))
        assert created.is_ok
        tid = created.danger_ok.id

        result = set_done_report(tmp_path, tid, why="did the thing")
        assert result.is_ok
        assert "### Captured claims" not in result.danger_ok.body

    def test_claims_captured_from_real_callables(self, tmp_path: Path) -> None:
        # frob:tests tests/test_ticket_done_report_claims.py::TestSetDoneReportClaims.test_claims_captured_from_real_callables  # noqa: E501
        """The whole point: the recorded count/gate-counts come from the
        CALLABLES' return values, not any text the caller passed as
        `why`."""
        created = new_ticket(tmp_path, _spec("Real capture"))
        assert created.is_ok
        tid = created.danger_ok.id
        loaded = load_all(tmp_path)
        ticket = loaded.danger_ok[tid]
        ticket = ticket.model_copy(
            update={"evidence": ("tests/a.py::test_1", "tests/a.py::test_2")}
        )
        assert write_ticket(tmp_path, ticket).is_ok

        seen_ids: list[tuple[str, ...]] = []

        def run_tests(ids):  # noqa: ANN001, ANN202
            seen_ids.append(tuple(ids))
            return 2

        result = set_done_report(
            tmp_path,
            tid,
            why="claimed way more tests passed than actually did, on purpose",
            run_tests=run_tests,
            check_gates=lambda: (0, 2, 1),
        )
        assert result.is_ok
        body = result.danger_ok.body
        assert "### Captured claims" in body
        assert "- tests: 2 passed (from 2 evidence id(s))" in body
        assert "- gates: 0 error(s), 2 warning(s), 1 waived" in body
        assert seen_ids == [("tests/a.py::test_1", "tests/a.py::test_2")]

        claims = parse_claims_from_done_report(body)
        assert claims == DoneReportClaims(
            test_count=2,
            evidence_count=2,
            gate_errors=0,
            gate_warnings=2,
            gate_waived=1,
        )

    def test_divergent_real_count_is_recorded_not_the_typed_narrative(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_ticket_done_report_claims.py::TestSetDoneReportClaims.test_divergent_real_count_is_recorded_not_the_typed_narrative  # noqa: E501
        """Acceptance [0]: the real run's count is what gets recorded, even
        when the agent's free-prose narrative claims something else --
        the whole point of capturing instead of typing."""
        created = new_ticket(tmp_path, _spec("Divergent capture"))
        assert created.is_ok
        tid = created.danger_ok.id
        loaded = load_all(tmp_path)
        ticket = loaded.danger_ok[tid]
        ticket = ticket.model_copy(update={"evidence": ("tests/a.py::test_1",)})
        assert write_ticket(tmp_path, ticket).is_ok

        result = set_done_report(
            tmp_path,
            tid,
            why="Gates: all 12 tests passed, 0 errors",
            run_tests=lambda ids: 0,
            check_gates=lambda: (1, 0, 0),
        )
        assert result.is_ok
        body = result.danger_ok.body
        # The narrative prose is preserved verbatim (WHY stays free text)...
        assert "Gates: all 12 tests passed, 0 errors" in body
        # ...but the CAPTURED claim reflects the real run, not the prose.
        assert "- tests: 0 passed (from 1 evidence id(s))" in body
        assert "- gates: 1 error(s), 0 warning(s), 0 waived" in body

    def test_gate_state_only_no_test_capture_leaves_claims_out(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_ticket_done_report_claims.py::TestSetDoneReportClaims.test_gate_state_only_no_test_capture_leaves_claims_out  # noqa: E501
        """Only one of `run_tests`/`check_gates` supplied is treated as
        "not opted in" -- both must be present to attempt a real capture,
        matching the D-05 collected/passed independence but with an
        all-or-nothing gate here since the rendered claim is one block."""
        created = new_ticket(tmp_path, _spec("Partial capture"))
        assert created.is_ok
        tid = created.danger_ok.id

        result = set_done_report(
            tmp_path, tid, why="partial", check_gates=lambda: (0, 0, 0)
        )
        assert result.is_ok
        assert "### Captured claims" not in result.danger_ok.body
