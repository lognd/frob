---
id: T-2343
title: Recovered from T-2323's phantom TICK006 citation of T-draft-2e335e20
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
Auto-filed by the TICK006 Tier-A fix (T-1544): T-2323's Done report claimed T-draft-2e335e20 was filed, but T-draft-2e335e20 resolves to no block in tickets.md or tickets-archive.md -- a phantom filing trail. The original claim's own surrounding text (the only surviving description of the intended work) is quoted verbatim below; review and refine as needed.

> till exactly the 2 originally scoped, plus 5 more in
tests/unit/verify/test_watermark.py (unrelated, out of this ticket's
declared scope) -- filed as T-draft-2e335e20 residue rather than expanding scope
mid-ticket.

docs/design/registry/capability-via-ratchet.lock.json: bumped 3 entries,
each indivi

## Drop reason
- 2026-08-17: duplicate: TICK006 auto-filed this from stale residue of an earlier failed T-2323 land attempt (a since-deleted draft, T-draft-2e335e20); the real, correct residue ticket for tests/unit/verify/test_watermark.py's undeclared capability effects is T-2340, filed directly from the same worktree session
