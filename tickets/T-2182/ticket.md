---
id: T-2182
title: Ticket rot is measured by TICK004 in the gates layer but never surfaced where
  dispatch happens, so 15 tickets aged past threshold (3 critical, up to 20d) while
  every wave picked freshly-filed work
state: queued
kind: feature
origin: human
created: '2026-08-16'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- scripts/fleet_status.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: 'Surface rotting tickets in the place a coordinator ALREADY looks before dispatching
    (scripts/fleet_status.py''s standing report), not behind a new command. Precedent:
    T-2049 did exactly this for the verify quarantine, and it was read and acted on
    by an agent within two hours of landing, having gone unnoticed for an hour before.
    A command someone must know to run is not surfacing. This test MUST fail against
    current main.'
  evidence: []
- text: Derive the rotting set from the ticket ledger's own STRUCTURED fields (state,
    priority, and the queued-since timestamp) compared against the configured TICK004
    thresholds -- never by parsing frob check's rendered diagnostic text. The gate
    message is a rendering; the ledger is the source of truth, and a text parse would
    break the moment the message wording changes.
  evidence: []
- text: Given 15 tickets past the rot threshold including 3 critical, when a coordinator
    runs the standing fleet report, then the count and the oldest/highest-priority
    entries appear WITHOUT passing any flag -- reproducing today's state where TICK004
    fired 11 times inside a 19-error frob check list and was read as noise for the
    whole session.
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
---
