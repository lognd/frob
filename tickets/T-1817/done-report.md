## Done report

`_b9_exempt_file` (the SCOPE001/PRE001 no-active-ticket exemption) only
knew about the legacy single-file `tickets.md` ledger, not the sharded
`tickets/<id>/*` layout this repo now uses -- `frob ticket start`'s own
auto-commit writes exactly `tickets/T-####/ticket.md`, so any unscoped
audit run from a worktree/branch whose only advance past `main` was
routine ticket-CLI bookkeeping saw a false, unexplainable "diff touches
N file(s)" PRE001/SCOPE001 on an otherwise genuinely clean tree.
Reproduced directly on this branch: `git status --porcelain` empty,
`frob check --only scope --only prework` (no --ticket) reported exactly
this shape naming `tickets/T-1817/ticket.md`.

Fix: `_b9_exempt_file` now also exempts any `tickets/`-prefixed path,
the sharded-ledger equivalent of the existing `tickets.md` exemption.
Chose suppression (the fix's own required option 1) over adding an
escape-hatch flag, per the ticket's explicit directive.

Also satisfies requirement 2: `_no_active_ticket_violation`'s message
now names the merge-base `diff` was computed against, so the "N
file(s)" count is explainable from the message alone instead of
unexplainable against a reader's clean `git status`.

Landing this ticket's own diff surfaced a second, distinct gap: SCOPE001
(scope_gate, a different check than the B9 no-active-ticket path this
ticket fixes) doesn't know about the sharded ledger either --
`tickets/<id>/**` is not implicitly in a ticket's own declared scope the
way `tickets.md` is. Filed as a follow-up (see Filed below) since the
fix belongs in `frob.tickets._models.scope_matches`/`LEDGER_PATH`,
outside this ticket's declared scope.

### Changed
```
 tickets/T-1817/ticket.md           | 40 +++++++++++++++++++++++++++++++++++++-
 tickets/T-1819/ticket.md | 39 +++++++++++++++++++++++++++++++++++++
 2 files changed, 78 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_gates.py::TestRunGates::test_run_gates_still_skips_scope_and_prework_for_sharded_ticket_diff` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestRunGates::test_no_active_ticket_violation_names_the_diff_base` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 1 error(s), 1170 warning(s), 734 waived
- error-findings: PRE001@tickets/T-1817
