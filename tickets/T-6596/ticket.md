---
id: T-6596
title: 'TDD001 test-side predicate in _tdd_order.py is still lexical after T-6570:
  unify it with the collector-driven rule in graph.dsl once T-3068 lands'
state: queued
kind: bug
origin: agent
created: '2026-09-26'
priority: medium
parent: T-6570
tier: ticket
sprint: null
runs_last: false
milestone: 0.535.0
flavour: null
due: null
rank: null
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
- src/frob/gates/_tdd_order.py
- src/frob/graph/dsl.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: set
  reason: DOC006 inline waivers (T-draft-7ee140de)
  actor: logan
  at: '2026-09-26'
  old_length: 892
  new_length: 892
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Follow-up to T-6570 (collector-driven test-side detection). T-6570 fixed
`frob.graph.dsl.looks_like_test_path` and `_partition_test_declarations`
but could not touch `src/frob/gates/_tdd_order.py::_looks_like_test_path`
because T-3068 held a live lease on that file; the implementer narrowed
scope instead. TDD001 therefore still decides test-side from the lexical
path rule (lowercase `tests/` part or `test_*.py`), so a Unity
`Assets/Tests/...` NUnit file is still production-shaped for TDD001's
implementation-first ordering check.

Deliver, after T-3068 lands: TDD001 reads the `origin_test_shaped` edge
attr T-6570 stamps (or calls the shared predicate through a layering-
clean seam) and the local duplicate plus its ARCH waiver are deleted.
Positive control: the hullbreach fixture from T-6570's tests run through
TDD001 yields an implementation -> test edge with no ordering finding.
