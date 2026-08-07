---
id: T-0848
title: 'tickets CLI: done-report --why-file duplicates the ENTIRE prior report body
  when narrative contains its own H2 headings'
state: done
kind: bug
origin: human
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- tests/test_evidence_integrity.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_evidence_integrity.py
  reason: 'Evidence test for the _done_report_section_end fix lives in

    tests/test_evidence_integrity.py (the existing D-0x done-report test

    home), not under src/frob/tickets/** which the ticket''s original scope

    declared.

    '
  actor: logan
  at: '2026-07-23'
evidence:
- tests/test_evidence_integrity.py::TestDoneReportSectionEndStructuralSentinel::test_narrative_h2_subheadings_do_not_end_the_section
designated_repro_test: null
threat: null
component: null
---
`_done_report_section_end` (src/frob/tickets/_models.py) computes the end
of an EXISTING `## Done report` section by scanning forward for the next
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