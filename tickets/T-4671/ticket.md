---
id: T-4671
title: 'SF-13/SF-02: derive the SYS111 ceiling instead of committing it -- end the
  five-ticket ratchet-race regression chain'
state: queued
kind: bug
origin: agent
created: '2026-09-19'
priority: high
blocked_by:
- T-4668
- T-4669
parent: T-4664
tier: ticket
sprint: v1.1.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_fix_engine_sync.py
- tests/unit/gates/test_fix_engine_ratchet_race.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: v0.536.0
  new_value: v1.1.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-20'
designated_repro_test: null
acceptance:
- text: Given the chain T-4495 -> T-4563 -> T-4596 -> T-4607 -> T-4633 -> T-draft-a62505d4,
    where a ticket bumps accepted_count against a stale dev count and the land then
    refuses with 'grew above the committed ceiling' (reproduced in scratchpad/why-T-4111.txt:111-122,
    resolved only by hand-edit 74f657ef6), when this lands, then a test reproducing
    that race asserts the land pre-commit check does NOT refuse -- a positive control
    that reproduces at HEAD c8f56ef10.
  evidence: []
- text: Given SF-02 measured 138 lock commits in 60 days (2.3/day), 123 also touching
    design/frob.strata, when this lands, then no ticket needs to hand-commit a ceiling
    number for a via-site count the gate can compute itself, and the done-report states
    the new lock commit rate.
  evidence: []
- text: Given the owner is rethinking strata grammar, when the chosen design would
    require a new declaration primitive (the shape T-4248's '(( ratchet ))' asks for),
    then that part is split out as a DECISION under T-4667 and is NOT built in this
    ticket.
  evidence: []
threat: null
component: gates
anchor: false
anchor_reason: null
land_commit: null
---
SF-13 (MEDIUM) and the outcome measure for SF-02 (HIGH). Leaf of story A
(T-4664) under epic T-4662. Story points: 3.

SF-13 EVIDENCE -- the ratchet auto-accept mechanism has regressed FOUR times,
each ticket created by the previous fix's failure mode:
- T-4495 "SYS100 testsuite via-lists enumerate every exec/fs.write test file by
  name" -> introduced the bare-glob auto-accept writer
  (src/frob/strata/_effects.py:1207, `_testsuite_glob_ratcheted_keys`).
- T-4563 "T-4495 regression: the post-land sweep's testsuite-glob ratchet
  auto-accept [writes the root tree]" -> added the `_land_commit_in_progress` gate.
- T-4596 "SELFAUDIT001 SYS111 auto-accept never fires: sys111_findings_touching
  runs in-process, never sees ..." (landed ad9ec4a5e).
- T-4607 -> the SAME `_land_commit_in_progress` guard had to be added to the
  OTHER writer. The docstring at src/frob/gates/_fix_engine_sync.py:1327-1337
  narrates the whole thing and was re-read verbatim by the planner; it says
  "exactly the DirtyMain-blocks-the-next-land shape T-4563 fixed for the OTHER
  writer of this same file, still open here".
- T-4633 (critical, done) "SYS111 ratchet ceilings race every land: a ticket that
  declares a new via site bumps accepted_count against a stale dev count, then
  dev moves and the land refuses with 'grew above the committed ceiling'".
- T-draft-a62505d4 is still open per PENDING.txt:14.

A concrete instance is written up in scratchpad/why-T-4111.txt:111-122: the
second land attempt refused by SELFAUDIT001 SYS111, "grew above the committed
ceiling of 56", resolved only by a hand-edit and an extra commit 74f657ef6
"resync gates fs.read ratchet ceiling for T-4111 land". Two other why-files
record "worked around by" for the same shape.

SF-02 EVIDENCE -- this is what the chain costs: 138 commits to the lock, all 138
within 60 days (2.3/day), 123 of them also touching design/frob.strata, 53
CHANGELOG mentions, and the churn lands on tickets with nothing to do with
strata (T-3411 a cycle-breaking refactor, T-3697 a Claude hook, T-3777 Windows
test fixes, T-3884 a release smoke test -- all four quoted in story A's body).
23 of 88 coordinator why-*.txt files mention the ratchet.

THE SHAPE THE EVIDENCE POINTS AT
Make the ceiling DERIVABLE rather than committed. A number committed by hand
against a moving dev branch is a race by construction; four fixes have now
attacked the symptom. T-4248 ("first-class (( ratchet )) declaration primitive")
and T-3990 ("SYS111 lock: digest the declared via glob list, not just a count")
both ask for the same thing from different directions and should be read first.
NOTE: if the chosen design needs a new declaration PRIMITIVE, that is a grammar
change and must be split out as a DECISION under story D (T-4667) rather than
built here. This leaf's remit is the gate side: derive, compare, and stop
hand-committing the number.

POSITIVE CONTROL (the test that fails today)
A test reproducing T-4633's race: bump accepted_count against a stale base
count, move the base, then run the land pre-commit check -- it must NOT refuse
with "grew above the committed ceiling". That refusal is reproducible at HEAD.

BLOCKED BY A1 (single loader/writer/schema to migrate both writers onto) and A2
(the derivation runs the scan; at 17.8s uncached, deriving on every land is not
affordable until the cache exists).
