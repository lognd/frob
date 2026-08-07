## Done report

Root cause: `_done_report_section_lines`/`replace_done_report_section`
(src/frob/tickets/_models.py) found the FIRST line anywhere in a ticket's
body that read exactly "## Done report" and treated its position as the
section start, with no check that the match was actually a genuine
section heading rather than a narrative/description line that merely
reads identically (e.g. a line-wrapped quoted phrase discussing this very
class of bug, landing at the start of its own physical line). When such a
lookalike line sat in the ticket's pre-existing Description/Plan prose
BEFORE any real Done report existed, `replace_done_report_section` spliced
the new report in at that lookalike position and silently dropped
everything in the body that followed it -- observed for real in T-0848's
own ledger block during its landing.

Fix: added `_is_real_done_report_heading` (src/frob/tickets/_models.py),
which only accepts a heading match as genuine when it is the first line
of the body or immediately preceded by a blank line -- the Markdown
convention every real heading this package writes (or a hand-authored
--body-file section) follows, and which a mid-paragraph line-wrap
lookalike never satisfies (it is preceded by another text line continuing
the same paragraph). `_find_done_report_heading` scans all exact-text
matches in order and returns the first one that passes this check;
`_done_report_section_lines` and `replace_done_report_section` both now
delegate to it instead of taking the first raw string match.

An earlier draft of this fix required a trailing "### Changed" marker
(the auto-generated Changed-block marker) instead of the blank-line
heuristic; that broke every legitimately terse Done report with no
Changed/Evidence block at all (this repo's own D-03 test fixtures use
bodies like "## Done report\nDone.\n") -- reverted in favor of the
blank-line-precedes check, which needs nothing about what follows the
candidate line.

Added TestDoneReportHeadingImpersonation
(tests/test_evidence_integrity.py) with two cases: a lookalike heading
line in pre-existing Description prose before any real report exists
(reproduces the exact T-0848 corruption -- content after the lookalike
line used to be silently dropped), and a second `done-report` call that
must still correctly replace only the real prior section when a lookalike
line also precedes it in the Description.

Verified: `uv run pytest tests/test_evidence_integrity.py
tests/test_tickets.py tests/unit/test_ticket_store.py -p no:cacheprovider
-q` -- 185 passed (37+72+76... see console: 3 files, all green, no
failures). `uv run frob check --only lint/static/gates-fast/gates-native/
gates-security --ticket T-0853` (chunked per playbook 3b): all five stage
groups report 0 errors (gates-fast required one `frob ticket sweep
T-0853` re-run first to clear a stale PRE001 after touching files).
ruff clean on both PATH ruff and `uv run ruff` for the two touched files.

Deviation from ticket's own fix-direction list: implemented neither of
the two directions named verbatim ("escape/reflow at render time" or
"require the Changed/Evidence structure to follow") -- escaping at
render time cannot fix ALREADY-EXISTING lookalike lines in a ticket's
hand-authored Description (which set_done_report never touches), and
requiring Changed/Evidence structure to follow breaks legitimate terse
reports as described above. Used a third approach (blank-line-preceded
heading convention) that satisfies the stated acceptance without either
drawback.

### Changed
(no changed files detected)

### Evidence
- `tests/test_evidence_integrity.py::TestDoneReportHeadingImpersonation::test_lookalike_heading_before_real_report_ignored` (pytest node id, verified passing when recorded)
- `tests/test_evidence_integrity.py::TestDoneReportHeadingImpersonation::test_lookalike_heading_without_changed_marker_not_real` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
