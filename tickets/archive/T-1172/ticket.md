---
id: T-1172
title: 'fix: tickets/__init__.py missing _run_evidence_command re-export after T-1152
  evidence-family split'
state: done
kind: bug
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/__init__.py
- tests/test_tickets_evidence_cli.py
- src/frob/tickets/_evidence.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_evidence.py
  reason: the fix re-exports a symbol from this module
  actor: logan
  at: '2026-07-28'
evidence:
- tests/test_tickets_evidence_cli.py::TestRunEvidenceCommandNoShell::test_command_substitution_is_not_expanded
designated_repro_test: null
threat: null
component: null
---
T-1152's evidence-family split moved _run_evidence_command into src/frob/tickets/_evidence.py without re-exporting it from the package -- tests/test_tickets_evidence_cli.py::TestRunEvidenceCommandNoShell imports it directly via 'from frob.tickets import _run_evidence_command', predating the split, and broke with ImportError. Found via a broad 'frob test --base main' touched-set run while landing T-1165 in the same worktree.