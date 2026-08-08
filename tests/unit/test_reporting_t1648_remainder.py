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
