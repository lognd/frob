---
id: T-1546
title: 'frob refactor rename: detect bound-evidence references and offer --replace
  rebind'
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
- src/frob/refactor/_repointer.py
- tests/test_refactor.py
- docs/commands/refactor.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/refactor/**
  reason: narrow the mega-glob to the one file this fix actually touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/refactor/_repointer.py
  reason: narrow the mega-glob to the one file this fix actually touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tests/test_refactor.py
  reason: narrow the mega-glob to the one file this fix actually touches
  actor: logan
  at: '2026-08-08'
- op: remove
  glob: src/frob/tickets/_evidence.py
  reason: not modifying this file; the fix is confined to _repointer.py's ledger-file
    list
  actor: logan
  at: '2026-08-08'
- op: add
  glob: docs/commands/refactor.md
  reason: 'AFFECT001: doc anchor for scan_evidence_citations needed updating'
  actor: logan
  at: '2026-08-08'
evidence:
- tests/test_refactor.py::TestRepointer::test_ticket_evidence_symref_rewritten
- tests/test_refactor.py::TestRepointer::test_per_ticket_ledger_file_evidence_rewritten
- tests/test_refactor.py::TestRepointer::test_archived_per_ticket_ledger_file_evidence_rewritten
designated_repro_test: tests/test_refactor.py::TestRepointer::test_per_ticket_ledger_file_evidence_rewritten
threat: null
component: null
---
Follow-up from T-1537 (frob ticket evidence --replace): that ticket shipped the CLI primitive (replace_evidence) but not the detection half its own body named -- frob refactor rename (or an equivalent rename-detection pass) should notice when a renamed/parametrized symbol/test node id is bound as a ticket's evidence and offer (or auto-apply) the matching --replace rebind, closing the loop the T-1520 parametrization incident exposed by hand.