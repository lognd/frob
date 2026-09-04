---
id: T-3784
title: fix win32 DEPR005/cycle-runner path separator mismatches
state: in-progress
kind: bug
origin: human
created: '2026-09-04'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/gates/test_deprecated_baseline.py
- src/frob/gates/_debt_deprecated.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/gates/test_deprecated_baseline.py
  reason: scope was accidentally a single space-joined glob string; split into two
    proper entries
  actor: logan
  at: '2026-09-04'
- op: remove
  glob: src/frob/gates/_debt_deprecated.py tests/unit/gates/test_deprecated_baseline.py
  reason: correct the malformed single-glob scope into two proper entries
  actor: logan
  at: '2026-09-04'
- op: add
  glob: src/frob/gates/_debt_deprecated.py
  reason: correct the malformed single-glob scope into two proper entries
  actor: logan
  at: '2026-09-04'
body_changes:
- mode: append
  reason: 'BUG002 waiver: win32-only defect, cannot repro on Linux CI'
  actor: logan
  at: '2026-09-04'
  old_length: 328
  new_length: 733
evidence:
- tests/unit/gates/test_deprecated_baseline.py::TestDepr005ViolationsGrowth::test_same_count_as_baseline_does_not_fire
- tests/unit/gates/test_deprecated_baseline.py::TestDepr005ViolationsGrowth::test_growth_beyond_baseline_fires_at_the_right_file_and_line
- tests/unit/gates/test_deprecated_baseline.py::TestDepr005ViolationsGrowth::test_two_baselined_symbols_each_evaluated_independently
- tests/unit/gates/test_deprecated_baseline.py::TestDeprecatedCurrentReferencesImportGating::test_unrelated_same_name_call_in_non_importing_file_is_excluded
- tests/unit/gates/test_deprecated_baseline.py::TestDeprecatedCurrentReferencesImportGating::test_call_through_import_alias_is_reported
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
win32 CI: DEPR005 growth-comparison tests fail because _build_deprecated_ref_index keys files with bare str(Path) (backslash-separated on win32) while the baseline lock file stores POSIX-separated keys, so current counts never match baseline counts and DEPR005 spuriously fires on every referencing file. Part of win32 CI drain.

frob:waive BUG002 reason="win32-only defect confirmed via winrun; on Linux the designated repro test passes at both the parent commit and the fix commit because bare str(Path) already produces POSIX separators on Linux -- the path-separator mismatch this ticket fixes only manifests when the process runs on win32, so no Linux-repro-at-parent-commit test can demonstrate the failure this fix addresses"