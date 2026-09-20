---
id: T-4416
title: 'Profile semantics: rapid=scoped-synchronous, standard=unscoped-synchronous'
state: queued
kind: feature
origin: human
created: '2026-09-11'
priority: high
blocked_by:
- T-4413
parent: T-4410
tier: story
sprint: v0.535.0
runs_last: false
milestone: v0.532.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/cli_doctor*
- src/frob/app/cli_init*
- src/frob/doctor.py
- src/frob/app/doctor_runner.py
- src/frob/app/scaffold_runner.py
- tests/unit/test_doctor.py
- tests/unit/test_doctor_runner_t1276.py
- tests/system/test_cli_scaffold_apply.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/app/ticket_runner/_land_cmd.py
  reason: not edited; deliverables are docs/doctor/init only, avoids T-3613 lease
    collision
  actor: logan
  at: '2026-09-16'
- op: add
  glob: src/frob/doctor.py
  reason: 'T-4416: real modules -- brief notes scope globs cli_doctor*/cli_init* do
    not exist; actual doctor/scaffold live in src/frob/doctor.py, src/frob/app/doctor_runner.py,
    src/frob/app/scaffold_runner.py'
  actor: logan
  at: '2026-09-16'
- op: add
  glob: src/frob/app/doctor_runner.py
  reason: 'T-4416: real modules -- brief notes scope globs cli_doctor*/cli_init* do
    not exist; actual doctor/scaffold live in src/frob/doctor.py, src/frob/app/doctor_runner.py,
    src/frob/app/scaffold_runner.py'
  actor: logan
  at: '2026-09-16'
- op: add
  glob: src/frob/app/scaffold_runner.py
  reason: 'T-4416: real modules -- brief notes scope globs cli_doctor*/cli_init* do
    not exist; actual doctor/scaffold live in src/frob/doctor.py, src/frob/app/doctor_runner.py,
    src/frob/app/scaffold_runner.py'
  actor: logan
  at: '2026-09-16'
- op: add
  glob: tests/unit/test_doctor.py
  reason: 'T-4416: real modules -- brief notes scope globs cli_doctor*/cli_init* do
    not exist; actual doctor/scaffold live in src/frob/doctor.py, src/frob/app/doctor_runner.py,
    src/frob/app/scaffold_runner.py'
  actor: logan
  at: '2026-09-16'
- op: add
  glob: tests/unit/test_doctor_runner_t1276.py
  reason: 'T-4416: real modules -- brief notes scope globs cli_doctor*/cli_init* do
    not exist; actual doctor/scaffold live in src/frob/doctor.py, src/frob/app/doctor_runner.py,
    src/frob/app/scaffold_runner.py'
  actor: logan
  at: '2026-09-16'
- op: add
  glob: tests/system/test_cli_scaffold_apply.py
  reason: 'T-4416: real modules -- brief notes scope globs cli_doctor*/cli_init* do
    not exist; actual doctor/scaffold live in src/frob/doctor.py, src/frob/app/doctor_runner.py,
    src/frob/app/scaffold_runner.py'
  actor: logan
  at: '2026-09-16'
triage_changes:
- field: sprint
  old_value: v0.532.0
  new_value: v0.535.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
designated_repro_test: null
acceptance:
- text: GIVEN the rapid and standard land profiles WHEN documented THEN rapid is described
    as scoped-synchronous (diff-plus-dependents) and standard as unscoped-synchronous
    (full check), matching their actual post-T-4413 behavior
  evidence: []
- text: GIVEN frob doctor or frob init runs on a repo above a measured size threshold
    (ticket count or file count) WHEN it evaluates land profile THEN it recommends
    rapid, citing the measured cost numbers (25-45 min unscoped check at ~4200 tickets/~1400
    files, T-4408's 50+ min)
  evidence: []
- text: GIVEN a repo below the threshold WHEN doctor/init evaluates profile THEN it
    does not force rapid, leaving standard as a reasonable default for small projects
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Owner design decision (2026-09-11) plus T-4413's scoped rapid sweep changes what 'rapid' means. Rename or document rapid as scoped-synchronous and make standard the unscoped-synchronous profile for small projects. frob doctor / frob init should recommend rapid above a measured repo size threshold, citing this repo's measured unscoped-check costs (25-45 min at ~4200 tickets/~1400 files; T-4408 land: 50+ min single-thread).