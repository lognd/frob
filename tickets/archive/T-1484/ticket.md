---
id: T-1484
title: 'WAVE14-B: drain TICK warning class (scope-breadth ack mechanism + TICK004/TICK003
  cleanup)'
state: done
kind: docs
origin: human
created: '2026-08-03'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_tickets_gate.py
- src/frob/tickets/_models.py
- src/frob/tickets/_setters.py
- src/frob/tickets/_doable.py
- src/frob/app/ticket_runner/_mutate.py
- src/frob/app/ticket_runner/__init__.py
- src/frob/app/config.py
- docs/modules/tickets.md
- docs/modules/gates.md
- tickets.md
- tests/test_tickets_lease.py
- tests/test_tickets_scope_mutation.py
- tests/test_ticket_evidence.py
- src/frob/tickets/__init__.py
- src/frob/_cli_parsers/_ticket/_metadata.py
- src/frob/_cli_parsers/_ticket/__init__.py
- src/frob/_cli_parsers/__init__.py
- tests/test_gates_tick009_tick010.py
- tickets-archive.md
- docs/modules/app.md
- docs/design/registry/EXHAUSTIVENESS-GATE.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: tests/**
  reason: 'Narrow tests/** to the specific test files this ticket touches (new

    scope_breadth_ack setter test + tick009 gate test), matching this drive''s

    own TICK009 mission of precise scopes over broad globs.

    '
  actor: logan
  at: '2026-08-03'
- op: add
  glob: tests/test_tickets_lease.py
  reason: 'Narrow tests/** to the specific test files this ticket touches (new

    scope_breadth_ack setter test + tick009 gate test), matching this drive''s

    own TICK009 mission of precise scopes over broad globs.

    '
  actor: logan
  at: '2026-08-03'
- op: add
  glob: tests/test_tickets_scope_mutation.py
  reason: 'Narrow tests/** to the specific test files this ticket touches (new

    scope_breadth_ack setter test + tick009 gate test), matching this drive''s

    own TICK009 mission of precise scopes over broad globs.

    '
  actor: logan
  at: '2026-08-03'
- op: add
  glob: tests/test_ticket_evidence.py
  reason: 'Narrow tests/** to the specific test files this ticket touches (new

    scope_breadth_ack setter test + tick009 gate test), matching this drive''s

    own TICK009 mission of precise scopes over broad globs.

    '
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/tickets/__init__.py
  reason: genuinely need to export new set_scope_breadth_ack setter from the package
    __init__, same as set_priority/set_kind/set_tier
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/_cli_parsers/_ticket/_metadata.py
  reason: the scope-ack CLI subcommand needs argparse registration in _cli_parsers/_ticket
    + config.py field additions, mirroring the existing scope command
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/_cli_parsers/_ticket/__init__.py
  reason: the scope-ack CLI subcommand needs argparse registration in _cli_parsers/_ticket
    + config.py field additions, mirroring the existing scope command
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/app/config.py
  reason: the scope-ack CLI subcommand needs argparse registration in _cli_parsers/_ticket
    + config.py field additions, mirroring the existing scope command
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/_cli_parsers/__init__.py
  reason: top-level _cli_parsers re-export list must mirror the new _add_ticket_scope_ack_parser
    the same way every existing _add_ticket_* name is re-exported
  actor: logan
  at: '2026-08-03'
- op: add
  glob: tests/test_gates_tick009_tick010.py
  reason: the direct TICK009 gate unit-test file is the right home for a scope_breadth_ack
    exemption regression test
  actor: logan
  at: '2026-08-03'
- op: add
  glob: tickets-archive.md
  reason: tickets-archive.md touched by frob ticket archive; docs/modules/app.md and
    EXHAUSTIVENESS-GATE.md are frob:doc targets of src/frob/app/config.py::AppConfig
    / app/ticket_runner __init__::run already in scope (SCOPE002 closure)
  actor: logan
  at: '2026-08-03'
- op: add
  glob: docs/modules/app.md
  reason: tickets-archive.md touched by frob ticket archive; docs/modules/app.md and
    EXHAUSTIVENESS-GATE.md are frob:doc targets of src/frob/app/config.py::AppConfig
    / app/ticket_runner __init__::run already in scope (SCOPE002 closure)
  actor: logan
  at: '2026-08-03'
- op: add
  glob: docs/design/registry/EXHAUSTIVENESS-GATE.md
  reason: tickets-archive.md touched by frob ticket archive; docs/modules/app.md and
    EXHAUSTIVENESS-GATE.md are frob:doc targets of src/frob/app/config.py::AppConfig
    / app/ticket_runner __init__::run already in scope (SCOPE002 closure)
  actor: logan
  at: '2026-08-03'
evidence:
- tests/test_tickets_scope_mutation.py::TestSetScopeBreadthAck::test_ack_sets_both_fields
- tests/test_tickets_scope_mutation.py::TestSetScopeBreadthAck::test_ack_requires_non_blank_reason
- tests/test_tickets_scope_mutation.py::TestSetScopeBreadthAck::test_cli_scope_ack_sets_flag
- tests/test_tickets_scope_mutation.py::TestSetScopeBreadthAck::test_cli_scope_ack_requires_reason
- tests/test_gates_tick009_tick010.py::TestTick009ScopeBreadthNudges::test_scope_breadth_ack_exempts_ticket
designated_repro_test: null
threat: null
component: null
---
WAVE14-B drain-to-zero: TICK warning class (~105 warnings from `uv run frob check --only tickets`).

Scope of this drive ticket:
1. TICK009 scope-breadth nudges: for queued non-epic tickets, narrow scopes to
   real file lists via `frob ticket scope --add/--remove --reason`. For
   genuinely-broad epic/umbrella tickets, design and implement an honest
   acknowledged-broad mechanism (new `scope_breadth_ack` ticket field +
   `frob ticket scope-ack` setter), since TICK009 currently has no waive
   channel at all.
2. TICK004 rotting criticals: re-prioritize with a recorded reason where
   genuinely not-critical; leave and note where still critical.
3. TICK003 archive threshold: run `frob ticket archive` if safe in this
   worktree, else note for the coordinator.

Before/after `uv run frob check --only tickets` counts recorded in Done report.