---
id: T-2354
title: Recovered from T-2344's phantom TICK006 citation of T-2348
state: dropped
kind: bug
origin: agent
created: '2026-08-17'
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
Auto-filed by the TICK006 Tier-A fix (T-1544): T-2344's Done report claimed T-2348 was filed, but T-2348 resolves to no block in tickets.md or tickets-archive.md -- a phantom filing trail. The original claim's own surrounding text (the only surviving description of the intended work) is quoted verbatim below; review and refine as needed.

> c/frob/gates/_wire.py: `_wire001_cli_dest_violations` (a genuine,
  self-admitted (c) candidate the new gate found) waived in-file with
  `follow_up="T-2348"` rather than silently allowlisted.
- docs/modules/gates.md: rule-catalog row + full `## LEXCHECK001 (T-2344)`
  section, `_KNOWN_GATE_RULES` f

## Drop reason
- 2026-08-17: T-2348 is a real, filed ticket (now landed at 31c1e197), verified via ticket show and git grep against tickets.md; T-2344's follow_up citation was never phantom. Same stale phantom-citation pattern T-2350 root-caused and closed (T-2351 fixed the underlying disqualified Tier-A revert mechanism); nothing independent to fix here.
