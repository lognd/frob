---
id: T-1976
title: Recovered from T-1944's phantom TICK006 citation of T-draft-4a627425
state: dropped
kind: bug
origin: agent
created: '2026-08-10'
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
land_commit: null
---
Auto-filed by the TICK006 Tier-A fix (T-1544): T-1944's Done report claimed T-draft-4a627425 was filed, but T-draft-4a627425 resolves to no block in tickets.md or tickets-archive.md -- a phantom filing trail. The original claim's own surrounding text (the only surviving description of the intended work) is quoted verbatim below; review and refine as needed.

> ft-8d6e958c (CLI wiring for demote_to_evidence_only, outside
this ticket's declared scope since the CLI parser tree lives outside
src/frob/tickets/); T-draft-4a627425 (add this ticket's and T-1946's doc
sections to docs/modules/tickets.md once T-1967's live lease on that
file frees -- could not comm

## Drop reason
- 2026-08-10: recovered content already landed: both doc sections (T-1946 at tickets.md:3573, T-1944 at tickets.md:3624) exist with valid frob:describes/frob:enumerates directives on real symbols; the other quoted item (ft-8d6e958c CLI wiring) was noted as out of this ticket's own scope; nothing outstanding to do
