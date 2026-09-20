---
id: T-4506
title: C# end-to-end adapter parity (capability resolver, directive DSL, docs/xref/perf,
  dup/docblock fixture)
state: queued
kind: feature
origin: agent
created: '2026-09-16'
priority: medium
blocked_by:
- T-3232
- T-3856
parent: T-4513
tier: story
sprint: v0.534.0
runs_last: false
milestone: v0.533.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/vet/_capability_csharp.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: v0.533.0
  new_value: v0.534.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-20'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Story: bring C# to the same adapter contract as python/rust/typescript/kotlin/c (mirrors T-1597's non-negotiable bar). Parent for the leaf tickets under it. blocked_by T-3232/T-3234/T-3856 because each is a generic cross-language bug this story's csharp-specific leaves build on top of -- fixing them here would duplicate those tickets, not extend them.

GIVEN a repo with .cs files using capability-relevant APIs, WHEN frob vet runs, THEN it reports the same capability findings a resolver-backed language reports (not just raw needle matches).
GIVEN a .cs file with // frob:doc, // frob:tests, and // frob:todo T-#### directives, WHEN the graph DSL parser runs, THEN each directive is accepted and produces the same obligation-graph edges Python's # directives produce.
GIVEN the frob.docs/frob.xref/frob.perf gaps fixed by T-3232/T-3234/T-3856, WHEN a csharp file is docstring-extracted, xref --lang filtered, or perf hot-graph collected, THEN csharp participates identically to python.

## Unblock log
- 2026-09-16: unblocked by T-3234 -- same: perf coverage deferred with T-3234
