"""T-1648: unit tests for the disclosure-shaped-language heuristic and the
`Filed:` ticket-id parser, the two pure-function pieces of the "a ticket
can close with disclosed unfinished work and no follow-up" fix -- see
`frob.app.ticket_runner._close_cmd._undisclosed_remainder_reason` for the
end-to-end wiring these building blocks feed."""

from __future__ import annotations

from frob.tickets._reporting import disclosure_shaped_language, filed_followup_tickets


class TestDisclosureShapedLanguage:
    """A generous phrase match, not an English parser (see the ticket's
    own note: false positives are the acceptable failure mode)."""

    def test_detects_known_phrase(self) -> None:
        # frob:tests tests/unit/test_reporting_t1648_remainder.py::TestDisclosureShapedLanguage.test_detects_known_phrase  # noqa: E501
        # T-2726: signal 1 now scopes to the Done-report section, same
        # as signal 2 -- so the phrase must sit under that heading.
        text = (
            "## Done report\n\nSplit 1 of 53 files; the other 52 were not attempted.\n"
        )
        assert disclosure_shaped_language(text) == "not attempted"

    def test_case_insensitive(self) -> None:
        # frob:tests tests/unit/test_reporting_t1648_remainder.py::TestDisclosureShapedLanguage.test_case_insensitive  # noqa: E501
        text = "## Done report\n\nSTILL OUTSTANDING work here\n"
        assert disclosure_shaped_language(text) is not None

    def test_clean_narrative_is_not_flagged(self) -> None:
        # frob:tests tests/unit/test_reporting_t1648_remainder.py::TestDisclosureShapedLanguage.test_clean_narrative_is_not_flagged  # noqa: E501
        text = "Fixed the PERF010 family across every touched file, all clean."
        assert disclosure_shaped_language(text) is None

    # frob:ticket T-2638
    def test_reworded_heading_still_flagged_structurally(self) -> None:
        # frob:tests tests/unit/test_reporting_t1648_remainder.py::TestDisclosureShapedLanguage.test_reworded_heading_still_flagged_structurally  # noqa: E501
        # T-2638's own confirmed incident: renaming the disclosure
        # heading from "What was NOT done, and why" (phrase-matched on
        # "not done") to a phrase-free "Scope boundary: ..." title, with
        # the SAME disclosed content unchanged one line below, used to
        # silence the phrase scan entirely. The structural subheading
        # check must still fire on it, regardless of wording.
        original = (
            "## Done report\n\nDid most of it.\n\n"
            "### What was NOT done, and why\n\nThe rest.\n"
        )
        reworded = (
            "## Done report\n\nDid most of it.\n\n"
            "### Scope boundary: measurement only, zero repairs (by design)\n\n"
            "The rest.\n"
        )
        assert disclosure_shaped_language(original) is not None
        assert disclosure_shaped_language(reworded) is not None

    # frob:ticket T-2638
    def test_description_headings_before_done_report_are_not_flagged(self) -> None:
        # frob:tests tests/unit/test_reporting_t1648_remainder.py::TestDisclosureShapedLanguage.test_description_headings_before_done_report_are_not_flagged  # noqa: E501
        # A ticket's own DESCRIPTION routinely carries rich `##`/`###`
        # structure (a "## Root cause" / "### Fix" section is normal
        # ticket-body prose, not a disclosure) -- the structural check
        # must scope to content under the LAST `## Done report` heading
        # only, or it would false-positive on nearly every ticket.
        text = (
            "## Root cause\n\nSomething.\n\n### Details\n\nMore.\n\n"
            "## Done report\n\nFixed everything, all clean.\n"
        )
        assert disclosure_shaped_language(text) is None

    # frob:ticket T-2726
    def test_phrase_in_description_before_done_report_is_not_flagged(self) -> None:
        # frob:tests tests/unit/test_reporting_t1648_remainder.py::TestDisclosureShapedLanguage.test_phrase_in_description_before_done_report_is_not_flagged  # noqa: E501
        # T-2726's own confirmed incident: T-2718's ticket DESCRIPTION
        # discussed disclosure-shaped language as its subject matter,
        # quoting "named no follow-up" -- signal 1 used to scan the
        # WHOLE body (description included), independent of signal 2's
        # already-scoped Done-report check, and independent of the
        # Done report's own content. A ticket whose description
        # legitimately discusses this guard's subject must close clean
        # when its Done report itself is clean.
        text = (
            "## Description\n\n"
            "Signal 1 fires even when the Done report named no follow-up "
            "and disclosed cut work honestly -- that phrase alone should "
            "not have blocked close.\n\n"
            "## Done report\n\nAll clean, nothing cut.\n\n"
            "### Changed\n\n- x.py\n\n"
            "### Evidence\n\n- tests/x.py::test_ok\n"
        )
        assert disclosure_shaped_language(text) is None

    # frob:ticket T-2726
    def test_phrase_in_done_report_still_fires(self) -> None:
        # frob:tests tests/unit/test_reporting_t1648_remainder.py::TestDisclosureShapedLanguage.test_phrase_in_done_report_still_fires  # noqa: E501
        # The positive control the narrowing must not remove: a genuine
        # hedged claim INSIDE the Done report itself -- no subheading,
        # plain prose -- still fires exactly as before T-2726.
        text = (
            "## Description\n\nOrdinary ticket about something else.\n\n"
            "## Done report\n\n"
            "Fixed most of it; the edge case was not addressed.\n\n"
            "### Changed\n\n- x.py\n\n"
            "### Evidence\n\n- tests/x.py::test_ok\n"
        )
        assert disclosure_shaped_language(text) == "not addressed"

    # frob:ticket T-2638
    def test_no_done_report_heading_is_not_flagged_by_structure(self) -> None:
        # frob:tests tests/unit/test_reporting_t1648_remainder.py::TestDisclosureShapedLanguage.test_no_done_report_heading_is_not_flagged_by_structure  # noqa: E501
        text = "## Root cause\n\nSomething.\n\n### Details\n\nMore.\n"
        assert disclosure_shaped_language(text) is None

    # frob:ticket T-2718
    def test_tier_a_generated_report_with_no_real_followup_closes_clean(self) -> None:
        # frob:tests tests/unit/test_reporting_t1648_remainder.py::TestDisclosureShapedLanguage.test_tier_a_generated_report_with_no_real_followup_closes_clean  # noqa: E501
        # T-2718's own positive control: a Tier-A `compose_done_report`
        # shape (Changed + Evidence, the two headings it always writes)
        # with a clean narrative and no genuinely cut work must NOT be
        # flagged, even with no hand-appended `Filed:` line -- the
        # measured incident (T-2141/T-2303/T-2679/T-2128) was exactly
        # this report shape refusing to close.
        text = (
            "## Done report\n\nAll clean, nothing cut.\n\n"
            "### Changed\n\n- src/frob/tickets/_land.py\n\n"
            "### Evidence\n\n- tests/unit/test_x.py::test_ok\n"
        )
        assert disclosure_shaped_language(text) is None

    # frob:ticket T-2718
    def test_tier_a_generated_report_with_captured_claims_and_amendments_closes_clean(
        self,
    ) -> None:
        # frob:tests tests/unit/test_reporting_t1648_remainder.py::TestDisclosureShapedLanguage.test_tier_a_generated_report_with_captured_claims_and_amendments_closes_clean  # noqa: E501
        # All FOUR fixed generator headings together, still exempt.
        text = (
            "## Done report\n\nAll clean.\n\n"
            "### Changed\n\n- x.py\n\n"
            "### Evidence\n\n- tests/x.py::test_ok\n\n"
            "### Captured claims\n\n- 0 errors\n\n"
            "### Acceptance amendments\n\n- [0] replace: 'a' -> 'b'\n"
        )
        assert disclosure_shaped_language(text) is None

    # frob:ticket T-2718
    def test_genuine_hand_typed_subheading_alongside_generated_ones_still_fires(
        self,
    ) -> None:
        # frob:tests tests/unit/test_reporting_t1648_remainder.py::TestDisclosureShapedLanguage.test_genuine_hand_typed_subheading_alongside_generated_ones_still_fires  # noqa: E501
        # The negative control this fix must NOT remove: a ticket that
        # genuinely cut scope and named no follow-up, expressed as a
        # real subheading sitting ALONGSIDE the generated ones, still
        # trips the structural check -- the fix only exempts the four
        # exact fixed titles, never anything else.
        text = (
            "## Done report\n\nMostly done.\n\n"
            "### Changed\n\n- x.py\n\n"
            "### Evidence\n\n- tests/x.py::test_ok\n\n"
            "### Scope boundary: measurement only\n\nThe rest was cut.\n"
        )
        result = disclosure_shaped_language(text)
        assert result is not None
        assert "Scope boundary" in result

    # frob:ticket T-2718
    def test_renaming_a_generated_heading_still_fires(self) -> None:
        # frob:tests tests/unit/test_reporting_t1648_remainder.py::TestDisclosureShapedLanguage.test_renaming_a_generated_heading_still_fires  # noqa: E501
        # T-2638's own reword-proof guarantee, preserved: the exemption
        # is an EXACT-title allowlist, not a prefix/substring match, so
        # renaming "### Evidence" to anything else still fires.
        text = (
            "## Done report\n\nDid it.\n\n"
            "### Changed\n\n- x.py\n\n"
            "### Proof (renamed from Evidence)\n\n- tests/x.py::test_ok\n"
        )
        assert disclosure_shaped_language(text) is not None


class TestFiledFollowupTickets:
    """Parses the playbook's own 'Filed:' Done-report convention."""

    def test_parses_ids_from_filed_line(self) -> None:
        # frob:tests tests/unit/test_reporting_t1648_remainder.py::TestFiledFollowupTickets.test_parses_ids_from_filed_line  # noqa: E501
        body = "## Done report\n\nDid X.\n\nFiled: T-1900, T-1901\n"
        assert filed_followup_tickets(body) == ["T-1900", "T-1901"]

    def test_no_filed_line_returns_empty(self) -> None:
        # frob:tests tests/unit/test_reporting_t1648_remainder.py::TestFiledFollowupTickets.test_no_filed_line_returns_empty  # noqa: E501
        assert filed_followup_tickets("## Done report\n\nDid X.\n") == []

    def test_filed_none_returns_empty(self) -> None:
        # frob:tests tests/unit/test_reporting_t1648_remainder.py::TestFiledFollowupTickets.test_filed_none_returns_empty  # noqa: E501
        assert filed_followup_tickets("Filed: none\n") == []

    # frob:ticket T-2638
    def test_parses_draft_ids(self) -> None:
        # frob:tests tests/unit/test_reporting_t1648_remainder.py::TestFiledFollowupTickets.test_parses_draft_ids  # noqa: E501
        # Draft ids (`T-draft-<hex>`) are the mandated shape for a
        # follow-up filed before its own worktree lands -- a ticket
        # whose every follow-up is a draft must be able to satisfy this
        # guard (T-2623's real incident: 8 real drafts, refused anyway).
        body = "## Done report\n\nDid X.\n\nFiled: T-draft-295a2473, T-draft-0abc1234\n"
        assert filed_followup_tickets(body) == [
            "T-draft-295a2473",
            "T-draft-0abc1234",
        ]

    # frob:ticket T-2638
    def test_parses_mixed_real_and_draft_ids(self) -> None:
        # frob:tests tests/unit/test_reporting_t1648_remainder.py::TestFiledFollowupTickets.test_parses_mixed_real_and_draft_ids  # noqa: E501
        body = "Filed: T-1900, T-draft-abcdef01\n"
        assert filed_followup_tickets(body) == ["T-1900", "T-draft-abcdef01"]
