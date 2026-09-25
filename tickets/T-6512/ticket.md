---
id: T-6512
title: retire scripts/fleet_status.py in favor of frob coord status
state: queued
kind: docs
origin: human
created: '2026-09-24'
priority: medium
parent: null
tier: ticket
sprint: coord-surface
runs_last: false
milestone: v0.536.0
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
- scripts/fleet_status.py
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
found while working T-draft-4ad886c1: frob coord status (COORD-1) supersedes fleet_status.py's queue/quarantine/worktree/lease reporting, but the script has 31 dependent test/script files (wait_for_land_slot.py imports land_process_rows/_parse_land_argv_ticket_id directly) -- retiring it is a separate, larger leaf than COORD-1's 5pt budget allows. Port the remaining live consumers onto frob.coord/_status.py's primitives, then delete the script and its dependent tests.