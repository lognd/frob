---
id: T-4407
title: 'verify_runner.py exceeds LARGE001 800-line threshold: extract coverage-lock
  auto-commit helpers'
state: in-progress
kind: feature
origin: human
created: '2026-09-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/verify_runner.py
- src/frob/app/_verify_coverage_lock.py
- docs/modules/tickets-verify-sweep.md
- src/frob/app/_verify_rapid_debt.py
- docs/modules/verify-rapid-debt-visibility.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/modules/tickets-verify-sweep.md
  reason: auto-commit helper doc lives here, moving into new module
  actor: logan
  at: '2026-09-10'
- op: add
  glob: src/frob/app/_verify_rapid_debt.py
  reason: second cohesive split (rapid-debt helpers) needed to actually clear the
    800-line threshold with margin
  actor: logan
  at: '2026-09-10'
- op: add
  glob: docs/modules/verify-rapid-debt-visibility.md
  reason: second cohesive split (rapid-debt helpers) needed to actually clear the
    800-line threshold with margin
  actor: logan
  at: '2026-09-10'
triage_changes:
- field: kind
  old_value: bug
  new_value: feature
  reason: behavior-preserving module split to clear LARGE001; no diff-touched behavior
    exists for BUG002 mutation evidence (land refusal 04:17 EvidenceConfirmatoryOnly)
  actor: logan
  at: '2026-09-11'
evidence:
- tests/unit/verify/test_verify_runner.py::TestLiveRapidDebt::test_no_baseline_is_live
- tests/unit/verify/test_verify_runner.py::TestLiveRapidDebt::test_later_baseline_clears
- tests/unit/verify/test_verify_runner.py::TestLiveRapidDebt::test_uncovered_stays_live
kind_history:
- 2026-09-11 bug->feature evidence=3 done_report=yes
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
LARGE001: src/frob/app/verify_runner.py is 874 lines, over the 800-line
threshold, and will red the next ubuntu self-gate.

Extract the coverage-lock auto-commit helpers T-4041 added
(_COVERAGE_LOCK_REL, _auto_commit_coverage_lock) into a cohesive new
private module, e.g. src/frob/app/_verify_coverage_lock.py, and have
verify_runner.py import and call it. No behavior change; existing tests
must still pass unmodified (only their frob:tests binding target moves
if the symbol's qualified path changes). Re-measure line count after the
split to confirm it clears 800 with margin.