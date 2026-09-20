---
id: T-4670
title: 'SF-05: ratchet drift report -- 45 units of accumulated slack and 3 dead entries
  are invisible to a monotone-only gate'
state: queued
kind: feature
origin: agent
created: '2026-09-19'
priority: medium
blocked_by:
- T-4668
parent: T-4664
tier: ticket
sprint: v1.1.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/strata/_ratchet_drift.py
- tests/unit/strata/test_ratchet_drift.py
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
- text: Given the committed lock has 7 keys under their ceiling (total slack 45) and
    3 entries with no measured grant (cli::env, serve::eval, tickets_ledger::eval)
    at HEAD c8f56ef10, when this lands, then a test asserting the LIVE lock has zero
    slack and zero dead entries exists as the standing regression -- a positive control
    that fails today at 45 and 3.
  evidence: []
- text: Given the lock is loose and not breached (0 keys over ceiling, 0 unlocked
    at HEAD), when the reporter runs, then it reports slack and dead entries only
    and changes no gate verdict; making slack a failure is deferred to T-4671's derivable-ceiling
    design.
  evidence: []
threat: null
component: strata
anchor: false
anchor_reason: null
land_commit: null
---
SF-05 (HIGH). Leaf of story A (T-4664) under epic T-4662. Story points: 2.

EVIDENCE, measured capability_via_site_counts at HEAD c8f56ef10 against the
committed `entries`:

    over ceiling:        0
    unlocked (no entry): 0
    under ceiling:       7   -> TOTAL SLACK 45
       testsuite::fs.read   209/232     testsuite::exec          301/312
       gates::fs.write       33/40      testsuite::eval           25/26
       testsuite::fetch_url   2/3       testsuite::install-hook    1/2
       testsuite::deserialize 2/3
    lock entries with no measured grant (DEAD): 3
       cli::env, serve::eval, tickets_ledger::eval

So 45 new capability sites -- 23 of them fs.read in the test suite, 11 exec --
can be added today with SYS111 saying nothing at all. This is structural, not
accidental: src/frob/strata/_effects.py:983-1046 states the design intent that
"a via-list may SHRINK freely", and the ratchet never re-tightens after a shrink.

IMPORTANT FRAMING (from the audit's "found NO friction" section): the lock is
LOOSE, not BROKEN. Zero keys are over ceiling and zero are unlocked at HEAD.
Do not file this as a breach.

WHAT TO BUILD
A drift reporter in a new `src/frob/strata/_ratchet_drift.py`: given the measured
counts and the lock, report slack per key, total slack, and dead entries. Report
only -- whether slack becomes a FAILURE, or the ratchet re-tightens on shrink, is
a gate-semantics choice that belongs to A4's derivable-ceiling design, not here.
This leaf exists so the number is visible before anyone decides what to do
about it.

POSITIVE CONTROL (the test that fails today)
A test asserting the reporter finds exactly the 7 under-ceiling keys and the 3
dead entries named above against a fixture lock, plus a test asserting zero
slack and zero dead entries against the LIVE committed lock -- which fails today
at 45 and 3. The live-tree assertion is the one that must fail at HEAD; keep it
as the standing regression once the lock is retightened.

BLOCKED BY A1 (SF-03): the reporter must read the lock through A1's single
loader, or it will read the shadow top-level keys and report drift that is
itself an artifact of the double-write bug.
