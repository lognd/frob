---
id: T-4416
title: 'Profile semantics: rapid=scoped-synchronous, standard=unscoped-synchronous'
state: done
kind: feature
origin: human
created: '2026-09-11'
priority: high
blocked_by:
- T-4413
parent: T-4410
tier: story
sprint: v0.532.0
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
- docs/modules/land-profiles.md
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
- op: add
  glob: docs/modules/land-profiles.md
  reason: 'T-4416: new doc file for rapid=scoped-synchronous/standard=unscoped-synchronous
    semantics -- docs/modules/tickets-landing.md''s profile section is leased by in-progress
    T-3613 (ScopeLeaseConflict), so this ticket documents in a new file instead of
    waiting indefinitely on another agent''s live lease'
  actor: logan
  at: '2026-09-16'
evidence:
- tests/unit/test_doctor.py::TestLandProfilesDocMatchesCode::test_doc_names_rapid_scoped_and_standard_unscoped
- tests/unit/test_doctor.py::TestProfileRecommendation::test_ticket_count_above_threshold_recommends_rapid
- tests/unit/test_doctor.py::TestProfileRecommendation::test_file_count_above_threshold_recommends_rapid
- tests/unit/test_doctor.py::TestProfileRecommendation::test_below_threshold_recommends_nothing
- tests/system/test_cli_scaffold_apply.py::TestScaffoldNewProfileRecommendation::test_new_small_project_prints_no_recommendation
designated_repro_test: null
acceptance:
- text: GIVEN the rapid and standard land profiles WHEN documented THEN rapid is described
    as scoped-synchronous (diff-plus-dependents) and standard as unscoped-synchronous
    (full check), matching their actual post-T-4413 behavior
  evidence:
  - tests/unit/test_doctor.py::TestLandProfilesDocMatchesCode::test_doc_names_rapid_scoped_and_standard_unscoped
- text: GIVEN frob doctor or frob init runs on a repo above a measured size threshold
    (ticket count or file count) WHEN it evaluates land profile THEN it recommends
    rapid, citing the measured cost numbers (25-45 min unscoped check at ~4200 tickets/~1400
    files, T-4408's 50+ min)
  evidence:
  - tests/unit/test_doctor.py::TestProfileRecommendation::test_ticket_count_above_threshold_recommends_rapid
  - tests/unit/test_doctor.py::TestProfileRecommendation::test_file_count_above_threshold_recommends_rapid
- text: GIVEN a repo below the threshold WHEN doctor/init evaluates profile THEN it
    does not force rapid, leaving standard as a reasonable default for small projects
  evidence:
  - tests/unit/test_doctor.py::TestProfileRecommendation::test_below_threshold_recommends_nothing
  - tests/system/test_cli_scaffold_apply.py::TestScaffoldNewProfileRecommendation::test_new_small_project_prints_no_recommendation
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Owner design decision (2026-09-11) plus T-4413's scoped rapid sweep changes what 'rapid' means. Rename or document rapid as scoped-synchronous and make standard the unscoped-synchronous profile for small projects. frob doctor / frob init should recommend rapid above a measured repo size threshold, citing this repo's measured unscoped-check costs (25-45 min at ~4200 tickets/~1400 files; T-4408 land: 50+ min single-thread).

AFFECT001 waiver on src/frob/app/scaffold_runner.py::run (T-4416): this ticket only appends a call to _print_profile_recommendation at the tail of run's new-project branch. docs/modules/app.md#runners' and docs/guides/worktree-pool.md#cli-frob-scaffold-pool-t-0877's documented contract for this runner (dispatch by scaffold_command, apply/pool/new behavior) is unchanged -- the new advisory nudge is covered by the land-profiles.md anchor added alongside it, not a change to either existing doc's content.