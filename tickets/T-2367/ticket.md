---
id: T-2367
title: 'TICK004: tickets.md ledger-consistency -- 9 errors + 17 warnings under one
  identity, needs per-finding triage'
state: queued
kind: bug
origin: human
created: '2026-08-17'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Split from T-2341's re-measured still-live remainder (measured 2026-08-18):
TICK004 (ledger-consistency) fires 9 errors + 17 warnings under a single
(rule, file) identity on tickets.md -- an exact match to T-2331's original
claim, unchanged since.

Needs its own read of `frob check --only tickets` output in full (not
summarised) to see the individual finding text before deciding a fix --
TICK004 collapses many distinct findings into one (rule, file) identity
here, so a real diagnosis requires the per-finding detail, not just the
9/17 count. First step: run `frob check --only tickets --json` (or the
plain-text form) and read every TICK004-tagged finding under tickets.md,
then triage which are genuine ledger defects vs stale/false-positive
readings before touching anything.
