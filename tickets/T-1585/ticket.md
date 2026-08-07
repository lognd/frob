---
id: T-1585
title: 'rapid profile: evidence/done-report leniency for docs/chore, REL001 off, baseline-thread-free
  land'
state: queued
kind: feature
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- src/frob/app/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
Filed while working T-1575: rapid profile's TEST016-skip and pre-commit-sweep-skip seams landed; three remaining rapid semantics from T-1575's body are still open: (1) evidence/done-report requirements light for kind=docs/chore, (2) REL001 off under rapid, (3) no baseline snapshot worktree at all -- today rapid still runs the T-1463 baseline thread because _land_cmd.py's post-land sweep reads the same result. Ledger integrity and LAND-PROOF stay non-negotiable in every profile.