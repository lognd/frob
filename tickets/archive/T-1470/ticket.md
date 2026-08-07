---
id: T-1470
title: 'TEST005 strata sweep: _native_test.py at 30% branch coverage, below floor'
state: done
kind: feature
origin: human
created: '2026-08-02'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/_native_test.py tests/unit/strata/test_native_test.py
- src/frob/strata/_native_test.py
- tests/unit/strata/test_native_test.py
- design/frob.strata
- tests/test_testing.py
- tests/system/test_frob_self_model.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/strata/_native_test.py
  reason: original scope declared as one space-joined string instead of two glob entries
    (malformed at ticket creation); splitting into proper entries. design/frob.strata
    added for the same shared merge-artifact reason as T-1220 (this worktree merged
    main once for the whole series).
  actor: logan
  at: '2026-08-04'
- op: add
  glob: tests/unit/strata/test_native_test.py
  reason: original scope declared as one space-joined string instead of two glob entries
    (malformed at ticket creation); splitting into proper entries. design/frob.strata
    added for the same shared merge-artifact reason as T-1220 (this worktree merged
    main once for the whole series).
  actor: logan
  at: '2026-08-04'
- op: add
  glob: design/frob.strata
  reason: original scope declared as one space-joined string instead of two glob entries
    (malformed at ticket creation); splitting into proper entries. design/frob.strata
    added for the same shared merge-artifact reason as T-1220 (this worktree merged
    main once for the whole series).
  actor: logan
  at: '2026-08-04'
- op: add
  glob: tests/test_testing.py
  reason: 'scope closure: existing frob:tests edges on this modules symbols already
    point into these two files (predating this ticket)'
  actor: logan
  at: '2026-08-04'
- op: add
  glob: tests/system/test_frob_self_model.py
  reason: 'scope closure: existing frob:tests edges on this modules symbols already
    point into these two files (predating this ticket)'
  actor: logan
  at: '2026-08-04'
evidence:
- tests/unit/strata/test_native_test.py::TestSummarize::test_no_gaps_reports_proved
- tests/unit/strata/test_native_test.py::TestSummarize::test_gaps_present_lists_them_instead_of_proved
- tests/unit/strata/test_native_test.py::TestSummarize::test_format_selfconform_one_line_per_violation
- tests/unit/strata/test_native_test.py::TestSummarize::test_format_gaps_empty_is_empty_list
- tests/unit/strata/test_native_test.py::TestRunNativeSysAuditErrorBranches::test_exhaustiveness_error_propagates
- tests/unit/strata/test_native_test.py::TestRunNativeSysAuditErrorBranches::test_selfconform_error_propagates
- tests/unit/strata/test_native_test.py::TestRunNativeSysAuditErrorBranches::test_both_reports_clean_is_proved
designated_repro_test: null
threat: null
component: null
---
Found during T-1415's full-package sweep (w4k-test005 session): src/frob/strata/_native_test.py measures 30% branch coverage (36/57 statements missed, lines 65,74,83-92,110-157) against tests/unit/strata/ as a whole -- well below T-1415's 75/70 floors and the only strata file still below floor after T-1415 closed _audit.py/_compliance.py/_code_binding.py/_crash.py to 100%. No dedicated tests/unit/strata/test_native_test.py exists yet. Needs real behavior-asserting tests for the native audit-invocation path (run_selected wiring, in-process load_design_ids/merge_models/evaluate_exhaustiveness/check_self_conformance composition) -- likely needs mocking around the real design dir or a small fixture design tree.