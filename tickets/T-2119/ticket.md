---
id: T-2119
title: Document T-2071's fact-based root-contamination guard in scaffold.md
state: queued
kind: docs
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- docs/commands/scaffold.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2071 added a second pre-commit/pre-merge-commit guard to install_worktree_lease_hook (keyed on primary-checkout + other-worktrees-exist + non-ledger staged file, not FROB_AGENT). docs/commands/scaffold.md#public-api was out of T-2071's own scope (held by T-1382's live lease on docs/commands/** at the time). Add a short mention of the new guard alongside the existing FROB_AGENT one once that lease frees.