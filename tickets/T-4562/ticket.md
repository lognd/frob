---
id: T-4562
title: docs/guides/extending/comment-dsl-directives.md lists seven walkers; csharp,
  java, bash, cuda and zig are wired in COMMENT_TYPES but undocumented
state: queued
kind: docs
origin: agent
created: '2026-09-17'
priority: low
parent: T-4513
tier: ticket
sprint: v0.533.0
runs_last: false
milestone: v0.533.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/guides/extending/comment-dsl-directives.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: GIVEN docs/guides/extending/comment-dsl-directives.md WHEN read THEN its walker
    list matches frob.lang._extract.COMMENT_TYPES exactly, proven by a doc test or
    a frob:enumerates directive
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found by the T-4507 implementer 2026-09-17: the guide's 'seven walkers' list omits csharp, java, bash, cuda and zig although all are registered in src/frob/lang/_extract.py COMMENT_TYPES. Regenerate the list from the table or bind it with frob:enumerates so it cannot drift.