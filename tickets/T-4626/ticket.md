---
id: T-4626
title: 'post-land residue (auto-filed by the coordinator dispose loop): COV002:tests/unit/rapid_sweep_suite/test_dispose.py
  COV002:tests/unit/rapid_sweep_suite/test_filing.py'
state: in-progress
kind: bug
origin: human
created: '2026-09-19'
priority: high
parent: null
tier: ticket
sprint: v0.533.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/rapid_sweep_suite/test_dispose.py
- tests/unit/rapid_sweep_suite/test_filing.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/rapid_sweep_suite/test_dispose.py
  reason: COV002 residue named exactly these two test files in the auto-filed ticket
    title
  actor: logan
  at: '2026-09-20'
- op: add
  glob: tests/unit/rapid_sweep_suite/test_filing.py
  reason: COV002 residue named exactly these two test files in the auto-filed ticket
    title
  actor: logan
  at: '2026-09-20'
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.533.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-20'
body_changes:
- mode: append
  reason: T-4626 land refused BUG002 (confirmatory-only) because this fix is a comment-directive-only
    annotation with no behavior change
  actor: logan
  at: '2026-09-20'
  old_length: 0
  new_length: 267
evidence:
- tests/unit/rapid_sweep_suite/test_dispose.py::TestAutoDisposeFiledFindings::test_leaves_quarantine_raised_when_other_findings_remain_undisposed
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---


frob:no-behavior-change reason="COV002 residue: adding a frob:ticket comment directive to re-anchor a changed test symbol to an open ticket is a lint-metadata-only change, no runtime behavior differs; the bound evidence legitimately passes at both dev and the fix."