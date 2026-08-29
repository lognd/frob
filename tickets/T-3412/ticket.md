---
id: T-3412
title: 'frob ticket scope: adding a doc FILE to scope does not subsume its own anchors,
  drowning closure warnings'
state: queued
kind: bug
origin: human
created: '2026-08-29'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_scope.py
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
Filed from T-3404's own investigation (found while measuring the
--reason-collapse defect, not fixed there per instruction). After
`frob ticket scope --add 'docs/guides/coordinator-scripts.md'`, scope
closure still emitted 272 warnings of the form "doc anchor
docs/guides/coordinator-scripts.md#X describes
docs/guides/coordinator-scripts.md#X in
'docs/guides/coordinator-scripts.md#X', not in scope -- consider --add
'docs/guides/coordinator-scripts.md#X'".

A glob covering the whole file should cover its own anchors (an anchor
is a location WITHIN that file, not a separate path); as written, the
advice is unfollowable at any reasonable scale (one --add per anchor)
and trains operators to ignore closure warnings entirely, which
defeats the warning's purpose.

WHAT TO BUILD: scope closure's anchor-coverage check should treat a
scope glob that matches a doc file's own path as covering every
#anchor within that same file, not just the bare file path. Needs its
own measurement of the closure-check code path (likely in
src/frob/tickets/_scope.py or a doc-coverage helper it calls) before
fixing.
