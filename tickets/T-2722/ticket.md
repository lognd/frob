---
id: T-2722
title: 'post-land sweep regression from an unattributed source (sweep spawned by T-1614):
  1 new (rule, file) identit(ies), 2 finding(s) (TICK006)'
state: done
kind: bug
origin: agent
created: '2026-08-20'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tickets.md
- tickets/T-1614/done-report.md
- rapid-debt.jsonl
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tickets/T-1614/done-report.md
  reason: 'TICK006 fix: correct T-1614''s Done report to name the post-renumber real
    ids instead of the pre-renumber draft ids'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: rapid-debt.jsonl
  reason: rapid profile debt bookkeeping auto-appended by frob ticket close
  actor: logan
  at: '2026-08-20'
- op: add
  glob: rapid-debt.jsonl
  reason: rapid profile debt bookkeeping auto-appended by frob ticket close
  actor: logan
  at: '2026-08-20'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
The deferred post-land unscoped sweep (T-1684) for an unattributed source (sweep spawned by T-1614) at commit 977be5a9056430b8b01805f029eb8a6360d5a43b found 1 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (1), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 2 actual finding(s) across those 1 identit(ies).

New (rule, file) identit(ies) filed here:

- TICK006  tickets.md

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.