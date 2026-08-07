---
id: T-0796
title: 'tickets CLI: --evidence-cmd with --accepts silently records evidence UNBOUND
  (add_cmd_evidence has no accepts param)'
state: done
kind: bug
origin: agent
created: '2026-07-23'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/__init__.py
- src/frob/app/ticket_runner.py
- tests/test_tickets_evidence_cli.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_tickets_evidence_cli.py::TestCmdEvidenceAcceptsBinding::test_evidence_cmd_with_accepts_binds_acceptance_via_cli
- tests/test_tickets_evidence_cli.py::TestCmdEvidenceAcceptsBinding::test_close_evidence_cmd_with_accepts_binds_acceptance_via_cli
designated_repro_test: null
acceptance:
- text: GIVEN frob ticket evidence T-X --evidence-cmd CMD --accepts 0 WHEN the command
    verifies THEN the cmd evidence is bound to acceptance index 0 exactly like pytest-node
    evidence; a regression test drives the CLI path
  evidence:
  - tests/test_tickets_evidence_cli.py::TestCmdEvidenceAcceptsBinding::test_evidence_cmd_with_accepts_binds_acceptance_via_cli
  - tests/test_tickets_evidence_cli.py::TestCmdEvidenceAcceptsBinding::test_close_evidence_cmd_with_accepts_binds_acceptance_via_cli
threat: null
component: null
---
Promotion of T-0677's worktree draft 91ef53bd: add_cmd_evidence in frob.tickets has no accepts parameter and both CLI call sites in ticket_runner.py drop cfg.ticket_accepts for cmd evidence, so docs-kind tickets silently end up with UNBOUND acceptance despite the operator passing --accepts (T-0677 worked around via the library add_evidence call). With the T-0763 land preflight now refusing unbound acceptance, this silent drop blocks docs-ticket lands.