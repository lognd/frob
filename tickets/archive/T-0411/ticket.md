---
id: T-0411
title: 'Queue health + priority model: nothing important rots silently (tickets have
  no priority/value today; doable is age-only)'
state: done
kind: feature
origin: human
created: '2026-07-20'
priority: medium
parent: T-0397
tier: ticket
sprint: null
scope:
- src/frob/tickets/
- src/frob/gates/
- frob.toml
- tests/test_tickets_priority.py
- docs/modules/tickets.md
- pyproject.toml
- CHANGELOG.md
- uv.lock
- .frob-release.json
- frob.lock
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_tickets_priority.py
  reason: T-0411 needs its own test file + doc update; declared scope only covered
    tickets/, gates/, frob.toml (the T-0446 scope-declaration gap)
  actor: logan
  at: '2026-07-21'
- op: add
  glob: docs/modules/tickets.md
  reason: T-0411 needs its own test file + doc update; declared scope only covered
    tickets/, gates/, frob.toml (the T-0446 scope-declaration gap)
  actor: logan
  at: '2026-07-21'
- op: add
  glob: pyproject.toml
  reason: REL001 version-bump chain (0.47.0 -> 0.48.0) touches these; standard release-stamp
    bootstrap, same as T-0446 tracked gap
  actor: logan
  at: '2026-07-21'
- op: add
  glob: CHANGELOG.md
  reason: REL001 version-bump chain (0.47.0 -> 0.48.0) touches these; standard release-stamp
    bootstrap, same as T-0446 tracked gap
  actor: logan
  at: '2026-07-21'
- op: add
  glob: uv.lock
  reason: REL001 version-bump chain (0.47.0 -> 0.48.0) touches these; standard release-stamp
    bootstrap, same as T-0446 tracked gap
  actor: logan
  at: '2026-07-21'
- op: add
  glob: .frob-release.json
  reason: REL001 version-bump chain (0.47.0 -> 0.48.0) touches these; standard release-stamp
    bootstrap, same as T-0446 tracked gap
  actor: logan
  at: '2026-07-21'
- op: add
  glob: frob.lock
  reason: REL001 version-bump chain (0.47.0 -> 0.48.0) touches these; standard release-stamp
    bootstrap, same as T-0446 tracked gap
  actor: logan
  at: '2026-07-21'
evidence:
- tests/test_tickets_priority.py::TestPriorityRank::test_critical_outranks_low
- tests/test_tickets_priority.py::TestDoablePriorityOrdering::test_high_priority_surfaces_before_older_low_priority
- tests/test_tickets_priority.py::TestDoablePriorityOrdering::test_same_priority_falls_back_to_age
- tests/test_tickets_priority.py::TestSetPriority::test_updates_priority_field
- tests/test_tickets_priority.py::TestTick004QueueRot::test_stale_critical_ticket_flags
- tests/test_tickets_priority.py::TestTick004QueueRot::test_fresh_ticket_does_not_flag
designated_repro_test: null
threat: null
component: null
---
User reflection (2026-07-20) on why T-0177 (warm-graph daemon, the fix for the perf pain) sat queued forever and was never built. ROOT CAUSE = a frob tooling gap, same class as every other today: (1) tickets carry NO priority/value/impact field -- the model has kind/state/scope/evidence/blocked_by/parent but nothing about importance; (2) frob ticket doable orders PURELY oldest-first (sorted by created); so a high-value infra ticket is indistinguishable from a cosmetic bug, and (3) the queue is not drained exhaustively -- work is top-of-mind/directive-driven while 99 queued tickets accumulate with no signal that important ones are rotting. This is the early-exit-without-exhausting-the-registry anti-pattern applied to the TICKET QUEUE.

FIX (the "rethink", one coherent layer, an instance of T-0407 registry-exhaustiveness applied to the open queue): (a) add PRIORITY + VALUE/IMPACT to the ticket model (e.g. priority: low/med/high/critical, and an impact/effort estimate) -- importance becomes first-class, not implied by age; (b) frob ticket doable factors priority/value AND staleness, not just created-date, so the most important unblocked work surfaces first; (c) a QUEUE-HEALTH gate/report (sibling of ledger-hygiene T-0409): flag when a high-priority ticket has sat queued past N days (rot), when the open queue grows unboundedly, or when high-value tickets are being skipped for low-value ones -- so "we are neglecting important work" is a visible signal, never silent; (d) frob ticket queue-health / a dashboard answering "what is the most important un-built thing" and "what is rotting" honestly. Ships per-project (T-0406). Acceptance: a high-priority ticket untouched for the threshold reds/warns; doable returns value-then-age order; the queue-health report names rotting high-value tickets (would have surfaced T-0177 immediately). This closes the "important work rots invisibly" gap for good.