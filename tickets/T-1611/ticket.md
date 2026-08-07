---
id: T-1611
title: Audit why frob missed each doc gap, and ticket every detector gap found
state: queued
kind: bug
origin: human
created: '2026-08-05'
priority: high
blocked_by:
- T-1610
parent: T-1609
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: docs/**
  reason: 'TICK009 pre-dispatch narrowing: docs/** leases every doc and serialises
    the queue'
  actor: logan
  at: '2026-08-07'
- op: add
  glob: docs/modules/gates.md
  reason: 'TICK009 pre-dispatch narrowing: docs/** leases every doc and serialises
    the queue'
  actor: logan
  at: '2026-08-07'
designated_repro_test: null
threat: null
component: null
---
For every documentation gap the sweep found, determine why frob did not already catch it, and ticket each detector gap.

This is the important half. A doc gap that frob could have caught and did not is a hole in the enforcement layer, and frob's entire premise is that unaccounted-for work is a build failure. Every gap is therefore a bug report against the gates, not merely an editing task.

For each gap, classify the cause and act accordingly:
- NO RULE EXISTS for this obligation -- file a ticket to add the rule.
- A RULE EXISTS BUT DID NOT FIRE (wrong scope, diff-scoped when it should be full-run, structurally unverifiable, cache serving stale results) -- file a ticket against that rule, and treat it as the same class as this drive's WAIVE004 and degraded-run incidents.
- THE RULE FIRED AND WAS WAIVED -- hand it to the waiver audit child; do not resolve it here.
- THE RULE FIRED AND WAS IGNORED as a warning that never became an error -- file a ticket to decide whether it should be promoted, and say why it was tolerated.

Deliverable: a written classification of every gap plus one filed ticket per distinct detector gap. A gap left unclassified is the outcome to avoid -- it is precisely the silent hole the exercise exists to close.