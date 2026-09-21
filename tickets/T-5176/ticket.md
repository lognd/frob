---
id: T-5176
title: ticket merge driver drops worktree-side evidence/acceptance bindings when dev
  rewrites the same ticket file
state: queued
kind: bug
origin: human
created: '2026-09-20'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_merge_driver.py
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
found while landing T-4759 (and 22 sibling worktrees): after 'git merge dev' into a finished worktree, the single-ticket-file merge driver resolves tickets/<id>/ticket.md 'by state precedence (winner=queued)' and the worktree side's top-level evidence: list, per-acceptance evidence lists and designated_repro_test are silently discarded (dev's sprint/mirror commits had rewritten the same file). Measured on 2026-09-20: every one of 23 finished worktrees came out with evidence: [] or no evidence key at all; T-4114/T-4115/T-4073 then refused NotCloseable, bug-kind tickets refused EvidenceConfirmatoryOnly, and each had to be re-recorded from its own 'record evidence' commits. Same driver also dropped T-4912's DOC006 waivers inside ticket bodies. Expected: state precedence picks the frontmatter STATE, but evidence/acceptance/designated_repro_test bindings must be unioned (the worktree side is the only writer of those), never dropped.