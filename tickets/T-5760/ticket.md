---
id: T-5760
title: 'TIER005: sprint stays a pure filter -- refuse a sprint label as parent and
  lint historical slips'
state: queued
kind: feature
origin: human
created: '2026-09-24'
priority: medium
blocked_by:
- T-5749
parent: T-5748
tier: ticket
sprint: ledger-tiers
runs_last: false
milestone: v0.536.0
flavour: null
due: null
rank: null
points: 2
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
- src/frob/gates/_tickets_gate.py
- src/frob/tickets/_new_renumber.py
- src/frob/gates/_waive.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_new_renumber.py
  reason: B5 needs a write-time belt refusal (parent naming a sprint label) wired
    through _new_renumber.py, and TIER005's gate-rule-id registration in _waive.py
    -- same split A4/T-5765 established
  actor: logan
  at: '2026-09-24'
- op: add
  glob: src/frob/gates/_waive.py
  reason: B5 needs a write-time belt refusal (parent naming a sprint label) wired
    through _new_renumber.py, and TIER005's gate-rule-id registration in _waive.py
    -- same split A4/T-5765 established
  actor: logan
  at: '2026-09-24'
triage_changes:
- field: points
  old_value: null
  new_value: '2'
  reason: ticket sizing
  actor: logan
  at: '2026-09-24'
- field: points
  old_value: '2'
  new_value: '2'
  reason: ticket sizing
  actor: logan
  at: '2026-09-24'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
TIER005: sprint stays a pure filter -- refuse at write time a parent that names a sprint label (belt) and add a lint-only check flagging any that slipped in historically (suspenders). A sprint cannot close anything and cannot be closed. Lands at WARN.

Positive control: a ticket with parent pointing at a sprint label is refused at write time; TIER005 flags a historical one; zero findings on a clean ledger stays quiet.

Doc page: docs/modules/tickets-lifecycle.md

Tree: /tmp/claude-1000/-home-logan-projects-frob/f95beb8e-97d5-4dd4-9038-3ffab8a3a4ea/scratchpad/LEDGER-TIERS-TREE.md (sections 2 and 5; section 5 overrides).
