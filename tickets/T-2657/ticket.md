---
id: T-2657
title: Recovered from T-2615's phantom TICK006 citation of T-draft-5d1d5de0
state: queued
kind: bug
origin: agent
created: '2026-08-19'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
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
Auto-filed by the TICK006 Tier-A fix (T-1544): T-2615's Done report claimed T-draft-5d1d5de0 was filed, but T-draft-5d1d5de0 resolves to no block in tickets.md or tickets-archive.md -- a phantom filing trail. The original claim's own surrounding text (the only surviving description of the intended work) is quoted verbatim below; review and refine as needed.

> md` fragment or its CHANGELOG.md line --
those are data artifacts outside this ticket's declared scope
(`src/frob/release/_fragments.py` only). Filed T-draft-5d1d5de0 for
that cleanup now that the generator is fixed and won't recreate it.

Positive controls verified by test (all in `tests/test_relea