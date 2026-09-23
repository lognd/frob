---
id: T-4672
title: 'SF-01: instrument the SYS/SELFAUDIT slice -- 614,294 telemetry rule fires
  contain zero SYS ids and no one has ever timed check --only sys'
state: queued
kind: feature
origin: agent
created: '2026-09-19'
priority: high
blocked_by:
- T-4112
parent: T-4665
tier: ticket
sprint: null
runs_last: false
milestone: 1.1.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/sys_runner.py
- tests/unit/app/test_sys_runner_telemetry.py
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
body_changes:
- mode: append
  reason: record scope-collision blocker discovered while attempting frob ticket work
    T-4672
  actor: logan
  at: '2026-09-19'
  old_length: 2685
  new_length: 3286
- mode: set
  reason: '2026-09-19: coordinator/owner re-classification -- SF-01 is a DECISION,
    not instrumentation, and is now T-4804. This ticket is re-scoped down to the ONE
    measurement nobody has ever taken (a check --only sys wall-clock), which is an
    input to that decision. The instrumentation and positive-control acceptance criteria
    are withdrawn into T-4804.'
  actor: logan
  at: '2026-09-19'
  old_length: 3286
  new_length: 2542
designated_repro_test: null
acceptance:
- text: Given no 'check --only sys' timing row exists in 31,459 telemetry entries
    and the strata slice has only ever been inferred from an in-process capability_via_site_counts
    measurement, when this lands, then a real end-to-end 'frob check --only sys' wall-clock
    is recorded with more than one sample, with the fleet-load conditions stated alongside
    it and the spread reported rather than a single figure.
  evidence: []
acceptance_amendments:
- op: replace
  index: 1
  old_text: Given .frob/telemetry.jsonl records 614,294 rule fires across 82 rule
    ids of which ZERO start with SYS and SELFAUDIT001 appears once, when this lands,
    then a test running the SYS slice over a fixture tree asserts the emitted telemetry
    names at least one SYS rule id -- a positive control that fails at HEAD c8f56ef10.
  new_text: Given no 'check --only sys' timing row exists in 31,459 telemetry entries
    and the strata slice has only ever been inferred from an in-process capability_via_site_counts
    measurement, when this lands, then a real end-to-end 'frob check --only sys' wall-clock
    is recorded with more than one sample, with the fleet-load conditions stated alongside
    it and the spread reported rather than a single figure.
  reason: '2026-09-19: SF-01 re-classified as a DECISION (T-4804); this ticket keeps
    only the measurement half, so criterion 1 is amended from ''telemetry names a
    SYS rule id'' to the missing wall-clock'
  actor: logan
  at: '2026-09-19'
- op: remove
  index: 3
  old_text: Given there is no 'check --only sys' timing row in 31,459 telemetry rows,
    when the slice runs, then it records a timing row and the done-report states the
    measured wall-clock the epic has been missing.
  new_text: null
  reason: '2026-09-19: SF-01 re-classified as a DECISION (T-4804); the timing criterion
    is now criterion 1, so this duplicate timing criterion is removed'
  actor: logan
  at: '2026-09-19'
- op: remove
  index: 2
  old_text: Given a zero can mean clean, could-not-run, nothing-to-measure or matcher-never-fired,
    when a SYS violation is PLANTED in the fixture, then a test asserts the runner
    reports it -- so a future zero is provably a clean zero.
  new_text: null
  reason: '2026-09-19: SF-01 re-classified as a DECISION (T-4804); planting a positive-control
    SYS violation is instrumentation work that waits on T-4804''s decision about what
    the family should measure, so it is withdrawn from this measurement-only ticket'
  actor: logan
  at: '2026-09-19'
threat: null
component: gates
anchor: false
anchor_reason: null
land_commit: null
---
SF-01, measurement half only. Leaf of story B (T-4665) under epic T-4662.
Story points: 1. IMMEDIATELY DISPATCHABLE -- no blockers.

RE-SCOPED 2026-09-19. This ticket was originally filed as instrumentation for
the SYS/SELFAUDIT family. The coordinator and owner re-classified SF-01 as a
DECISION -- "what should the SYS/SELFAUDIT family measure so that zero fires
means clean rather than measures-nothing" -- now filed as **T-4804** under story
D (T-4667). Do not add telemetry, do not plant positive-control fixtures, and do
not re-tune any rule under this id; all of that waits on T-4804's decision.

WHAT REMAINS HERE: take the one measurement nobody has ever taken.

THE GAP, VERBATIM FROM THE AUDIT'S BOUNDARIES SECTION:
"I did not run `frob check --only sys` end-to-end: telemetry shows `check --json`
at a median of 717s and the fleet is live, so the strata slice is inferred from
the in-process `capability_via_site_counts` measurement, not from a gate
wall-clock. **No one has ever recorded a `check --only sys` timing** -- zero such
rows in 31,459 telemetry entries. That measurement is still missing and the epic
should take it."

SUPPORTING NUMBERS (context, not this ticket's work):
- 614,294 rule fires across 82 rule ids in .frob/telemetry.jsonl; ZERO start
  with SYS; SELFAUDIT001 appears once.
- Container cost for contrast: `check --json` n=145, median 717.1s, max 1684.5s;
  `verify drain-async` n=64, median 1008.5s.
- The in-process proxy: capability_via_site_counts 23.03s cold, 17.83s warm.
- `frob check --ticket` is NOT a speedup (memory/frob-check-cost-model.md), so
  do not substitute it for the real `--only sys` form.

WHY THE NUMBER MATTERS TO THE DECISION
T-4804's option 1 is "keep the family but stop paying for it on every land" --
run it nightly or pre-release instead. That option cannot be costed without
knowing what the slice actually costs per land. This ticket produces that input.

HOW TO TAKE IT HONESTLY
Per memory/coordinator-measurement-discipline.md and the CPU-budget rule in the
standing brief: the box is shared with a serial land, so a slice timed under
fleet load is measuring the load, not the gate. Record the load conditions
alongside the number, take more than one sample, and report the spread rather
than a single figure. Per memory/wrapper-exit-code-is-not-the-work.md, the
deliverable is the recorded timing artifact, not a command that exited 0.

Nothing in src/ changes under this ticket unless emitting the timing row
requires it; if it does, keep it to the timing row alone.
