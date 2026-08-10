---
id: T-1939
title: 'No rule-level telemetry: cannot measure which of 293 gate rules ever fire'
state: queued
kind: feature
origin: human
created: '2026-08-09'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/telemetry/
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
AUDIT FINDING (full gate audit, 2026-08-09).

The question "which of our 293 gate rules earn their keep?" cannot be
answered from recorded data. `.frob/telemetry.jsonl` (36,982 records,
8.6MB) has exactly two record shapes:

  ('args_head','duration_ms','exit','iso_ts','kind','subcommand','tree_hash')
  ('event','iso_ts','kind','ticket_id')

Zero records carry a rule dimension -- distinct rule ids in telemetry: 0.
So we record how long `frob check` TOOK and whether it PASSED, but never
which rules fired, how often, or how long each cost.

CONSEQUENCE: this audit had to proxy rule liveness by grepping the ticket
ledger for rule-id mentions. That proxy is biased in a way that matters --
it measures rules that caused ARGUMENT, not rules that caused WORK. A
rule that fires constantly and is fixed without comment looks identical
to a rule that never fires at all.

VALUE: rule-level firing counts would make three recurring decisions
mechanical instead of speculative -- retiring a rule that never fires,
finding the slowest rule when check time regresses, and identifying which
rules actually gate a given subsystem. It also gives the ratchet a real
denominator.

Prefer emitting this automatically from the existing gate-result path
(the findings already exist in memory at the end of every check; only the
write is missing) over adding a `frob gates stats` verb the operator must
know to run. Surfacing belongs where people already look.