---
id: T-3861
title: 'exhaustive-handling family (EXHAUST002/003/004) burn-down: 323 unwaived findings'
state: in-progress
kind: bug
origin: agent
created: '2026-09-05'
priority: medium
parent: null
tier: ticket
sprint: v0.541.0
runs_last: false
milestone: v0.541.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- scripts/fleet_status.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: scripts/fleet_status.py
  reason: EXHAUST burn-down
  actor: logan
  at: '2026-09-20'
body_changes:
- mode: append
  reason: 'BUG002 land refusal: bound evidence killed zero mutants because this leaf''s
    only diff-touched production code is waiver comments, not executable logic

    '
  actor: logan
  at: '2026-09-21'
  old_length: 672
  new_length: 1190
evidence:
- tests/gates_suite/test_compliance.py::TestExhaustiveHandlingGate::test_unresolvable_callee_fires_exhaust003_not_exhaust001
- tests/gates_suite/test_exhaust_burndown_t3861.py::TestExhaustBurndownFleetStatus::test_fleet_status_exhaust003_004_findings_are_all_waived
designated_repro_test: null
evidence_changes:
- old_node: tests/gates_suite/test_compliance.py::TestExhaustiveHandlingGate::test_fleet_status_exhaust003_004_findings_are_all_waived
  new_node: tests/gates_suite/test_exhaust_burndown_t3861.py::TestExhaustBurndownFleetStatus::test_fleet_status_exhaust003_004_findings_are_all_waived
  reason: T-4420 leases tests/gates_suite/test_compliance.py; moved this T-3861 repro
    to its own unleased test module instead
  actor: logan
  at: '2026-09-20'
- old_node: tests/unit/coordinator_suite/test_fleet_worktrees.py::TestLeases::test_reads_lease_records
  new_node: ''
  reason: 'T-4665 BUG002: confirmatory-only, passes at parent dev, not related to
    this ticket''s scripts/fleet_status.py diff'
  actor: logan
  at: '2026-09-21'
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-3861
branch: t-3861
---
T-3844 burn-down: this rule/cluster (EXHAUST002,EXHAUST003,EXHAUST004) carried 323 unwaived warning-level findings on the 2026-09-05 full unscoped 'frob check --no-cache' baseline measured for T-3844 (see that ticket's body for the full histogram). It is intentionally NOT promoted to error by T-3844 -- promoting a rule that still fires reds the build for everyone. This ticket's job: drive the live unwaived finding count for EXHAUST002,EXHAUST003,EXHAUST004 to zero (real fixes and/or reasoned frob:waive entries), then promote EXHAUST002,EXHAUST003,EXHAUST004 from warn to error in frob.toml's [gates.severity] T-1002 managed zone as a follow-up to this same campaign.

frob:no-behavior-change reason="This ticket's diff-touched production file, scripts/fleet_status.py, receives ONLY frob:waive EXHAUST003 comment additions across this leaf -- no executable code line changed (verified: every added line in the diff is a #-prefixed comment). Pure lint-metadata/waiver-comment edit, no runtime behavior differs; BUG002/mutation-kill evidence structurally cannot apply the way it does to a code-path bug fix, per this same T-1616 precedent used by other EXHAUST/WAIVE burn-down leaves."