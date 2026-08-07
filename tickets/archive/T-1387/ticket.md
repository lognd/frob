---
id: T-1387
title: frob ticket close's app-layer wiring for T-1384's own_obligations_clean guard
state: done
kind: bug
origin: human
created: '2026-08-01'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/ticket_runner/**
- tests/unit/test_ticket_close_own_obligations_t1387.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_ticket_close_own_obligations_t1387.py
  reason: T-1387's own end-to-end regression test for own_obligations_clean wiring
  actor: logan
  at: '2026-08-01'
evidence:
- tests/unit/test_ticket_close_own_obligations_t1387.py::TestCloseOwnObligationsForTicket::test_no_touched_files_skips_the_check
- tests/unit/test_ticket_close_own_obligations_t1387.py::TestCloseOwnObligationsForTicket::test_diff_unavailable_skips_the_check
- tests/unit/test_ticket_close_own_obligations_t1387.py::TestCloseOwnObligationsForTicket::test_dirty_cov001_under_touched_file_returns_false
- tests/unit/test_ticket_close_own_obligations_t1387.py::TestCloseOwnObligationsForTicket::test_rel001_bump_outstanding_returns_false
- tests/unit/test_ticket_close_own_obligations_t1387.py::TestCloseOwnObligationsForTicket::test_clean_diff_and_no_bump_returns_true
- tests/unit/test_ticket_close_own_obligations_t1387.py::TestCloseRefusesOwnObligationsEndToEnd::test_close_refuses_when_own_diff_leaves_cov001_outstanding
- tests/unit/test_ticket_close_own_obligations_t1387.py::TestCloseRefusesOwnObligationsEndToEnd::test_close_succeeds_once_the_diff_is_actually_clean
- tests/unit/test_ticket_close_own_obligations_t1387.py::TestCloseOwnObligationsForTicket::test_dirty_selfaudit001_under_touched_file_returns_false
designated_repro_test: null
acceptance:
- text: 'GIVEN a ticket whose change adds a public symbol with no frob:doc edge

    WHEN frob ticket close runs

    THEN it refuses and names the missing edge'
  evidence:
  - tests/unit/test_ticket_close_own_obligations_t1387.py::TestCloseOwnObligationsForTicket::test_dirty_cov001_under_touched_file_returns_false
  - tests/unit/test_ticket_close_own_obligations_t1387.py::TestCloseRefusesOwnObligationsEndToEnd::test_close_refuses_when_own_diff_leaves_cov001_outstanding
- text: 'GIVEN a ticket whose change adds public test classes not declared on the

    testsuite strata node

    WHEN close runs

    THEN it refuses and names the sync command'
  evidence:
  - tests/unit/test_ticket_close_own_obligations_t1387.py::TestCloseOwnObligationsForTicket::test_dirty_selfaudit001_under_touched_file_returns_false
- text: 'GIVEN a ticket whose change alters the public API

    WHEN close runs

    THEN it refuses unless the REL001 bump is already taken'
  evidence:
  - tests/unit/test_ticket_close_own_obligations_t1387.py::TestCloseOwnObligationsForTicket::test_rel001_bump_outstanding_returns_false
threat: null
component: null
---
T-1384 added the `own_obligations_clean` injected parameter to
`frob.tickets.transition`/`reverify_close_guard` (mirroring the existing
D-02/T-0571/T-0844/T-0417 injected-boolean pattern) -- `frob.tickets`
itself deliberately stays free of the `frob.gates`/`frob.graph`
dependency needed to COMPUTE the value (docs/rework.md cycle-avoidance),
so the guard clause refuses when the caller passes `False` but nothing
yet passes anything other than the default `None` (fully permissive).

This ticket is the wiring half: `src/frob/app/ticket_runner/_close_cmd.py`'s
`_close_guards_for_ticket` (and `_reverify`'s identical computation) needs
a new `_close_own_obligations_for_ticket`-shaped helper, alongside
`_covers_scope_for_ticket`/`_close_mutation_evidence_for_ticket`, that:

- runs a `--ticket`-scoped-but-diff-aware COV001 check for new public
  symbols the ticket's own diff added with no `frob:doc` edge
- runs the SELFAUDIT001/SYS104 testsuite-declaration check for new public
  test classes the diff added
- runs REL001's changed-public-API check for whether the bump is already
  taken

and passes the combined boolean into `transition(..., own_obligations_clean=...)`
in `_close` and into `reverify_close_guard(..., own_obligations_clean=...)`
in `_reverify`, refusing with `TicketError.OwnObligationsUnclean`'s exact
remedy message when any of the three come back dirty -- closing the
T-1377/T-1379/T-1381 residue class end to end (this was observed twice in
one session: a `--ticket`-scoped close saw zero because these gate
families are repo-wide, not ticket-scoped, and the residue only surfaced
on the NEXT unscoped `frob check`).