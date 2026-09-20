---
id: T-4547
title: rapid land --files scope counts every commit since the MAIN merge-base as touched
  (252 files for a 6-file ticket), so the scoped check is not scoped on dev
state: done
kind: bug
origin: agent
created: '2026-09-16'
priority: critical
parent: T-4410
tier: ticket
sprint: v0.532.0
runs_last: false
milestone: v0.532.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_land_cmd.py
- tests/unit/test_check_scoped_files.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/unit/test_check_scoped_files.py::TestRapidLandFilesWiring::test_land_touched_paths_against_main_includes_unrelated_dev_commit
- tests/unit/test_check_scoped_files.py::TestRapidLandFilesWiring::test_rapid_check_scope_files_includes_touched_and_dependents
designated_repro_test: tests/unit/test_check_scoped_files.py::TestRapidLandFilesWiring::test_land_touched_paths_against_main_includes_unrelated_dev_commit
acceptance:
- text: GIVEN a worktree branched from dev with a 6-file diff WHEN the rapid land
    computes its --files scope THEN the touched set is the diff against the land TARGET
    branch (LandReport.target_branch / ticket_land_branch), i.e. 6 files plus direct
    dependents, never the diff against main
  evidence:
  - tests/unit/test_check_scoped_files.py::TestRapidLandFilesWiring::test_land_touched_paths_against_main_includes_unrelated_dev_commit
- text: GIVEN the target branch is main WHEN computed THEN behaviour is byte-for-byte
    today's
  evidence:
  - tests/unit/test_check_scoped_files.py::TestRapidLandFilesWiring::test_rapid_check_scope_files_includes_touched_and_dependents
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Measured 2026-09-16 in the T-4511 land log: '[+1469.4s] rapid --files scoped to 252 file(s) (252 touched + 0 direct-dependent)' for a ticket whose own diff is 6 files; the synchronous check phase then took 24 minutes, the same as an unscoped check. _rapid_check_scope_files (T-4413) diffs against the historical main, but dev is 200+ commits ahead of main, so every sibling land's files read as touched. Use the resolved land target (T-3787: _resolve_land_target_branch / cfg.ticket_land_branch) as the diff base, the same way evidence/done-report take --base-ref. Also suspicious: 0 direct dependents for 252 files means the affects walk returned nothing; verify the callgraph query actually runs.