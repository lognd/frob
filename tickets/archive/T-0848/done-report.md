## Done report

` section by scanning forward for the next
line that is exactly `## ` (H2) and is NOT itself another `## Done
report` heading -- treating that as the section boundary. This silently
breaks whenever the Done-report NARRATIVE ITSELF legitimately uses `## `
(H2) sub-headings (e.g. `## Per-pattern decision`, `## Reviewer round 1`,
`## Gates`) rather than `### ` (H3): the parser stops at the FIRST such
line, so `replace_done_report_section` only ever overwrites the short
intro paragraph BEFORE that first H2 sub-heading and treats everything
from there onward (the bulk of the actual report) as unrelated ticket
body content to preserve untouched.

On a SECOND `frob ticket done-report --why-file` call (e.g. a reviewer-
requested correction), the tool composes a brand-new full section
(heading + entire new narrative, itself containing multiple `## `
sub-headings) and splices it into the too-small "replaceable" window it
detected. The net effect is NOT a replace: the new full report gets
inserted ahead of the stale first-round report, which survives verbatim
below it -- a live ticket record that visibly contradicts itself (in the
repro below, the corrected round advises the ORIGINAL, reviewer-disproven
claim still reads as live text in the surviving stale block).

This is more severe than T-0826 ("done-report --why-file duplicates the
'## Done report' heading (recurring cosmetic ledger noise)"), which is
scoped to a purely cosmetic double-heading case (a --why-file that
already begins with its own `## Done report` heading). This finding is a
distinct code path in the SAME function family (`_done_report_section_end`
/ `replace_done_report_section` in `src/frob/tickets/_models.py`) with a
much worse outcome: silent, undetected duplication of an entire prior
report body, including a factual claim the second round explicitly
disproved, persisting as live-looking ledger text. Filed separately
because T-0826's acceptance criterion ("exactly one heading appears")
would not catch this case even if satisfied -- the heading can be
singular while the BODY still duplicates.

## Reproduction

1. `frob ticket done-report T-0605 --why-file r1.md` where `r1.md`'s
   content contains internal `## ` (H2) headings, e.g.:
   ```
   Some intro paragraph.

   ## Per-pattern decision

   1. ... the two hallmarks are structurally disjoint per-method, so a
      class cannot double-fire both.

   ## Evidence

   ...
   ```
   First call succeeds and looks correct (nothing pre-existing to
   preserve incorrectly).
2. Edit `r1.md` in place -- e.g. append a "## Reviewer round 1" section
   correcting the disjointness claim above, keeping the SAME `##
   Per-pattern decision` / `## Evidence` / etc. headings -- and call
   `frob ticket done-report T-0605 --why-file r1.md` again.
3. Observed: the ticket's body now contains the FULL new narrative
   (correct), immediately followed by the ENTIRE original narrative
   (stale, including the disproven claim), both under variants of the
   same H2 headings, with a duplicate `## Per-pattern decision` /
   `## Evidence` / `### Captured claims` block. `git diff` on the ledger
   shows only insertions past the correct section, not a true replace.

## Acceptance

GIVEN a ticket's `## Done report` narrative contains its own `## `
(H2) sub-headings AND `frob ticket done-report --why-file` is called a
second time with revised content WHEN the ledger is re-rendered THEN
the OLD section (heading through true end-of-body / next ticket marker)
is fully replaced by the new one -- no stale sub-section survives
alongside the new report, and no factual claim from a prior round
persists as live (non-historical) text outside an explicitly-labeled
review-round heading the caller wrote intentionally.
 the Done-report heading
 the Done-report heading

Fixed `_done_report_section_end` (src/frob/tickets/_models.py) to stop
treating ANY `## ` line as a Done-report section boundary. It now stops
only at a fixed set of programmatically-written structural headings --
another `## Done report` (existing T-0493 repeated-heading behavior,
unchanged), `## Failure log`, or `## Drop reason` -- via a new shared
`_STRUCTURAL_HEADINGS_AFTER_DONE_REPORT` constant built from two new
public constants, `FAILURE_LOG_HEADING` and `DROP_REASON_HEADING`.
`src/frob/tickets/__init__.py`'s own `_FAILURE_LOG_HEADING` /
`_DROP_REASON_HEADING` (used by `record_failure`/`drop`'s
`_append_to_section` calls) now alias these instead of holding a second
hand-typed copy, so the two can never drift apart.

Previously, any `## ` line INSIDE the narrative text passed via
`--why-file` (e.g. `## Per-pattern decision`, `## Evidence`) was
misread as the end of the Done-report section. On a second
`done-report --why-file` call, this meant `replace_done_report_section`
only overwrote the short intro before that first narrative sub-heading,
leaving the entire prior report (including any factual claim a later
round had disproven) duplicated verbatim just past the corrected one.

Reproduced the exact ticket scenario as a unit test,
`TestDoneReportSectionEndStructuralSentinel.test_narrative_h2_subheadings_do_not_end_the_section`
(tests/test_evidence_integrity.py, the existing D-0x Done-report test
home -- added `tests/test_evidence_integrity.py` to this ticket's scope
via `frob ticket scope T-0848 --add` for this reason): round one writes
a Done report with `## Per-pattern decision` / `## Evidence`
sub-headings; round two writes a corrected report reusing the same
sub-headings plus a `## Reviewer round 1` heading disproving the first
claim. Asserts the corrected narrative is present, the disproven
round-one text is NOT (it used to survive verbatim), and exactly one
`## Done report` / `## Evidence` heading exists in the final body (no
duplicated section).

Hand-verified mutant kill: reverted the sentinel check back to "stop at
any `## ` line" (the pre-fix shape) and reran the new test -- it failed
exactly as the ticket describes, with the disproven round-one text
(`structurally disjoint per-method`) surviving in the post-round-two
body. Restored the fix afterward; reran and confirmed
`tests/test_evidence_integrity.py` (32 passed) and `tests/test_tickets.py`
(115 passed) both pass.

Live sanity check (per dispatch instruction): re-ran
`frob ticket done-report T-0847 --why-file <the same round-1 why-file>`
against T-0847's already-recorded report under this fix. Since that
narrative has no internal `## ` sub-headings, the replace worked
correctly both before and after this fix -- single copy of the body, and
the `

### Changed
```
 docs/modules/gates.md                          |   1 +
 src/frob/app/ticket_runner.py                  | 156 +++++++---
 src/frob/gates/__init__.py                     |  23 ++
 src/frob/tickets/__init__.py                   |  12 +-
 src/frob/tickets/_land.py                      |  22 +-
 src/frob/tickets/_models.py                    |  45 ++-
 tests/test_evidence_integrity.py               |  51 +++-
 tests/test_ticket_land.py                      |  40 +++
 tests/unit/test_ticket_runner_gate_findings.py |  99 ++++++-
 tickets.md                                     | 380 ++++++++++++++++++++++++-
 10 files changed, 774 insertions(+), 55 deletions(-)
```

### Evidence
- `tests/test_evidence_integrity.py::TestDoneReportSectionEndStructuralSentinel::test_narrative_h2_subheadings_do_not_end_the_section` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 0 error(s), 1238 warning(s), 222 waived
- error-findings: none (measured, zero errors)
