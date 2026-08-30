---
id: T-3474
title: may-raise resolver treats a list-comprehension leading expression as preceding
  its own trailing if-clause
state: done
kind: bug
origin: human
created: '2026-08-30'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/arch/_mayraise.py
- src/frob/arch/_normalized.py
- src/frob/arch/_python.py
- tests/unit/test_arch.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/arch/_normalized.py
  reason: Series S measured that the fix needs NormalizedModule to carry module-level
    assignments / comprehension tags; _mayraise.py alone cannot see them
  actor: logan
  at: '2026-08-30'
- op: add
  glob: src/frob/arch/_python.py
  reason: Series S measured that the fix needs NormalizedModule to carry module-level
    assignments / comprehension tags; _mayraise.py alone cannot see them
  actor: logan
  at: '2026-08-30'
- op: add
  glob: tests/unit/test_arch.py
  reason: must-fire/must-stay-quiet unit tests for the comprehension_id correlation
    and adapter extraction
  actor: logan
  at: '2026-08-30'
evidence:
- tests/unit/test_arch.py::TestComprehensionGuardOrdering::test_trailing_if_clause_discharges_its_own_leading_expression
- tests/unit/test_arch.py::TestComprehensionGuardOrdering::test_different_comprehension_ids_do_not_discharge
- tests/unit/test_arch.py::TestComprehensionGuardOrdering::test_comprehension_branch_does_not_discharge_a_non_comprehension_call
- tests/unit/test_arch.py::TestComprehensionGuardOrdering::test_real_proc_scan_corpus_site_has_no_leaked_value_error
- tests/unit/test_arch.py::TestPythonAdapter::test_adapt_tags_comprehension_branch_and_call_with_shared_id
- tests/unit/test_arch.py::TestIsdigitGuardDischarge::test_guarded_int_call_discharges_value_error
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 6a0b1f4f74b204434a0f0dfcd2ccde53cbf1ced1
---
follow-up split off T-2568 (isdigit-guard discharge). src/frob/process/_proc_scan.py::reap_orphaned_forkservers has [int(entry.name) for entry in entries if entry.name.isdigit() and ...] -- the output expr int(entry.name) is TEXTUALLY before the if-clause's isdigit() guard even though it executes AFTER it at runtime per item. T-2568's guard-discharge only accepts a guard branch at or before the call's own line, so it never matches this shape. Needs comprehension-awareness (tag which NormalizedBranch is a comprehension if-clause and which calls are inside the same comprehension's output expr) that the current NormalizedFunction model does not carry. EXHAUST002 finding: src/frob/process/_proc_scan.py:318 (reap_orphaned_forkservers).

## Failure log
- 2026-08-30 attempt 1: Infeasible in declared scope src/frob/arch/_mayraise.py: NormalizedBranch has only (line, condition_text) and NormalizedCall only (callee, line, args) -- neither carries a comprehension tag (which if-clause belongs to which comprehension, which calls sit in that comprehension's output expr). reap_orphaned_forkservers's int(entry.name) (line 368) textually precedes its own guarding if-clause entry.name.isdigit() (line 370) because a comprehension's if-clause is written after the output expr but the model has no field distinguishing this from an unrelated later branch. A safe fix needs comprehension-awareness added to _normalized.py/_python.py (the adapter), both outside T-3474's declared scope; a line-window heuristic inside _mayraise.py alone would not be sound (indistinguishable from an unrelated guard placed after the call).