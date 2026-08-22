---
id: T-2887
title: Remove now-inert frob:waive DSL001 follow_up=T-2875 marker in _reap.py
state: dropped
kind: bug
origin: human
created: '2026-08-22'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/process/_reap.py
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
T-2875 fixed frob.graph.dsl._RESERVED_MARKER_VERBS to include callee-raises, so the # frob:callee-raises marker on src/frob/process/_reap.py's libc.prctl(...) call site (arm_parent_death_signal) now parses clean with zero DSL001 findings. The frob:waive DSL001 follow_up="T-2875" comment directly above that line is now dead-waiver debt (T-1614 shape) and should be removed once a scope lease on this file is available -- it was blocked from removal in T-2875 itself by a live cross-worktree lease held by T-2874 on the same file. Verify the underlying marker still parses cleanly (0 DSL001) after removing the waiver.

## Drop reason
- 2026-08-22: T-2874's lease cleared while T-2875 was in flight, so T-2875 removed the frob:waive DSL001 follow_up=T-2875 marker in _reap.py directly instead of re-pointing it -- the work this draft named no longer exists (absorbed by T-2875)
