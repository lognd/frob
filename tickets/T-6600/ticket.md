---
id: T-6600
title: register PRECHECK001-006 in gates _KNOWN_GATE_RULES and src/frob/agent/_precheck.py
  in design/frob.strata
state: queued
kind: docs
origin: human
created: '2026-09-24'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: null
branch: null
scope:
- src/frob/gates/_waive.py
- design/frob.strata
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
found while working T-5642: frob.agent._precheck constructs 6 new rule ids (PRECHECK001..006) that GATERULE001 flags as unregistered in frob.gates._waive._KNOWN_GATE_RULES, and the module's own fs.read/git-subprocess capability (SELFAUDIT001 SYS103/SYS106) is not covered by any design/frob.strata node code= glob, the same gap T-draft-6d585d1b already tracks for frob.agent._brief. Could not fix either within T-5642 itself: src/frob/gates/_waive.py is leased by T-3008 and design/frob.strata is leased by other in-progress tickets. T-5642 carries interim frob:waive directives citing this ticket at each site.