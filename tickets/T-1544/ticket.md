---
id: T-1544
title: 'Tier-A auto-fix: TICK006 phantom draft citation refile+renumber'
state: done
kind: feature
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_fix_engine.py
- docs/modules/gates.md
- tests/test_gates.py
- design/frob.strata
- tickets/T-1544/ticket.md
- tickets/T-1544/done-report.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/tickets/**
  reason: narrowed from the mega-glob to the actual files touched
  actor: logan
  at: '2026-08-07'
- op: add
  glob: docs/modules/gates.md
  reason: narrowed from the mega-glob to the actual files touched
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tests/test_gates.py
  reason: narrowed from the mega-glob to the actual files touched
  actor: logan
  at: '2026-08-07'
- op: add
  glob: design/frob.strata
  reason: narrowed from the mega-glob to the actual files touched
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tickets/T-1544/ticket.md
  reason: v2 per-ticket ledger files
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tickets/T-1544/done-report.md
  reason: v2 per-ticket ledger files
  actor: logan
  at: '2026-08-07'
evidence:
- tests/test_gates.py::TestFixEngineTierA::test_tick006_refiles_and_rewrites_citation
- tests/test_gates.py::TestFixEngineTierA::test_tick006_known_id_is_never_touched
designated_repro_test: null
threat: null
component: null
---
Follow-up from T-1531: when a TICK006 finding names a draft citation absent from both the ledger and archive, refile a real ticket for it and renumber the citation to the new real id. Needs a Tier-A handler that parses the phantom draft id, files a real ticket capturing recoverable context, and rewrites the citation -- T-1125's prose-reference rewrite already handles the case where the draft DOES exist in the ledger.