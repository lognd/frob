---
id: T-draft-05300afe
title: 'EXHAUST003/004 warning drain needs may-raise resolver coverage for common
  stdlib/builtin callees, not per-site waivers: 383 findings on dev are unresolvable-callee
  noise'
state: queued
kind: bug
origin: human
created: '2026-09-20'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/arch/_mayraise.py
- src/frob/gates/_exhaustive_handling.py
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Baseline 2026-09-20 (frob check --base dev): EXHAUST003 275, EXHAUST004 108. The T-3861 burn-down agent probed scripts/fleet_status.py (56 findings) against frob.arch._mayraise.compute_may_raise: every leaked type traces to an ordinary stdlib or builtin call (Path.is_dir, str.strip, sorted, dict.get) absent from the curated raiser tables, so the callee is unresolvable and the gate fires by construction. T-1402 moved this shape out of EXHAUST001 into EXHAUST003 but left it as warning noise; draining it with per-def frob:waive lines (56 in one file) hides the measurement gap instead of fixing it. Fix: extend the raiser tables with curated may-raise sets for the common stdlib surface (pathlib, str, dict, list, sorted, os.path, json) and mark builtins that cannot raise on well-typed input as resolved-empty; re-measure; then T-3861 drains only the true residue. Found while coordinating the warning drain.