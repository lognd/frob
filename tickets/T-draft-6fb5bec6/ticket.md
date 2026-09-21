---
id: T-draft-6fb5bec6
title: Land prepare phase merges the target branch out of tree with land-owned files
  resolved to the target side; pre-commit guard compares against ticket_land_branch
state: queued
kind: feature
origin: human
created: '2026-09-21'
priority: high
blocked_by:
- T-4738
parent: T-5106
tier: ticket
sprint: v0.535.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_land.py
- src/frob/tickets/_land_git_ops.py
- .claude/hooks/**
- tests/ticket_land_suite/**
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
Leaf C2 of T-5106 (~2 pts). Target-branch merge with land-owned files resolved in prepare. Blocked by T-4738.
- prepare merges the target branch (`ticket_land_branch`) into the worktree branch out of tree (a merge-tree over the snapshot, no worktree writes); conflicts on land-owned files (.frob-release.json, CHANGELOG.md, changelog.d, uv.lock, pyproject.toml, frob.lock, ratchet/coverage lock files) resolve to the target branch's side, since land regenerates them; conflicts on tickets/** resolve to the target side except the landing ticket's own dir.
- Any other conflict is the existing merge-conflict refusal, unchanged.
- The T-0731 pre-commit guard compares against literal main (T-5162); this leaf makes it compare against `ticket_land_branch` so a dev merge inside a worktree stops tripping it. Coordinate with T-5162 (absorb or block).
- Replaces the merge half of the coordinator's hygiene.sh. Positive control: a worktree behind dev with a CHANGELOG conflict lands without a hand merge.
