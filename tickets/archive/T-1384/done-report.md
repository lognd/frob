## Done report

Added the `own_obligations_clean` injected boolean parameter to
`frob.tickets.transition`/`_transition_guard`/`_done_transition_guard`/
`reverify_close_guard`, mirroring the existing D-02 (covers_scope)/T-0571
(reviewed)/T-0844 (mutation_evidence)/T-0417 (evidence_reverified)
injected-parameter pattern exactly: `frob.tickets` deliberately stays free
of the `frob.gates`/`frob.graph` dependency needed to COMPUTE whether a
ticket's own diff leaves a new-symbol doc edge, testsuite declaration, or
REL001 bump outstanding (docs/rework.md cycle-avoidance), so the value is
injected by an app-layer caller, never computed inside this package.
`own_obligations_clean=False` refuses `done` with the new
`TicketError.OwnObligationsUnclean`, naming the exact remedy
(`frob check --delta`); `True` allows; `None` (the default, matching
every pre-T-1384 caller) is fully permissive, so no existing caller
changes behavior.

Disclosed cut: this ticket's declared scope (`src/frob/tickets/**` plus
the one test file added to scope) covers only the tickets-package half of
the fix -- the state-machine enabling mechanism, tested directly. The
acceptance criteria describe end-to-end `frob ticket close` behavior,
which additionally needs `src/frob/app/ticket_runner/_close_cmd.py`
(`_close_guards_for_ticket`/`_reverify`) to actually COMPUTE the
COV001/SELFAUDIT001-SYS104/REL001 obligations from the ticket's own diff
and pass them in as `own_obligations_clean=...` -- that file is
out of this ticket's scope (`src/frob/app/**`, not `src/frob/tickets/**`)
and is owned by a filed follow-up ticket instead of being folded in here
silently: T-1387 (renumbers at land), "frob ticket close's
app-layer wiring for T-1384's own_obligations_clean guard".

### Changed
```
 tickets.md | 148 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++--
 1 file changed, 144 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/test_tickets_own_obligations.py::TestT1384OwnObligationsOnClose::test_transition_rejects_when_own_obligations_clean_false` (pytest node id, verified passing when recorded)
- `tests/test_tickets_own_obligations.py::TestT1384OwnObligationsOnClose::test_transition_allows_when_own_obligations_clean_true` (pytest node id, verified passing when recorded)
- `tests/test_tickets_own_obligations.py::TestT1384OwnObligationsOnClose::test_transition_permissive_when_own_obligations_clean_none` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 0 error(s), 1104 warning(s), 697 waived
- error-findings: none (measured, zero errors)
