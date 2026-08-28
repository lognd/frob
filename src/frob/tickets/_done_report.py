"""frob.tickets._done_report -- refuse the hollow-done-report class
(T-3195): a Done report that records BOTH zero evidence and zero changed
files for a ticket transitioning to `done`. That combination is not
silent about being empty -- `render_evidence_block`/`render_changed_
block` render it as literal placeholder text ("(no evidence recorded)" /
"(no changed files detected)") -- but nothing previously refused
committing it anyway, so a ticket could reach `done` on main carrying a
report that affirmatively records no real work while the ticket's actual
work sat unlanded elsewhere (T-3157's measured incident).

MEASURED 2026-08-28 (T-3195): 45 such reports already exist on main --
`git grep -l "(no changed files detected)" -- tickets/` intersected with
`grep -l "(no evidence recorded)"`, excluding this ticket's own body
(which quotes the pattern, not an instance of it), with every remaining
ticket confirmed `state: done`. That population predates this guard and
is a record of what happened -- T-3195 explicitly does not delete or
rewrite any of it. This module only refuses NEW hollow reports going
forward."""

from __future__ import annotations

from frob.tickets._models import Ticket, TicketKind, _done_report_section_lines

# Exact placeholder text `render_evidence_block`/`render_changed_block`
# (frob.tickets._evidence) emit for the empty case -- the only strings
# this module matches against, so a report is never flagged for
# containing similar-looking prose ELSEWHERE in the narrative (e.g. a
# report that quotes these markers while explaining them, as this
# module's own docstring above does), only the literal auto-fill output
# actually rendered under the `### Changed`/`### Evidence` headings.
_HOLLOW_EVIDENCE_MARKER = "(no evidence recorded)"
_HOLLOW_CHANGED_MARKER = "(no changed files detected)"
_CHANGED_HEADING = "### Changed"
_EVIDENCE_HEADING = "### Evidence"

# T-3195's carved-out exemption: a narrative that explicitly names a
# no-behaviour-change close is visibly different from a silently-hollow
# one, so it is let through rather than papered over with a waiver.
_NO_BEHAVIOUR_CHANGE_MARKER = "no behaviour change"


def _section_body(lines: list[str], heading: str) -> str | None:
    """The text directly under a `### <heading>` line in `lines` (a Done
    report's own lines), up to the next `### ` heading or the end -- or
    `None` if `heading` is not present. Used to scope the hollow-marker
    check to the actual auto-filled section content, never to free
    narrative text that may happen to quote the marker strings (as this
    module's own docstring does)."""
    start = next(
        (i for i, line in enumerate(lines) if line.strip() == heading), None
    )
    if start is None:
        return None
    end = next(
        (
            i
            for i in range(start + 1, len(lines))
            if lines[i].strip().startswith("### ")
        ),
        len(lines),
    )
    return "\n".join(lines[start + 1 : end]).strip()


# frob:ticket T-3195
# frob:tests tests/test_tickets.py::TestHollowDoneReportGuard.test_rapid_hollow_report_refused  # noqa: E501
# frob:tests tests/test_tickets.py::TestHollowDoneReportGuard.test_real_evidence_never_flagged_as_hollow  # noqa: E501
# frob:tests tests/test_tickets.py::TestHollowDoneReportGuard.test_narrative_mentioning_the_markers_is_never_flagged  # noqa: E501
def _is_hollow_done_report(body: str) -> bool:
    """True when `body` (a ticket's Done report text) has a `### Changed`
    section whose content is EXACTLY the empty-case placeholder AND a
    `### Evidence` section whose content is EXACTLY the empty-case
    placeholder (T-3195) -- the exact shape that reached main for T-3157
    while its real work sat unlanded in a worktree. Scoped to those two
    sections specifically (via `_section_body`), not a raw substring
    search over the whole body, so narrative prose that merely quotes or
    discusses the marker text (e.g. describing this very guard) is never
    mistaken for an actually-hollow report."""
    lines = _done_report_section_lines(body)
    if lines is None:
        return False
    changed = _section_body(lines, _CHANGED_HEADING)
    evidence = _section_body(lines, _EVIDENCE_HEADING)
    return changed == _HOLLOW_CHANGED_MARKER and evidence == _HOLLOW_EVIDENCE_MARKER


# frob:ticket T-3195
# frob:tests tests/test_tickets.py::TestHollowDoneReportGuard.test_docs_kind_rapid_hollow_report_exempt  # noqa: E501
# frob:tests tests/test_tickets.py::TestHollowDoneReportGuard.test_no_behaviour_change_narrative_exempt  # noqa: E501
def _hollow_done_report_exempt(ticket: Ticket, body: str, *, rapid: bool) -> bool:
    """True when `ticket` is legitimately allowed to close carrying a
    hollow Done report (T-3195's stated exemption): a DOCS-kind ticket
    closed under the rapid/light profile (frob has no separate "chore"
    kind -- DOCS is the closest existing evidence-light kind), or a
    narrative that explicitly records a no-behaviour-change close. Both
    exemptions are visible on the ticket itself (its `kind` field, or the
    narrative text a reviewer already reads) -- neither is a silent
    bypass."""
    if ticket.kind is TicketKind.DOCS and rapid:
        return True
    return _NO_BEHAVIOUR_CHANGE_MARKER in body.lower()
