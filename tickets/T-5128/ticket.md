---
id: T-5128
title: Recovered from T-4689's phantom TICK006 citation of T-5005
state: queued
kind: bug
origin: agent
created: '2026-09-20'
priority: high
parent: null
tier: ticket
sprint: v0.534.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.534.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-20'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Auto-filed by the TICK006 Tier-A fix (T-1544): T-4689's Done report claimed T-5005 was filed, but T-5005 resolves to no block in tickets.md or tickets-archive.md -- a phantom filing trail. The original claim's own surrounding text (the only surviving description of the intended work) is quoted verbatim below; review and refine as needed.

> as the ticket's implicit_scope grant assumed; app.py was not
leased by any other in-progress ticket at the time.

FILED (out of scope, not touched)

T-5005 "record verb/subverb for --help and argparse usage-error
exits" -- argparse's own --help/usage-error SystemExit happens inside
parser.parse_arg