---
id: T-3083
title: ruff format drift has no pre-commit gate under rapid (T-3060 follow-up)
state: queued
kind: bug
origin: human
created: '2026-08-27'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_land_cmd.py
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
T-3060 investigation: T-3061 added an unconditional pre-land ruff CHECK gate (lint + import-sort) for every profile, closing the two classes that reached main on 2026-08-26. It does not run ruff FORMAT (formatting drift is a distinct ruff subcommand from ruff check) -- override_ratchet still leaves that class uncaught pre-commit under rapid, same shape as the original incident but for a different, cheap, fully auto-fixable rule class. Candidate fix: a small pre-land check scoped to the ticket's own touched .py files that runs 'ruff format --check' and, since this class is deterministic and auto-fixable, applies the fix and continues rather than halting the land -- proportional to the owner's 'does not halt development too badly' constraint, unlike a full sweep restoration.