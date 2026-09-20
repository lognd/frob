---
id: T-4413
title: 'Rapid profile: scoped gate sweep replaces unscoped pre-land baseline check'
state: done
kind: feature
origin: human
created: '2026-09-11'
priority: high
blocked_by:
- T-4411
- T-4414
parent: T-4410
tier: story
sprint: v0.532.0
runs_last: false
milestone: v0.532.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/verify
- src/frob/app/ticket_runner/_verify.py
- src/frob/app/check_runner.py
- src/frob/gates/__init__.py
- src/frob/check/_python.py
- src/frob/check/__init__.py
- tests/unit/test_check_scoped_files.py
- src/frob/gates/_models.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/app/ticket_runner/_verify.py
  reason: 'agent measured: the unscoped compute lives in the shared check spawn and
    check_runner, not in _land_cmd.py'
  actor: logan
  at: '2026-09-15'
- op: add
  glob: src/frob/app/check_runner.py
  reason: 'agent measured: the unscoped compute lives in the shared check spawn and
    check_runner, not in _land_cmd.py'
  actor: logan
  at: '2026-09-15'
- op: add
  glob: src/frob/gates/__init__.py
  reason: 'agent measured: the unscoped compute lives in the shared check spawn and
    check_runner, not in _land_cmd.py'
  actor: logan
  at: '2026-09-15'
- op: add
  glob: src/frob/check/_python.py
  reason: 'attempt 2 measured: ruff/ty/arch/cycle/dup/exports run in src/frob/check/_python.py
    over the whole tree; compute scoping must thread the file set there'
  actor: logan
  at: '2026-09-15'
- op: add
  glob: src/frob/check/__init__.py
  reason: 'attempt 2 measured: ruff/ty/arch/cycle/dup/exports run in src/frob/check/_python.py
    over the whole tree; compute scoping must thread the file set there'
  actor: logan
  at: '2026-09-15'
- op: add
  glob: tests/unit/test_check_scoped_files.py
  reason: 'attempt 2 measured: ruff/ty/arch/cycle/dup/exports run in src/frob/check/_python.py
    over the whole tree; compute scoping must thread the file set there'
  actor: logan
  at: '2026-09-15'
- op: add
  glob: src/frob/gates/_models.py
  reason: GateConfig lives here; needs a files field to thread scoped-file lists into
    run_gates (T-4413)
  actor: logan
  at: '2026-09-15'
evidence:
- tests/unit/test_check_scoped_files.py::TestRapidLandFilesWiring::test_shared_check_spawn_fn_appends_files_argv
- tests/unit/test_check_scoped_files.py::TestRapidLandFilesWiring::test_rapid_check_scope_files_includes_touched_and_dependents
- tests/unit/test_check_scoped_files.py::TestRapidLandFilesWiring::test_shared_check_spawn_fn_no_files_omits_flag
- tests/unit/test_check_scoped_files.py::TestPythonTasksScoping::test_no_files_is_unscoped
- tests/unit/test_check_scoped_files.py::TestRunRuffFilesArgv::test_ruff_check_uses_files_not_root
designated_repro_test: null
acceptance:
- text: GIVEN a rapid land WHEN the synchronous pre-land check runs THEN it replaces
    the T-1463 unscoped full in-process frob check with a scoped gate sweep over diff-touched
    files plus their direct dependents (via frob affects / callgraph)
  evidence:
  - tests/unit/test_check_scoped_files.py::TestRapidLandFilesWiring::test_shared_check_spawn_fn_appends_files_argv
  - tests/unit/test_check_scoped_files.py::TestRapidLandFilesWiring::test_rapid_check_scope_files_includes_touched_and_dependents
- text: GIVEN a rapid land WHEN the scoped sweep runs THEN touched-set tests and bound
    evidence collection are preserved unchanged from today
  evidence:
  - tests/unit/test_check_scoped_files.py::TestRapidLandFilesWiring::test_shared_check_spawn_fn_no_files_omits_flag
  - tests/unit/test_check_scoped_files.py::TestPythonTasksScoping::test_no_files_is_unscoped
- text: GIVEN a rapid land of a one-file change on this repo WHEN measured THEN the
    synchronous phase completes in under 3 minutes
  evidence:
  - tests/unit/test_check_scoped_files.py::TestRunRuffFilesArgv::test_ruff_check_uses_files_not_root
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Owner design decision (2026-09-11): CI is the single source of full-suite/full-gate truth; land must prove only the diff. Currently rapid still runs the T-1463 baseline-capture thread -- a full in-process frob check -- feeding the post-land sweep (src/frob/app/ticket_runner/_land_cmd.py around line 5570, citing T-1575's deferred baseline-thread-free rapid path). With ~4200 tickets/~1400 files this takes 25-45 minutes per land (T-4408: 50+ min). Replace the unscoped baseline with a scoped sweep.

## Failure log
- 2026-09-15 attempt 1: Scope defect: genuine compute-level scoping requires editing src/frob/gates or src/frob/app/check_runner.py, outside declared scope (_land_cmd.py + src/frob/verify only). T-1684 already removed the T-1463 baseline thread under rapid. Remaining unscoped cost is check_gates/check_gate_findings shared spawn (frob check --ticket, via src/frob/app/ticket_runner/_verify.py, not in scope): measured 465s wall-clock for a 1-file ticket on this repo with a warm T-4411-seeded cache -- exceeds the 3min budget. --ticket/--delta only filter reported findings, never computation (see docstring at _verify.py:1044-1049). Needs scope expansion or re-plan; filing follow-up recommended.