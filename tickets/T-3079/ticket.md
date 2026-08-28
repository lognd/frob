---
id: T-3079
title: 'post-land sweep regression from T-3044: 2 new (rule, file) identit(ies), 2
  finding(s) (LARGE001)'
state: in-progress
kind: bug
origin: agent
created: '2026-08-27'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- strata-core/src/graph/vmodel.rs
- strata-core/src/parse/grammar_core.rs
- tickets.md
- tickets/T-draft-703f9e02/ticket.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tickets.md
  reason: filing the deferred-split follow-up ticket (T-draft-703f9e02) for this sweep-regression
    ticket writes tickets.md and its own ticket.md; both are frob ticket-infra artifacts
    of doing this ticket's work, not unrelated scope creep
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tickets/T-draft-703f9e02/ticket.md
  reason: filing the deferred-split follow-up ticket (T-draft-703f9e02) for this sweep-regression
    ticket writes tickets.md and its own ticket.md; both are frob ticket-infra artifacts
    of doing this ticket's work, not unrelated scope creep
  actor: logan
  at: '2026-08-28'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
findings:
- - LARGE001
  - strata-core/src/graph/vmodel.rs
- - LARGE001
  - strata-core/src/parse/grammar_core.rs
---
The deferred post-land unscoped sweep (T-1684) for T-3044 at commit 51bc8c6ddb492d00af3341e00f7727011e8a961c found 2 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (2), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 2 actual finding(s) across those 2 identit(ies).

New (rule, file) identit(ies) filed here:

- LARGE001  strata-core/src/graph/vmodel.rs
- LARGE001  strata-core/src/parse/grammar_core.rs

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- LARGE001  strata-core/src/graph/vmodel.rs  -> attributed to T-3044 (commit 51bc8c6ddb49, already closed/dropped -- filed below) via strata-core/src/graph/vmodel.rs::ATTR_CODE_REF
- LARGE001  strata-core/src/parse/grammar_core.rs  -> attributed to T-3044 (commit 51bc8c6ddb49, already closed/dropped -- filed below) via strata-core/src/parse/grammar_core.rs::Parser.parse_vmodel_edge -> strata-core/src/parse/grammar_core.rs::Parser.at_keyword

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.