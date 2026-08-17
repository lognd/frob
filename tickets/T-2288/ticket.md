---
id: T-2288
title: 'Recover three confirmed stranded lands: T-2097 (t-2097), T-1479 (t1539-series),
  T-1238 explore slice (532799ac)'
state: queued
kind: bug
origin: agent
created: '2026-08-17'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: given branch t-2097, when its T-2097 work is landed, then T-2097 is terminal
    on main and git show --stat confirms the test fix arrived
  evidence: []
- text: given branch t1539-series, when its T-1479 work is landed, then the frob map
    --json daemon proxy feature is present on main
  evidence: []
- text: given commit 532799ac, when T-1238's explore slice is landed or explicitly
    re-scoped, then T-1238's state on main matches its Done report rather than reading
    queued
  evidence: []
- text: given all three are resolved, when frob ticket reconcile runs, then none of
    these three branches is reported as carrying unlanded work
  evidence: []
threat: null
component: tickets
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED 2026-08-17 (coordinator, read-only via git plumbing). Three
specimens of the exact leak class T-1934 exists to catch -- finished work
committed on a branch, never landed to main -- confirmed present today:

1. `t-2097` -- T-2097 is Done-reported, evidence-recorded and CLOSED on the
   branch (commits ab4ec71b3 Done report, 7230c4352 close, 532c28bea rapid
   close debt). Carries `fix(tests): assert --json CLI payload via caplog,
   not capsys` (c85b21124) plus tests/unit/test_check_budget.py changes.
   Not on main.

2. `t1539-series` -- T-1479 is finalized and closed on the branch
   (74c56ea77). Carries `feat(serve): wire frob map --json through the
   daemon proxy` (c30906ec4), a real feature, plus ticket updates for
   T-1479 and T-1807. Not on main.

3. `532799aca feat(cli): frob explore verb group + regrouping design
   (T-1238)` -- verified NOT an ancestor of main. T-1238's own ticket.md on
   main still reads `state: queued` while its Done report describes the
   slice as implemented and merged. This is the epic's entire first slice.

MISATTRIBUTION NOTE (feeds T-2287): `frob ticket reconcile` reported these
branches under the id **T-1238**, not under T-2097 / T-1479. The
directive-anchored signal names whichever id it greps out of blob text
rather than the id whose ledger state actually disagrees, so even its TRUE
positives point at the wrong ticket. An operator following the report to
T-1238 would never find T-2097's or T-1479's stranded work.

RECOVERY CONSTRAINT: do NOT land these while a dispatch fleet is running.
Concurrent lands each spawn their own `frob check` and thrash each other
past the shell cap. Land them one at a time, serially, verifying each with
`git show --stat` against the ticket's declared scope -- LAND-PROOF checks
ancestry, not content, so an ancestry pass is not evidence the ticket's own
code arrived. Re-measure the error floor before and after, since these
branches diverged long ago and their doc/test/waiver edges may have been
invalidated by intervening refactors.
