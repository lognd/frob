---
id: T-2735
title: Document T-2721's git-tracked/mirrored waive-audit watermark in docs/modules/app.md
state: queued
kind: docs
origin: human
created: '2026-08-20'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/modules/app.md
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
T-2721 changed `frob.gates._waive_audit_watermark.save_watermark` to commit
the watermark file (now git-tracked at the repo root, not `.frob/`) and
mirror it onto the primary checkout from a worktree.
`docs/modules/app.md#waive-audit-t-2467` (the section `frob:doc` targets
for this module) was NOT updated in T-2721's own change:
`docs/modules/app.md` was held by a live cross-worktree lease (T-2694) for
T-2721's entire duration, so T-2721 could not touch it and waived
AFFECT001 on `save_watermark` citing this ticket.

Update that section to describe: the watermark is now committed in git
(not gitignored per-checkout scratch state), the file lives at the repo
root (`waive-audit-watermark.json`, `.gitignore`-negated like
`rapid-debt.jsonl`), and `save_watermark` mirrors a worktree's write onto
the primary checkout immediately (same shape as T-2563's ledger mirror)
so the fleet sees audit progress without waiting for a land.
