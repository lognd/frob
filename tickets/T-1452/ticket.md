---
id: T-1452
title: 'strata: design argument-level may scoping (may KIND of TARGET)'
state: queued
kind: feature
origin: human
created: '2026-08-02'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- docs/strata/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
T-1440 parent: argument-level `may` scoping follow-up (design sketch item
5, explicitly deferred to documentation-only by T-1440's own acceptance
plan): e.g. `may "env.read" of "FROB_*"` narrowing WHICH env vars, fs
paths, or net hosts a grant covers, not just which FILES (`via`) may
exercise it. Natural follow-up once `via` itself has real migrated usage
(T-1440's sibling migration ticket) to learn argument-scoping shapes
from. Not designed in detail yet -- this ticket is a placeholder for that
design pass, not a ready-to-implement plan.