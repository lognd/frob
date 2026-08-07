---
id: T-0906
title: SCOPE001 vacuously passes when ticket.scope is empty (no non-empty-scope precondition)
state: done
kind: bug
origin: human
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/__init__.py
- src/frob/tickets/_models.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestScopePrework::test_scope001_fires_when_no_scope_declared
- tests/test_gates.py::TestScopePrework::test_scope001_empty_scope_ledger_still_implicitly_in_scope
designated_repro_test: null
threat: null
component: null
---
Found while working T-0786 (gate-vacuousness sweep).

SCOPE001 (frob.gates._models scope_gate, src/frob/gates/__init__.py:5006)
returns () with no enforcement at all whenever `ticket.scope` is empty:

    if not ticket.scope:
        _log.debug(...)
        return ()

`Ticket.scope`/`TicketSpec.scope` both default to `()` (src/frob/tickets/_models.py)
and no validator enforces a non-empty scope at ticket-creation time. A ticket
filed via `frob ticket new` without `--scope` (or one whose scope was cleared
by a bad `frob ticket scope` edit) is therefore NEVER checked by SCOPE001 --
its diff can touch any file in the repo and this gate stays silent. This is a
satisfied-by-absence vacuousness vector: the gate exists specifically to keep
a worked ticket's diff inside its declared scope, but a ticket with no
declared scope silently gets the LEAST enforcement, not the most.

Fix direction: either (a) refuse to start/queue a ticket whose scope is empty
(TicketSpec/Ticket validator, or a `frob ticket start` precondition), or (b)
change scope_gate's empty-scope branch to a loud, unwaivable violation instead
of a silent pass -- symmetric with how COV002/TODO001 treat a failed diff
load (T-0550/T-0719) as a loud violation rather than a silently-cleared
enforcement surface. Prefer (a): an empty scope should never be a valid
ticket state to begin work from.