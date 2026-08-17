---
id: T-2253
title: Recovered from T-2226's phantom TICK006 citation of T-draft-385de2c7
state: dropped
kind: bug
origin: agent
created: '2026-08-16'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 7ff05545fb72c74f9434ab3de35a12b54cce2076
---
Auto-filed by the TICK006 Tier-A fix (T-1544): T-2226's Done report claimed T-draft-385de2c7 was filed, but T-draft-385de2c7 resolves to no block in tickets.md or tickets-archive.md -- a phantom filing trail. The original claim's own surrounding text (the only surviving description of the intended work) is quoted verbatim below; review and refine as needed.

> rds are re-attempted and confirmed relocated
   once this lands".

2. The 2 DOC011 dangling-`T-draft-*` doc citations: both mappings ARE
   resolved (T-draft-385de2c7 -> T-2188, T-draft-354a6b64 -> T-2172; see
   the filed ticket for the exact git-archaeology evidence -- no live
   promote-mapping a

## Drop reason
- 2026-08-17: duplicate auto-filed TICK006 recovery ticket (T-2226 phantom citation of T-draft-385de2c7), identical to T-2247 (already dropped for the same reason). The real, already-diagnosed fix (2 DOC011 doc-citation rewrites, T-draft-385de2c7->T-2188 and T-draft-354a6b64->T-2172, verified via git archaeology) is owned by T-2237, which has the correct scope (docs/design/gate-semantics-classification.md, docs/guides/coordinator-scripts.md) and is still queued/actionable (absorbed by T-2237)
