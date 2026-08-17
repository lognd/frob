---
id: T-2238
title: Recovered from T-2226's phantom TICK006 citation of T-draft-0bd874ac
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
land_commit: null
---
Auto-filed by the TICK006 Tier-A fix (T-1544): T-2226's Done report claimed T-draft-0bd874ac was filed, but T-draft-0bd874ac resolves to no block in tickets.md or tickets-archive.md -- a phantom filing trail. The original claim's own surrounding text (the only surviving description of the intended work) is quoted verbatim below; review and refine as needed.

> this
   CRLF corruption. Filed T-2239 (high) for the .gitattributes
   glob fix; acceptance [3] there is "T-2226's two still-unresolved
   T-draft-0bd874ac records are re-attempted and confirmed relocated
   once this lands".

2. The 2 DOC011 dangling-`T-draft-*` doc citations: both mappi

## Drop reason
- 2026-08-16: Phantom TICK006 auto-filing, verified junk. Created from T-2226's Done report prose, which discussed T-draft-0bd874ac because repairing records naming that dead draft id WAS the ticket's subject. That draft was promoted to T-2195 (state=done); zero scope entries, no content. The landing agent independently assessed it as benign. Generator ticketed as T-2243.
