---
id: T-3226
title: Add filing-provenance field to Ticket schema (which ticket filed a given T-draft-*
  id)
state: queued
kind: feature
origin: human
created: '2026-08-28'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_models.py
- src/frob/tickets/_new_renumber.py
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
found while working T-2878: _pending_draft_ids_after_close (frob ticket close's draft auto-promote sweep) had no data source to determine which ticket filed a given T-draft-* id, so it swept the whole fleet-wide queue. T-2878's fix works around this by parsing the closing ticket's own Done report for an affirmative 'Filed: <id>' claim (reusing TICK006's _tick006_phantom_ids), which is good-enough as an interim signal but is still text-matching prose, not a structural guarantee -- a ticket's Done report could plausibly omit or misstate a Filed: claim with no schema-level check. A real fix needs a field on Ticket (or the draft-minting path in _new_renumber.py::new_ticket) recording the filing ticket's id at draft-creation time, threaded through so any future ownership-scoped draft query (not just close's) can filter on real data instead of parsing prose.