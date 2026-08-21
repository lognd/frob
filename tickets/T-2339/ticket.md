---
id: T-2339
title: Recovered from T-2324's phantom TICK006 citation of T-2332
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
Auto-filed by the TICK006 Tier-A fix (T-1544): T-2324's Done report claimed T-2332 was filed, but T-2332 resolves to no block in tickets.md or tickets-archive.md -- a phantom filing trail. The original claim's own surrounding text (the only surviving description of the intended work) is quoted verbatim below; review and refine as needed.

> s OWN fixed code against the live root.
    before: commits since watermark: 586 (oldest unverified 577455s old)
    round:  status=red, filed_ticket=T-2332, advanced_watermark=true,
            119 queue entries compacted
    after:  commits since watermark: 13
One round dropped the gap from 586 to

## Drop reason
- 2026-08-17: premise already dead: T-2332 is not phantom -- it exists at tickets/T-2332/ticket.md (a real, filed, later self-dropped sweep-regression ticket), so this is a false phantom-citation report. The generating mechanism (TICK006 auto-filer racing a just-created sibling ticket at land time) was investigated directly under T-2350 and DROPPED there as no-longer-reproducing on current main once T-2351 landed (T-2350's own drop reason: reproduced the flagged disqualified-Tier-A-revert mechanism directly and it now SURVIVES, covered by the existing regression test test_uncommitted_in_scope_edit_survives_a_disqualified_tier_a_revert). Nothing left here to fix.
