---
id: T-draft-98186c7b
title: 'frob ticket land --drain crashes after each landed entry: _LandReportShim
  lacks the ticket_id that _print_land_proof reads'
state: queued
kind: bug
origin: human
created: '2026-09-21'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_land_cmd.py
- tests/unit/test_land_default_queue.py
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
drain_next lands an entry then _print_land_proof reads report.ticket_id to look up _LAST_CLAIMS_OUTCOME / _LAST_ORPHAN_EVIDENCE_OUTCOME / _LAST_BUDGET_DEFERRALS, but _LandReportShim (constructed in _land_cmd.py to stand in for the real LandReport since QueueEntry only carries commit_sha and final_id) never sets ticket_id, so it raises AttributeError after every landed entry and a multi-entry drain lands one ticket per invocation instead of draining the whole queue.