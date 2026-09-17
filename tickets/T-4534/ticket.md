---
id: T-4534
title: 'Post-land residue from the v0.532.0 lands (T-4413/T-4414/T-4415): 8 uncovered-symbol,
  affect and dup findings'
state: dropped
kind: bug
origin: agent
created: '2026-09-16'
priority: medium
parent: T-4410
tier: ticket
sprint: v0.532.0
runs_last: false
milestone: v0.532.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_models.py
- src/frob/gates/__init__.py
- src/frob/app/check_runner.py
- src/frob/app/ticket_runner/_rapid_sweep.py
- src/frob/check/__init__.py
- src/frob/check/_python.py
- tests/unit/test_ci_self_gate_unscoped.py
- docs/modules/tickets-landing.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'BUG002 structurally untestable via pytest: the defect and fix are both
    frob-check gate/doc-metadata state, not application code a unit test observes'
  actor: logan
  at: '2026-09-16'
  old_length: 657
  new_length: 1423
evidence:
- tests/unit/test_check_scoped_files.py::TestGateConfigFiles::test_repo_wide_gates_constant
- tests/test_check_runner.py::TestApplyTierAAndReverify::test_doc007_finding_fixed_and_reverified_clean
- tests/unit/rapid_sweep_suite/test_window.py::TestWindowStateIo::test_round_trips
- tests/unit/test_check.py::TestCheckResultCounts::test_total_errors_sums_across_results
- tests/unit/test_ci_self_gate_unscoped.py::TestSelfGateIsUnscoped::test_self_gate_step_exists_and_is_named
- tests/unit/test_ci_self_gate_unscoped.py::TestLandVsCiDocumentedSplit::test_both_doc_homes_state_the_split
- tests/unit/test_check_scoped_files.py::TestRunRuffFilesArgv::test_ruff_check_uses_files_not_root
designated_repro_test: null
acceptance:
- text: GIVEN frob check --only gates on dev WHEN run THEN AFFECT001/COV001/COV002/DUP001/DRIFT002
    report zero errors for the eight files this ticket owns
  evidence:
  - tests/unit/test_check_scoped_files.py::TestGateConfigFiles::test_repo_wide_gates_constant
  - tests/test_check_runner.py::TestApplyTierAAndReverify::test_doc007_finding_fixed_and_reverified_clean
  - tests/unit/rapid_sweep_suite/test_window.py::TestWindowStateIo::test_round_trips
  - tests/unit/test_check.py::TestCheckResultCounts::test_total_errors_sums_across_results
  - tests/unit/test_ci_self_gate_unscoped.py::TestSelfGateIsUnscoped::test_self_gate_step_exists_and_is_named
  - tests/unit/test_ci_self_gate_unscoped.py::TestLandVsCiDocumentedSplit::test_both_doc_homes_state_the_split
  - tests/unit/test_check_scoped_files.py::TestRunRuffFilesArgv::test_ruff_check_uses_files_not_root
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Quarantine raised by the post-land sweep on batch (d6cfcaf99, a5be90df4, aa3cb6304) 2026-09-16: AFFECT001 src/frob/gates/_models.py; COV001 src/frob/gates/__init__.py; COV002 on src/frob/app/check_runner.py, src/frob/app/ticket_runner/_rapid_sweep.py, src/frob/check/__init__.py, src/frob/check/_python.py, src/frob/gates/__init__.py; DUP001 tests/unit/test_ci_self_gate_unscoped.py; DRIFT002 docs/modules/tickets-landing.md. The landing tickets were closed by the land before the sweep read the tree, so the changed symbols have no open scope owner. Fix: bind frob:doc / frob:tests / frob:waive edges and re-ack the drifted doc anchor; no behaviour change.

frob:waive BUG002 reason="post-land residue: the defect is a `frob check` GATE finding (AFFECT001/COV001/COV002/DUP001/DRIFT002 firing on already-landed commits with no open scope owner), not application behavior a pytest repro can exercise at the parent commit -- the fix is comment/doc directives (frob:doc, frob:tests, prose) plus one new ticket (T-4533) for a real gap found in frob.graph._resolve.resolve, none of which pytest observes. Repro is the frob check invocation itself: `frob check --only coverage --only drift --only affect_drift --only clones --ticket T-4532 --base dev --files <the 8 scoped files>` reported these 5 rules as errors before this change and reports 0 for them after (see Done report for the exact before/after)."

## Drop reason
- 2026-09-16: duplicate promoted copy of the residue draft T-draft-357dade2, which landed as T-4532; its in-progress lease on src/frob/gates/__init__.py was blocking T-4540
