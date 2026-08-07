---
id: T-1384
title: frob ticket close must check the ticket's own doc/strata/REL obligations before
  allowing the close
state: done
kind: bug
origin: human
created: '2026-08-01'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- tests/test_tickets_own_obligations.py
- docs/modules/tickets.md
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_tickets_own_obligations.py
  reason: 'The own_obligations_clean guard clause lives entirely in

    src/frob/tickets/_evidence.py and src/frob/tickets/_models.py, already

    in scope; its regression tests need a dedicated test file since no test

    glob was declared at filing time.

    '
  actor: logan
  at: '2026-08-01'
- op: add
  glob: docs/modules/tickets.md
  reason: 'This ticket''s fix creates its own COV/AFFECT/SCOPE residue (docs/modules/

    tickets.md doc edges for transition/reverify_close_guard/TicketError,

    design/frob.strata''s testsuite node declaration for the new test class)

    -- exactly the class of obligation this ticket exists to catch. Adding

    both to scope rather than leaving them undeclared.

    '
  actor: logan
  at: '2026-08-01'
- op: add
  glob: design/frob.strata
  reason: 'This ticket''s fix creates its own COV/AFFECT/SCOPE residue (docs/modules/

    tickets.md doc edges for transition/reverify_close_guard/TicketError,

    design/frob.strata''s testsuite node declaration for the new test class)

    -- exactly the class of obligation this ticket exists to catch. Adding

    both to scope rather than leaving them undeclared.

    '
  actor: logan
  at: '2026-08-01'
evidence:
- tests/test_tickets_own_obligations.py::TestT1384OwnObligationsOnClose::test_transition_rejects_when_own_obligations_clean_false
- tests/test_tickets_own_obligations.py::TestT1384OwnObligationsOnClose::test_transition_allows_when_own_obligations_clean_true
- tests/test_tickets_own_obligations.py::TestT1384OwnObligationsOnClose::test_transition_permissive_when_own_obligations_clean_none
designated_repro_test: null
acceptance:
- text: GIVEN a ticket whose change adds a public symbol with no frob:doc edge WHEN
    frob ticket close runs THEN it refuses and names the missing edge
  evidence:
  - tests/test_tickets_own_obligations.py::TestT1384OwnObligationsOnClose::test_transition_rejects_when_own_obligations_clean_false
  - tests/test_tickets_own_obligations.py::TestT1384OwnObligationsOnClose::test_transition_allows_when_own_obligations_clean_true
  - tests/test_tickets_own_obligations.py::TestT1384OwnObligationsOnClose::test_transition_permissive_when_own_obligations_clean_none
- text: GIVEN a ticket whose change adds public test classes not declared on the testsuite
    strata node WHEN close runs THEN it refuses and names the sync command
  evidence:
  - tests/test_tickets_own_obligations.py::TestT1384OwnObligationsOnClose::test_transition_rejects_when_own_obligations_clean_false
  - tests/test_tickets_own_obligations.py::TestT1384OwnObligationsOnClose::test_transition_allows_when_own_obligations_clean_true
  - tests/test_tickets_own_obligations.py::TestT1384OwnObligationsOnClose::test_transition_permissive_when_own_obligations_clean_none
- text: GIVEN a ticket whose change alters the public API WHEN close runs THEN it
    refuses unless the REL001 bump is already taken
  evidence:
  - tests/test_tickets_own_obligations.py::TestT1384OwnObligationsOnClose::test_transition_rejects_when_own_obligations_clean_false
  - tests/test_tickets_own_obligations.py::TestT1384OwnObligationsOnClose::test_transition_allows_when_own_obligations_clean_true
  - tests/test_tickets_own_obligations.py::TestT1384OwnObligationsOnClose::test_transition_permissive_when_own_obligations_clean_none
threat: null
component: null
---
Observed twice in a row 2026-08-01. T-1377/T-1379 closed clean, then the next unscoped run showed 23 errors that were entirely their own residue (COV001 doc edges, SELFAUDIT001/SYS104 testsuite declarations, DOC007/DRIFT002 directive-form typos, ARCH103, REL001) -- T-1380 had to be filed to carry it. T-1381 then closed clean and left the SAME three classes, needing T-1383.

close already runs a gate sweep, but scoped to the ticket -- and gate:COV/SELFAUDIT/REL findings for newly added symbols are repo-wide, so a --ticket-scoped close sees zero and lets the ticket through. The residue only surfaces on the next unscoped run, by which time the ticket is closed and a follow-through ticket is the only honest option.

close should evaluate the obligations the ticket's OWN diff creates -- every public symbol it added needs a frob:doc edge, every public test class it added needs a strata declaration, a changed public API needs its REL001 bump -- and refuse with the exact remedy, in the same shape as T-1381's stamp guard.

This is the systematize-the-footgun rule: I hit it twice in one session and the tool could have caught both.