---
id: T-4672
title: 'SF-01: instrument the SYS/SELFAUDIT slice -- 614,294 telemetry rule fires
  contain zero SYS ids and no one has ever timed check --only sys'
state: queued
kind: feature
origin: agent
created: '2026-09-19'
priority: high
parent: T-4665
tier: ticket
sprint: v0.536.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/sys_runner.py
- tests/unit/app/test_sys_runner_telemetry.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: Given .frob/telemetry.jsonl records 614,294 rule fires across 82 rule ids
    of which ZERO start with SYS and SELFAUDIT001 appears once, when this lands, then
    a test running the SYS slice over a fixture tree asserts the emitted telemetry
    names at least one SYS rule id -- a positive control that fails at HEAD c8f56ef10.
  evidence: []
- text: Given a zero can mean clean, could-not-run, nothing-to-measure or matcher-never-fired,
    when a SYS violation is PLANTED in the fixture, then a test asserts the runner
    reports it -- so a future zero is provably a clean zero.
  evidence: []
- text: Given there is no 'check --only sys' timing row in 31,459 telemetry rows,
    when the slice runs, then it records a timing row and the done-report states the
    measured wall-clock the epic has been missing.
  evidence: []
threat: null
component: gates
anchor: false
anchor_reason: null
land_commit: null
---
SF-01 (HIGH). Leaf of story B (T-4665) under epic T-4662. Story points: 3.
IMMEDIATELY DISPATCHABLE -- no blockers.

EVIDENCE. Parsing .frob/telemetry.jsonl (31,459 rows) and summing every
rule_counts map: 614,294 rule fires across 82 distinct rule ids. NOT ONE id
starts with SYS. SELFAUDIT001 appears exactly ONCE. Top fires for contrast:
CPLACE002 124,184; CPLACE001 89,963; TICK014 88,050; DOCARCH001 59,362.
79 rule ids of the SYS/SELFAUDIT/REL/PII/THREAT/VMOD/CLAIM families are defined
under src/frob/strata + src/frob/gates/_sys.py; zero appear in telemetry.

Against that: git log --since="60 days ago" -- design/frob.strata = 434 commits
(452 all-time), so >95% of the self-model's lifetime churn happened in the last
60 days and produced ONE recorded finding.

And nobody has ever measured the slice: there is NO `check --only sys` row in
31,459 telemetry rows. The audit could not run one end-to-end either (check
--json median 717s, fleet live), so the strata slice is inferred from an
in-process capability_via_site_counts measurement, never from a gate wall-clock.
The audit explicitly hands that measurement to this epic.

WHY THIS LEAF IS MEASUREMENT FIRST
Per memory/silent-zero-is-the-dominant-bug-class.md, a zero is one of four
things: clean, could-not-run, nothing-to-measure, or matcher-never-fired. Today
we cannot tell which one this zero is. The audit's own caveat is that SYS is a
SELF-CONFORMANCE family, so "zero findings" is partly the INTENDED steady state
-- the friction is the RATIO, not the zero. It also notes that if a gate path
exists that does not emit telemetry, its SYS findings would be invisible to this
finding altogether (SELFAUDIT001's single recorded fire suggests the path IS
instrumented, but that is inference, not proof). Nothing else in story B should
be re-tuned until this leaf can distinguish the four cases.

WHAT TO BUILD
In src/frob/app/sys_runner.py: emit rule_counts telemetry for SYS/SELFAUDIT rule
EVALUATIONS, not only for findings, so an evaluated-and-clean rule is
distinguishable from a never-evaluated one; and record a timing row for the
`--only sys` slice so the epic finally has the wall-clock number nobody has.
Log the evaluated-rule set and the elapsed time at INFO.

POSITIVE CONTROL (the test that fails today)
A test that runs the SYS slice over a fixture tree and asserts the emitted
telemetry contains a row naming at least one SYS rule id. It fails at HEAD:
zero SYS ids exist in 614,294 recorded fires. Per
memory/positive-control-or-it-proves-nothing.md, add a second test that PLANTS a
genuine SYS violation in the fixture and asserts the runner reports it -- so a
future zero is provably a clean zero.
