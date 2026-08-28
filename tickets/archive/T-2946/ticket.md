---
id: T-2946
title: Burn TICK004/TICK007 to zero via real ticket-queue triage, then promote
state: done
kind: bug
origin: human
created: '2026-08-26'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tickets/T-0969/ticket.md
- tickets/T-1273/ticket.md
- tickets/T-1382/ticket.md
- tickets/T-2391/ticket.md
- tickets/T-2501/ticket.md
- tickets/T-2573/ticket.md
- tickets/T-2916/ticket.md
- tickets/archive/T-0450/ticket.md
- tickets/T-2954/**
evidence_scope:
- tests/integration/test_interfaces.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tickets/*/ticket.md
  reason: per-ticket triage requires editing state/priority/sprint fields on the flagged
    tickets themselves
  actor: logan
  at: '2026-08-26'
- op: remove
  glob: tickets/*/ticket.md
  reason: narrow to the specific TICK004/TICK007-flagged tickets under triage
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tickets/T-0450/ticket.md
  reason: narrow to the specific TICK004/TICK007-flagged tickets under triage
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tickets/T-0969/ticket.md
  reason: narrow to the specific TICK004/TICK007-flagged tickets under triage
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tickets/T-1273/ticket.md
  reason: narrow to the specific TICK004/TICK007-flagged tickets under triage
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tickets/T-1382/ticket.md
  reason: narrow to the specific TICK004/TICK007-flagged tickets under triage
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tickets/T-2391/ticket.md
  reason: narrow to the specific TICK004/TICK007-flagged tickets under triage
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tickets/T-2501/ticket.md
  reason: narrow to the specific TICK004/TICK007-flagged tickets under triage
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tickets/T-2573/ticket.md
  reason: narrow to the specific TICK004/TICK007-flagged tickets under triage
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tickets/T-2916/ticket.md
  reason: narrow to the specific TICK004/TICK007-flagged tickets under triage
  actor: logan
  at: '2026-08-26'
- op: remove
  glob: tickets/T-0450/ticket.md
  reason: 'T-0450 lives under tickets/archive/ (the ledger anomaly itself: archived
    while still queued)'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tickets/archive/T-0450/ticket.md
  reason: 'T-0450 lives under tickets/archive/ (the ledger anomaly itself: archived
    while still queued)'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tickets/T-2954/**
  reason: the T-0450 archive-anomaly follow-up ticket this triage filed
  actor: logan
  at: '2026-08-26'
body_changes:
- mode: append
  reason: 'BUG002: this ticket is queue triage, not a reproducible code defect'
  actor: logan
  at: '2026-08-26'
  old_length: 1422
  new_length: 1780
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: fc46d5ababe6a380eb3316a36bb7a2643d88f3d1
---
T-2372 burned TICK011 to zero and promoted it to ERROR (fixed a bare-word
false-positive pattern plus repaired two genuine unticketed disclosures).
TICK004 (7 live findings) and TICK007 (1 live finding) remain at WARN,
unburned -- both are DATA-DRIVEN checks over the live ticket queue's real
state, not code defects, so burning them honestly requires real
ticket-queue triage on other tickets, not a code fix:

TICK004 (queue rot, 7 findings):
- T-0450 (archived directory, but state=queued -- a real ledger anomaly
  worth investigating on its own before triaging its rot)
- T-0969, T-1273 (epics, already decomposed -- these may be structurally
  expected to keep firing until every child closes; worth checking
  whether TICK004's own "already decomposed" branch should eventually
  go silent once ALL children are terminal, not just noted)
- T-1382, T-2391, T-2501, T-2573 (standalone high-priority tickets,
  8-25 days old, need an owner decision: work, re-prioritize, or drop)

TICK007 (undispatched-stale, 1 finding):
- T-2916 ("frob is Linux-only in practice", critical priority) needs
  dispatch or re-prioritization.

Do NOT promote TICK004/TICK007 severity until the count is genuinely
zero (T-2372's own body explicitly forbids promoting before the burn --
it reds the tree). Re-measure with `frob check --json --only tickets`
before starting and before claiming done, per T-2372's own measurement
discipline.

frob:waive BUG002 reason="T-2946 is real ticket-queue triage (per-finding TICK004/TICK007 disposition), not a code defect -- there is no code path to reproduce as a failing-then-passing test; the one code artifact of this pass is a follow-up ticket (T-2954) filed for a separate, undispatched gap. Standard done-report/evidence discipline applies instead."