---
id: T-4482
title: frob.doctor.ImportSourceStatus (T-4459) missing from the exports policy
state: done
kind: bug
origin: agent
created: '2026-09-14'
priority: critical
parent: null
tier: ticket
sprint: v0.531.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/doctor.py
- src/frob/exports*
- tests/unit/test_exports.py
- src/frob/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/__init__.py
  reason: registering ImportSourceStatus as public API requires editing src/frob/__init__.py's
    import+__all__ list, the same file every other DoctorReport-sibling export already
    lives in
  actor: logan
  at: '2026-09-14'
evidence:
- tests/unit/test_exports.py::TestFrobExportsPolicyResidue::test_all_nine_packages_report_zero_missing_symbols
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
CI run 34817719845 (main 316b99eec), ubuntu+macOS: tests/unit/test_exports.py::TestFrobExportsPolicyResidue::test_all_nine_packages_report_zero_missing_symbols fails: "frob-exports still reports missing symbols: {'src/frob': ['frob.doctor.ImportSourceStatus']}". T-4459 added the public dataclass ImportSourceStatus to src/frob/doctor.py without registering it in the exports policy (the frob-exports registry / __all__ contract the test measures). Fix: register the symbol the way the policy expects (read `frob exports --help` and the test to find the registry file), or make it private if it is not meant to be public API, and re-run `frob exports` plus the test. Sprint v0.531.0 (CI green blocker).