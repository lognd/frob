---
id: T-2754
title: ARCH103 _promote_pending_drafts_after_close mixes I/O, string-formatting, and
  6 decision points
state: queued
kind: bug
origin: human
created: '2026-08-20'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_close_cmd.py
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
Surfaced during T-2743's ARCH103 disposition work (found while scoped to a different, named set of ARCH103 sites; out of T-2743's declared scope so not fixed there). _promote_pending_drafts_after_close (src/frob/app/ticket_runner/_close_cmd.py:1338) mixes I/O, string-formatting, and 6 decision points in one body per ARCH103. Needs its own subsystem-owner disposition: either a T-0977-style waiver (if it is genuinely a cohesive orchestration routine, same shape as the many already-waived CLI/IO helpers) or a real decomposition.