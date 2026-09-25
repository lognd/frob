---
id: T-5771
title: 'Docs: ledger tiers -- milestone tier, story flavour, due/rank, TIER001-006
  family across tickets docs, ticket-kinds-states guide and vmodel'
state: queued
kind: docs
origin: human
created: '2026-09-24'
priority: medium
blocked_by:
- T-5749
- T-5751
- T-5780
- T-5774
- T-5770
- T-5757
- T-5763
- T-5760
- T-5755
- T-5758
parent: T-5748
tier: ticket
sprint: ledger-tiers
runs_last: false
milestone: v0.536.0
flavour: null
due: null
rank: null
points: 5
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
- docs/guides/extending/ticket-kinds-states.md
- docs/strata/vmodel.md
- docs/modules/tickets-data-storage.md
- docs/modules/tickets-lifecycle.md
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: docs/modules/tickets*.md
  reason: narrow the wildcard to the three actual files this leaf touches, avoiding
    an unrelated agent's lease on docs/modules/tickets-landing.md
  actor: logan
  at: '2026-09-25'
- op: add
  glob: docs/modules/tickets-data-storage.md
  reason: narrow the wildcard to the three actual files this leaf touches, avoiding
    an unrelated agent's lease on docs/modules/tickets-landing.md
  actor: logan
  at: '2026-09-25'
- op: add
  glob: docs/modules/tickets-lifecycle.md
  reason: narrow the wildcard to the three actual files this leaf touches, avoiding
    an unrelated agent's lease on docs/modules/tickets-landing.md
  actor: logan
  at: '2026-09-25'
- op: add
  glob: docs/modules/tickets.md
  reason: narrow the wildcard to the three actual files this leaf touches, avoiding
    an unrelated agent's lease on docs/modules/tickets-landing.md
  actor: logan
  at: '2026-09-25'
triage_changes:
- field: points
  old_value: null
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-24'
- field: points
  old_value: '5'
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-25'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Update docs/modules/tickets-data-storage.md, tickets-lifecycle.md, tickets.md, docs/guides/extending/ticket-kinds-states.md and docs/strata/vmodel.md for the new milestone tier, story flavour, due/rank fields, the TIER001-006 family, --with-ticket, and the retirement of kind: invariant.

Positive control: the repo's doc-edge closure check (frob check doc drift) reports zero drift against the touched code paths.

Doc page: this leaf IS the doc leaf

Tree: /tmp/claude-1000/-home-logan-projects-frob/f95beb8e-97d5-4dd4-9038-3ffab8a3a4ea/scratchpad/LEDGER-TIERS-TREE.md (sections 2 and 5; section 5 overrides).

## Unblock log
- 2026-09-24: unblocked by T-draft-3661879e -- 2026-09-24: dangling draft id; the land runner promoted this blocker to its real T-#### id without rewriting the edge, real-id edge re-added via frob ticket block
- 2026-09-24: unblocked by T-draft-9570bf46 -- 2026-09-24: dangling draft id; the land runner promoted this blocker to its real T-#### id without rewriting the edge, real-id edge re-added via frob ticket block
- 2026-09-24: unblocked by T-draft-58029dd5 -- 2026-09-24: dangling draft id; the land runner promoted this blocker to its real T-#### id without rewriting the edge, real-id edge re-added via frob ticket block
- 2026-09-24: unblocked by T-draft-08ef9199 -- 2026-09-24: dangling draft id; the land runner promoted this blocker to its real T-#### id without rewriting the edge, real-id edge re-added via frob ticket block
- 2026-09-24: unblocked by T-draft-50f4484a -- 2026-09-24: dangling draft id; the land runner promoted this blocker to its real T-#### id without rewriting the edge, real-id edge re-added via frob ticket block
