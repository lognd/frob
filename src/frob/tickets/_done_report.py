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

# frob:waive REF002 reason="T-3195 split this guard into its own module on 2026-08-28; \
# src/frob/tickets/_evidence.py is the sole intended caller by design (the guard fires \
# from _evidence.py's close-path check) -- a second independent consumer is not \
# expected, this is a leaf policy module, not a shared utility"

from __future__ import annotations

from frob.tickets._models import (
    Ticket,
    TicketKind,
    _done_report_section_lines,
    is_cmd_evidence,
    parse_claims_from_done_report,
)

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


# frob:ticket T-3266
# frob:doc \
# docs/modules/tickets-data-storage.md#stale-captured-claims-refused-at-close-t-3266
# frob:tests tests/test_tickets.py::TestStaleClaimsGuard.test_zero_claims_with_real_evidence_refused  # noqa: E501
# frob:tests tests/test_tickets.py::TestStaleClaimsGuard.test_wrong_nonzero_claims_refused  # noqa: E501
# frob:tests tests/test_tickets.py::TestStaleClaimsGuard.test_matching_claims_not_flagged  # noqa: E501
# frob:tests tests/test_tickets.py::TestStaleClaimsGuard.test_no_claims_section_not_flagged  # noqa: E501
def _stale_claims_reason(ticket: Ticket, body: str) -> str | None:
    """`None` if `body`'s '### Captured claims' section (if any) has an
    `evidence_count` matching `ticket`'s own recorded non-cmd evidence
    count, else a human-readable reason string naming both numbers (T-3266).

    MEASURED 2026-08-28 (T-3266): 206 of 1,934 done-reports on main (10.7%)
    render a Captured-claims evidence count that disagrees with the
    ticket's own `evidence:` list -- 145 claim zero against real evidence
    (worst case: 47 ids rendered as 0), 61 claim a wrong non-zero count.
    Root cause: `set_done_report` (`_reporting.py`) captures claims from a
    ticket snapshot read once, and nothing re-captures them if evidence is
    attached (`frob ticket evidence`) AFTER the Done report narrative was
    last written -- the report's own docstring already flagged this
    tradeoff as a rare race; measurement showed it is instead the
    project's dominant wrong-record defect class, live on ~40% of recent
    lands, not a historical artifact.

    This is the T-3195 hollow-report guard's structural sibling: that
    guard catches the ALL-zero placeholder-text shape
    (`_is_hollow_done_report`); this one catches every OTHER disagreement
    between the rendered claims number and the ticket's actual evidence,
    including the "wrong non-zero" shape a hollow-only check can never see
    (T-3230: evidence=6, claims=3). Wiring this into the same close-time
    structural guard `_is_hollow_done_report` already sits in
    (`_evidence.py::_done_transition_structural_guard`) means a NEW close
    can never reach `done` on main carrying a stale claims line again --
    the fix is enforcement at the write boundary, not a rewrite of the
    206 historical reports already on main (deliberately left as-is, a
    record of what happened, per this ticket's own explicit instruction
    not to bulk-rewrite landed artifacts).

    Returns `None` (never flags) when `body` carries no '### Captured
    claims' section at all -- an older or claims-less Done report is a
    different, pre-existing shape this guard does not police."""
    claims = parse_claims_from_done_report(body)
    if claims is None:
        return None
    actual = len([e for e in ticket.evidence if not is_cmd_evidence(e)])
    if claims.evidence_count == actual:
        return None
    return (
        f"Done report's Captured claims line says {claims.evidence_count} "
        f"evidence id(s) but the ticket currently records {actual} -- "
        "re-run `frob ticket done-report` to refresh it"
    )
