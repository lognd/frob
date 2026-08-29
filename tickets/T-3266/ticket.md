---
id: T-3266
title: 136 done-reports claim '0 passed (from 0 evidence id(s))' while their ticket
  carries real evidence (T-3244 has 47)
state: done
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
- src/frob/tickets/_evidence.py
- src/frob/tickets/_models.py
- tests/test_tickets.py
- docs/modules/tickets-data-storage.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_evidence.py
  reason: wire the T-3266 stale-claims guard into the existing close-time structural
    check (_evidence.py), add its TicketError variant (_models.py), and cite the doc
    anchor + regression tests
  actor: logan
  at: '2026-08-28'
- op: add
  glob: src/frob/tickets/_models.py
  reason: wire the T-3266 stale-claims guard into the existing close-time structural
    check (_evidence.py), add its TicketError variant (_models.py), and cite the doc
    anchor + regression tests
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/test_tickets.py
  reason: wire the T-3266 stale-claims guard into the existing close-time structural
    check (_evidence.py), add its TicketError variant (_models.py), and cite the doc
    anchor + regression tests
  actor: logan
  at: '2026-08-28'
- op: add
  glob: docs/modules/tickets-data-storage.md
  reason: wire the T-3266 stale-claims guard into the existing close-time structural
    check (_evidence.py), add its TicketError variant (_models.py), and cite the doc
    anchor + regression tests
  actor: logan
  at: '2026-08-28'
body_changes:
- mode: append
  reason: 'scope correction: the class is stale-count not zero (61 wrong non-zero
    cases the original scan missed), and a liveness measurement showing 6 of the 15
    newest reports wrong including T-3247 landed today'
  actor: logan
  at: '2026-08-28'
  old_length: 3442
  new_length: 6315
evidence:
- tests/test_tickets.py::TestStaleClaimsGuard::test_zero_claims_with_real_evidence_refused
- tests/test_tickets.py::TestStaleClaimsGuard::test_wrong_nonzero_claims_refused
- tests/test_tickets.py::TestStaleClaimsGuard::test_matching_claims_not_flagged
- tests/test_tickets.py::TestStaleClaimsGuard::test_no_claims_section_not_flagged
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


SCOPE CORRECTION AND A LIVENESS MEASUREMENT, both taken 2026-08-28 after this
ticket was filed. The defect is BROADER and MORE ACTIVE than the original body
says.

1. THE CLASS IS "STALE COUNT", NOT "ZERO". The original filing counted only
reports claiming `0 passed (from 0 evidence id(s))` against a non-empty
evidence list. Re-measuring for ANY disagreement between the claims line and
the ticket's own evidence count, across all 1,917 done tickets that carry a
claims line:

    claims match evidence      1719
    claims = 0, evidence > 0    137
    claims non-zero but WRONG    61
    TOTAL WRONG                 198   (10.3%)

Example of the previously-missed shape: T-3230 has 6 evidence ids and its
report claims 3. A fix that special-cases zero would leave those 61 wrong.
Fix the rendering so the number is derived from the ticket's evidence at close
time, whatever the number is.

2. IT IS LIVE AND FREQUENT, NOT HISTORICAL. Of the 15 most recently written
done-reports, SIX are wrong:

    T-3247   evidence=9    report_claims=0     (landed 2026-08-28)
    T-3244   evidence=47   report_claims=0
    T-2988   evidence=8    report_claims=0
    T-3255   evidence=1    report_claims=0
    T-2940   evidence=1    report_claims=0
    T-2992   evidence=1    report_claims=0
    T-3230   evidence=6    report_claims=3     (partial shape)

T-3247 landed roughly an hour before this measurement, with 9 evidence ids
rendered as 0. So this is not a legacy artifact being cleaned up -- it is
producing a wrong record on roughly 40% of current lands, including tickets
that shipped enforcement gates.

That matters for the owner's current goal. A PyPI release review that reads
done-reports to answer "what shipped and was it tested" will get a false
answer for one ticket in ten, and the failure is biased toward UNDER-reporting
evidence, so the record looks worse than reality rather than better. Both
directions are bad but this one invites redoing work that was already done.

3. WHAT DOES NOT CHANGE. The ledger is still correct -- evidence ids are
recorded, land commits are real. Only the rendered claims line is wrong. Do not
merge this with the hollow-report defect (T-3157), where the ledger itself was
empty. And still do NOT bulk-rewrite the 198 historical reports; fix the
renderer, then decide separately and say what you decided.

ACCEPTANCE ADDITION
- The must-fire fixture must cover BOTH shapes: a ticket with N evidence ids
  rendering 0, and one rendering a wrong non-zero count.
- Re-run the scan after the fix and report the three counts above. The
  "claims non-zero but WRONG" bucket must be zero for new reports, not just the
  zero bucket.
- Scan scripts used for these numbers are at
  /tmp/claude-1000/-home-logan-projects-frob/79c6402d-b401-4652-bea7-f81df1be9322/scratchpad/scan3.py
  -- re-run rather than trusting the counts second-hand.