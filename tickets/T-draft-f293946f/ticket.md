---
id: T-draft-f293946f
title: 'docs: tickets-landing dry-run squash preview contract'
state: queued
kind: docs
origin: human
created: '2026-09-24'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
points: null
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
- docs/modules/tickets-landing.md
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
found while working T-5403: docs/modules/tickets-landing.md's dry-run contract section needs a paragraph describing the new squash-preview pre-commit check (_dry_run_squash_preview_pre_commit_checks, src/frob/tickets/_land.py) -- a clean --dry-run now measures the same T-3324/SYS111/DOC006 findings a real land's _run_pre_commit_checks runs post-squash, via a disposable-worktree preview that is always unwound. Blocked from being done in T-5403 itself: docs/modules/tickets-landing.md's scope lease is held by in-progress T-draft-16f22785 (unrelated land --drain re-exec feature, landing first per coordinator direction).