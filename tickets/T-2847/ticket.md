---
id: T-2847
title: 'LARGE001: src/frob/tickets/_setters.py unwaived after T-2834''s split (1111
  lines)'
state: in-progress
kind: bug
origin: human
created: '2026-08-21'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_setters.py
evidence_scope:
- tests/test_tickets_tiers.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: add no-behavior-change directive before landing
  actor: logan
  at: '2026-08-21'
  old_length: 764
  new_length: 1276
evidence:
- tests/test_tickets_tiers.py::TestSprintShow::test_state_rollup_and_velocity
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2822 waived LARGE001 on src/frob/tickets/_setters.py with T-1651-grade reasoning. T-2834 (the follow-up filed by T-2822 to split its sprint/flow analytics family into _flow.py) landed and removed that waiver along with the split code, but the file is STILL 1111 lines (over the 800-line threshold) and now has no frob:waive LARGE001 directive at all -- confirmed via direct frob.gates._arch.arch_gate() + frob.gates._waive._apply_waivers() re-measurement against a live build_graph snapshot post-T-2834-land. Needs a fresh disposition: either a new T-1651-grade waiver (if the post-split remainder is genuinely cohesive) or a further split. Found while doing the final unscoped re-measurement for the T-2823/T-2824 series, out of scope for both of those tickets.

frob:no-behavior-change reason="comment-only fix -- one fresh frob:waive LARGE001 directive added to src/frob/tickets/_setters.py, zero code lines changed; no defect fix is claimed for the file's logic. Verified via ast.parse on the touched file plus a targeted pytest re-run (24/24 passed, tests/test_tickets_tiers.py + tests/test_tickets_velocity.py setter/sprint/tier/kind/component/priority coverage). BUG002's designated-repro requirement does not apply: there is no behavior to reproduce a failure for."
