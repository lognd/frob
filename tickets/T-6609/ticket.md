---
id: T-6609
title: done-report scoped check runs with --files (empty list) instead of unscoped,
  so a refresh never captures a TICK015 identity added post-hoc
state: queued
kind: bug
origin: human
created: '2026-09-27'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
flavour: null
due: null
rank: null
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
- src/frob/app/ticket_runner/_verify.py
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
found while working T-6569 (crunk-ba addendum): frob.app.ticket_runner._verify's check_gate_findings/check_gates spawn builds its argv with --files <touched files>; when the touched-file list resolves empty (files=0) at done-report refresh time (T-0257/T-0211 crunk incident, T-6569 body addendum 2026-09-27), the spawned frob check checks zero files and never re-captures a fresh TICK015 (or any other) finding, so a refresh-and-retry loop after a ClaimDivergence refusal fails identically. Needs the files=0 case to fall back to an unscoped check (or refuse the refresh loudly) instead of silently checking nothing.