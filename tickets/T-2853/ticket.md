---
id: T-2853
title: 'LARGE001: src/frob/tickets/_leases.py unwaived after T-2833''s split (3182
  lines)'
state: in-progress
kind: bug
origin: human
created: '2026-08-22'
priority: medium
parent: T-2375
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_leases.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: record no-behavior-change rationale before landing, same shape as T-2847/T-2828
  actor: logan
  at: '2026-08-22'
  old_length: 1062
  new_length: 1611
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2822 waived LARGE001 on src/frob/tickets/_leases.py with T-1651-grade reasoning, naming _leases.py as one of two files (with _setters.py) with a genuine investigated seam filed as a follow-up rather than split there. T-2833 split the worktree-sweep family (sweep_worktrees/remove_worktree) out into frob.tickets._worktree_sweep and landed (76865828e), removing the old waiver along with the split code. The remainder is still 3182 lines (nearly 4x the 800-line threshold) and carries NO frob:waive LARGE001 directive at all -- confirmed via direct frob.gates._arch.arch_gate() plus frob.gates._waive._apply_waivers() re-measurement against a live build_graph() snapshot. Needs a fresh disposition: either a new T-1651-grade waiver reflecting the CURRENT post-split shape, or a further split if a real seam remains. Same pattern T-2847 already fixed for _setters.py after T-2834's split -- read T-2847's diff/Done report as template. Found while doing T-2831's final unscoped re-measurement (T-2831 cannot promote LARGE001 to ERROR while this file is unwaived).

frob:no-behavior-change reason=comment-only fix -- one fresh frob:waive LARGE001 directive added to src/frob/tickets/_leases.py, zero code lines changed; no defect fix is claimed for the file's logic. Verified via ast.parse on the touched file plus a targeted pytest re-run of tests/test_ticket_leases.py (identical 6 pre-existing failures reproduced independently on unmodified main; a lease/commit-focused subset of 10 node ids passed clean). BUG002's designated-repro requirement does not apply: there is no behavior to reproduce a failure for.