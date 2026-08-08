---
id: T-1483
title: wire frob refactor into main CLI dispatch
state: done
kind: feature
origin: human
created: '2026-08-03'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/_cli_parsers/**
- src/frob/__main__.py
- docs/commands/refactor.md
- tests/test_refactor.py
- tests/unit/test_main_entry.py
- src/frob/refactor/_cli.py
- tickets/T-1483/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/commands/refactor.md
  reason: the doc's own not-yet-wired claim (frob:until T-1483) must be updated now
    that wiring lands, and CLI-dispatch integration coverage needs test_refactor.py/test_main_entry.py
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tests/test_refactor.py
  reason: the doc's own not-yet-wired claim (frob:until T-1483) must be updated now
    that wiring lands, and CLI-dispatch integration coverage needs test_refactor.py/test_main_entry.py
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tests/unit/test_main_entry.py
  reason: the doc's own not-yet-wired claim (frob:until T-1483) must be updated now
    that wiring lands, and CLI-dispatch integration coverage needs test_refactor.py/test_main_entry.py
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/refactor/_cli.py
  reason: module docstring claims wiring is out of scope/not yet connected -- now
    stale, must be corrected
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tickets/T-1483/**
  reason: 'SCOPE001: ticket''s own per-ticket ledger file written by ordinary frob
    ticket CLI lifecycle commands, per T-1742/T-1737 precedent'
  actor: logan
  at: '2026-08-08'
evidence:
- tests/unit/test_main_entry.py::TestRefactorDispatch::test_refactor_subcommand_dispatches_to_run_refactor_command
- tests/unit/test_main_entry.py::TestRefactorDispatch::test_refactor_exit_code_propagates
designated_repro_test: null
threat: null
component: null
---
docs/commands/refactor.md documents frob.refactor._cli.add_refactor_parser
and run_refactor_command as built and ready, but T-1197's declared scope
never included src/frob/_cli_parsers/** or src/frob/__main__.py, so the
one-line _add_refactor_parser(sub) wiring call was never actually made.
Wire frob refactor into the main CLI dispatch. Found while draining
NEGEXIST001 (T-1477): the doc's own "not yet wired" claim had
no frob:until binding.