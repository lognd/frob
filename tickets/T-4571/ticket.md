---
id: T-4571
title: 'ticket merge-driver state-precedence resolution keeps the loser''s draft id
  line: after a sibling land promotes T-draft-X to T-NNNN on dev, merging dev into
  the draft''s worktree writes tickets/T-NNNN/ticket.md with id: T-draft-X, so every
  ledger verb reports NotFound and land refuses NotCloseable'
state: queued
kind: bug
origin: human
created: '2026-09-19'
priority: high
parent: null
tier: ticket
sprint: v0.535.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.535.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
body_changes:
- mode: set
  reason: coordinator repro
  actor: logan
  at: '2026-09-19'
  old_length: 0
  new_length: 1091
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Repro 2026-09-19: T-draft-b6949eab was promoted to T-4562 by the T-2965 land. The worktree t-draft-b6949eab later merged dev; the ticket merge-driver logged "resolved a single-ticket-file conflict by state precedence (winner=in-progress)" and wrote tickets/T-4562/ticket.md whose frontmatter id: was still T-draft-b6949eab. frob ticket show T-4562 -> NotFound; land -> NotCloseable (evidence and done report were bound under the stale id). Same for T-draft-d56bad34 -> T-4563 and T-draft-db13b6bc -> T-4550.

Fix in the merge driver: the id field is path-derived truth and must always be taken from the directory name (or the land branch's side); evidence/acceptance bindings and the done-report directory must migrate across the promotion.

Acceptance:
GIVEN a draft promoted on the land branch WHEN the draft's worktree merges that branch THEN tickets/T-NNNN/ticket.md carries id: T-NNNN and the worktree's evidence is preserved.
GIVEN a worktree whose tickets/<dir>/ticket.md id disagrees with <dir> WHEN any ledger verb loads it THEN it reports the mismatch by path instead of NotFound.
