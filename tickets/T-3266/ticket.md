---
id: T-3266
title: 136 done-reports claim '0 passed (from 0 evidence id(s))' while their ticket
  carries real evidence (T-3244 has 47)
state: queued
kind: bug
origin: human
created: '2026-08-28'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_done_report.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED 2026-08-28 across every `state: done` ticket carrying a done-report on
main (2,590 of them):

    136 done-reports (5.3%) render
        "- tests: 0 passed (from 0 evidence id(s))"
    while the ticket's OWN `evidence:` list is non-empty.

Worst example: T-3244 carries 47 evidence ids and its done-report claims 0.
Others in the sample include T-2988 (8), T-2409 (7), T-3044 (6), T-2999 (6),
T-2919 (5), T-1654 (4). The scan script is at
/tmp/claude-1000/-home-logan-projects-frob/79c6402d-b401-4652-bea7-f81df1be9322/scratchpad/scan.py
-- re-run it, do not trust this count second-hand.

HOW IT WAS FOUND. A worktree (t-3065) still held an uncommitted copy of
T-3033's done-report reading "tests: 2 passed (from 2 evidence id(s))" while
main's landed copy of the same report read "0 passed (from 0 evidence id(s))".
The ticket has both evidence ids and a real land commit with real changed files.
The truthful number existed and did not reach main.

THIS IS NOT THE KNOWN HOLLOW-REPORT DEFECT, AND MUST NOT BE MERGED WITH IT. In
that one (T-3157) the ticket genuinely had no evidence and no changed files, and
the ledger itself was empty. Here the LEDGER IS CORRECT -- evidence ids are
recorded, the land commit is real, the changed-files section of the same report
is accurate. Only the rendered "Captured claims" line is wrong. Check both
before assuming a shared cause.

LIKELY MECHANISM, NOT VERIFIED -- MEASURE IT: the claims line appears to be
rendered from a snapshot taken BEFORE evidence is attached, so it reports the
state at report-generation time rather than at close time. The t-3065 evidence
supports this: the worktree's later-generated copy has the right numbers and
main's earlier one does not. Confirm the ordering in the code rather than
assuming it.

WHY IT MATTERS. The done-report is the human-readable record of what shipped.
Anything auditing "was this work tested" -- a person, a future agent, a release
review -- reads a confident "0 passed (from 0 evidence id(s))" and concludes the
ticket shipped untested. For 136 tickets that conclusion is false, and the
ticket file sitting beside it says so. This is the project's dominant defect
class in the shipped record: a measurement that was taken and then reported as
absent.

It also defeats the guard built for the hollow-report case, which keys on "(no
evidence recorded)" -- "0 passed (from 0 evidence id(s))" is a different string
with the same meaning and passes straight through.

DO NOT FIX THIS BY BULK-REWRITING THE 136 EXISTING REPORTS. They are the
evidence of what happened, and a mass rewrite of landed historical artifacts is
exactly the move that makes an incident unreconstructable. Fix the renderer so
new reports are correct; then decide separately, and say what you decided,
whether historical reports get a correction pass or are left as-is with the
defect recorded.

ACCEPTANCE
- The render-ordering mechanism identified with evidence, not a plausible story.
- New done-reports render the claims line from the ticket's evidence at CLOSE
  time; a must-fire fixture (a ticket with N evidence ids renders N, not 0) and
  a must-stay-quiet fixture (a genuinely evidence-free ticket still renders 0).
- The hollow-report guard extended to catch this string too, or a stated reason
  why it should not.
- A re-run of the scan showing the count for NEW reports is zero. The historical
  136 may remain; say explicitly which choice was made.
