---
id: T-0929
title: 'frob check quick wins from the audit: shared caches, incremental gates, spawn
  dedup'
state: done
kind: feature
origin: human
created: '2026-07-26'
priority: high
blocked_by:
- T-0928
parent: T-0927
tier: ticket
sprint: null
scope:
- src/frob/check/**
- src/frob/gates/**
- docs/audits/check-performance.md
- docs/modules/gates.md
- docs/modules/tickets.md
- frob.lock
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/audits/check-performance.md
  reason: audit remediation log + doc-drift updates for the tickets_gate shared-load
    fix, per this ticket's own dispatch instruction to append to the audit doc
  actor: logan
  at: '2026-07-27'
- op: add
  glob: docs/modules/gates.md
  reason: audit remediation log + doc-drift updates for the tickets_gate shared-load
    fix, per this ticket's own dispatch instruction to append to the audit doc
  actor: logan
  at: '2026-07-27'
- op: add
  glob: docs/modules/tickets.md
  reason: audit remediation log + doc-drift updates for the tickets_gate shared-load
    fix, per this ticket's own dispatch instruction to append to the audit doc
  actor: logan
  at: '2026-07-27'
- op: add
  glob: frob.lock
  reason: frob ack writes to frob.lock for the three new frob:tests directives this
    ticket added
  actor: logan
  at: '2026-07-27'
evidence:
- tests/test_gates_tickets_hygiene.py::TestTick003StaleArchive::test_above_default_error_threshold_errors
- tests/test_tickets_collision.py::TestRealLedgerIntegrity::test_no_duplicate_ids_within_or_across_ledgers
- tests/test_gates.py::TestTick006PhantomFiling::test_phantom_filed_colon_fires
designated_repro_test: null
threat: null
component: null
---
Child 2 of T-0927, blocked by the audit child. Implement the python-side remedies the audit ranks highest (e.g. one shared parsed-file/content cache across gates instead of per-gate re-reads; incremental gate evaluation off the T-0628 AFFECT digest graph; reuse of the T-0919 shared-spawn pattern anywhere check spawns twice). Each fix cites its audit row and re-measures after.