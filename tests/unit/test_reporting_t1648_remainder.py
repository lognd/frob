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
        text = "Split 1 of 53 files; the other 52 were not attempted."
        assert disclosure_shaped_language(text) == "not attempted"

    def test_case_insensitive(self) -> None:
        # frob:tests tests/unit/test_reporting_t1648_remainder.py::TestDisclosureShapedLanguage.test_case_insensitive  # noqa: E501
        assert disclosure_shaped_language("STILL OUTSTANDING work here") is not None

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

    # frob:ticket T-2638
    def test_no_done_report_heading_is_not_flagged_by_structure(self) -> None:
        # frob:tests tests/unit/test_reporting_t1648_remainder.py::TestDisclosureShapedLanguage.test_no_done_report_heading_is_not_flagged_by_structure  # noqa: E501
        text = "## Root cause\n\nSomething.\n\n### Details\n\nMore.\n"
        assert disclosure_shaped_language(text) is None


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
