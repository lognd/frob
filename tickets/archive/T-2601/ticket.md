---
id: T-2601
title: Recovered from T-2561's phantom TICK006 citation of T-draft-5e5a0e2b
state: dropped
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
Auto-filed by the TICK006 Tier-A fix (T-1544): T-2561's Done report claimed T-draft-5e5a0e2b was filed, but T-draft-5e5a0e2b resolves to no block in tickets.md or tickets-archive.md -- a phantom filing trail. The original claim's own surrounding text (the only surviving description of the intended work) is quoted verbatim below; review and refine as needed.

> live lease
(T-2377) throughout this session, so widening T-2561's scope onto it
would have been a lease collision, not a legitimate expansion. Filed
T-draft-5e5a0e2b (`docs/modules/gates.md` scope) to add TICK012 (and the
pre-existing CYCLE001 gap found alongside it) once that lease frees up.
DOCEN

## Drop reason
- 2026-08-19: Exact duplicate of T-2590: both are 'Recovered from T-2561's phantom TICK006 citation of T-draft-5e5a0e2b'. Same measurement applies -- TICK012 and CYCLE001 are already present in docs/modules/gates.md's DOCENUM001 enumeration and table (lines 13, 31, 55); 'uv run frob check --only gates --json' shows zero DOCENUM001 findings for gates.md on current main. Dropping as a duplicate finding, not separate work. (absorbed by T-2590)
