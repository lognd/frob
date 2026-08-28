---
id: T-3195
title: A done-report recording zero evidence and zero changed files reached main while
  the work sat unlanded
state: in-progress
kind: bug
origin: human
created: '2026-08-27'
priority: medium
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
scope_changes:
- op: add
  glob: src/frob/tickets/_done_report.py
  reason: the done-report write path that produced the hollow record
  actor: logan
  at: '2026-08-27'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED 2026-08-27 while recovering T-3157's stranded work.

Main carried a done-report for T-3157 that recorded, verbatim:

    ### Changed
    (no changed files detected)

    ### Evidence
    (no evidence recorded)

    ### Captured claims
    - tests: 0 passed (from 0 evidence id(s))

Meanwhile the ticket's REAL work -- `tests/system/test_fleet_status_ground_truth.py`,
361 lines, 11 passing evidence ids across four claim classes -- sat unlanded in
`.claude/worktrees/t-3157` for hours. The truthful done-report existed only in
that worktree. The two collided as an add/add conflict when the land finally ran
(resolved in favour of the evidenced copy; the real work landed at
`fece5760372a8beaad5eab5b1fe93825a643e3d3`).

WHAT THIS MEANS. A ticket can reach main in `state=done` carrying a done-report
that affirmatively records NO evidence and NO changed files, while the work it
describes is not on main at all. Nothing refused that. The report is not silent
about being empty -- it says "(no evidence recorded)" in plain text -- and it was
committed anyway.

THIS IS THE SILENT-ZERO CLASS IN ITS MOST LOAD-BEARING FORM. A zero-evidence
done-report and a genuinely-evidence-free ticket render identically. Everything
downstream that reads done-reports (attribution, sweeps, the ledger, any future
audit of what shipped) reads the hollow record as fact.

RELATED BUT DISTINCT from the already-known failure where a timed-out land
writes `state=done` with zero code on main: here the land did not obviously time
out, and the hollow REPORT is the artifact, not just the state field. Also
distinct from T-3128's land-proof misattribution, where a real fix landed under
a sibling's commit. Check both before assuming a shared cause; do not merge
these into one theory without evidence.

DETERMINE FIRST (measure, do not assume):
  - How the hollow report reached main. Which code path writes a done-report
    with "(no evidence recorded)" and commits it? Is it a legitimate template
    write that was never filled, a close that ran in the wrong tree, or a
    partial land?
  - Whether this is a one-off or a population. COUNT the done-reports currently
    on main that record zero evidence AND zero changed files while their ticket
    is `done`. That count is the whole story: one is an incident, many is a
    systemic accounting hole. Report the number either way.

WHAT TO BUILD, once the population is known:
  - Refuse to commit a done-report that records zero evidence and zero changed
    files for a ticket transitioning to `done`, UNLESS the ticket is legitimately
    evidence-free (docs/chore kinds under a light profile, or a ticket closed
    with a recorded no-behaviour-change front door). That exemption is real and
    must not be papered over -- it needs its own must-stay-quiet fixture.
  - Make the refusal name the ticket, the empty fields, and the fix.

DO NOT SOLVE THIS BY DELETING OR REWRITING EXISTING HOLLOW REPORTS. They are
evidence of what happened. If any are found, leave them and file what they show.

ACCEPTANCE
- A stated count of hollow done-reports currently on main, with the method used
  to count them.
- The write path that produced T-3157's identified.
- A guard refusing the hollow-report-plus-done combination, with a must-fire
  fixture and a must-stay-quiet fixture for the legitimately evidence-free case.
- No existing done-report content deleted or rewritten under this ticket.
