---
id: T-0572
title: 'acceptance-evidence binding: close verifies the acceptance mapping, not just
  evidence existence'
state: done
kind: feature
origin: agent
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- src/frob/app/ticket_runner.py
- src/frob/app/config.py
- src/frob/__main__.py
- docs/modules/tickets.md
- tests/test_tickets_acceptance.py
- tests/test_tickets.py
- tests/test_tickets_brief.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/**
  reason: 'replaying worktree scope on main: schema-bootstrap manual land (worktree
    ledger unreadable by pre-T-0572 parser)'
  actor: logan
  at: '2026-07-22'
- op: add
  glob: src/frob/app/ticket_runner.py
  reason: 'replaying worktree scope on main: schema-bootstrap manual land (worktree
    ledger unreadable by pre-T-0572 parser)'
  actor: logan
  at: '2026-07-22'
- op: add
  glob: src/frob/app/config.py
  reason: 'replaying worktree scope on main: schema-bootstrap manual land (worktree
    ledger unreadable by pre-T-0572 parser)'
  actor: logan
  at: '2026-07-22'
- op: add
  glob: src/frob/__main__.py
  reason: 'replaying worktree scope on main: schema-bootstrap manual land (worktree
    ledger unreadable by pre-T-0572 parser)'
  actor: logan
  at: '2026-07-22'
- op: add
  glob: docs/modules/tickets.md
  reason: 'replaying worktree scope on main: schema-bootstrap manual land (worktree
    ledger unreadable by pre-T-0572 parser)'
  actor: logan
  at: '2026-07-22'
- op: add
  glob: tests/test_tickets_acceptance.py
  reason: 'replaying worktree scope on main: schema-bootstrap manual land (worktree
    ledger unreadable by pre-T-0572 parser)'
  actor: logan
  at: '2026-07-22'
- op: add
  glob: tests/test_tickets.py
  reason: 'replaying worktree scope on main: schema-bootstrap manual land (worktree
    ledger unreadable by pre-T-0572 parser)'
  actor: logan
  at: '2026-07-22'
- op: add
  glob: tests/test_tickets_brief.py
  reason: 'replaying worktree scope on main: schema-bootstrap manual land (worktree
    ledger unreadable by pre-T-0572 parser)'
  actor: logan
  at: '2026-07-22'
evidence:
- tests/test_tickets_acceptance.py::TestCloseGate::test_unbound_acceptance_criterion_refuses_close
designated_repro_test: null
threat: null
component: null
---
Ticket acceptance: items are prose; close checks that evidence exists and covers scope, not that each acceptance item is evidenced. Bind acceptance items to evidence ids (acceptance: [{text, evidence: [...]}]) and refuse close while any item is unbound, closing the 'closed but not what was asked' hole. Scope: src/frob/tickets/, gates evidence checks, docs/modules/tickets.md.