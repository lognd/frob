## Done report

`frob ticket land <id> --worktree W` merges `W`'s whole branch, not just
`<id>`'s own commits. Fixed two things per the ticket's plan, plus
answered the "why did CrossTicketLeakage not fire" question:

1. Passenger disclosure: `_check_passenger_tickets` (`frob.tickets._land`)
   scans the branch's full committed diff for `frob:ticket <id>` directive
   ADDITIONS naming any ticket other than the one landing, independent of
   that sibling's own ledger state. Refuses (`LandError.PassengerTickets`,
   listing every passenger id) unless `--allow-cross-ticket` (the same
   escape hatch `_check_cross_ticket_leakage` already uses) acknowledges
   them. This is deliberately a DIFFERENT signal from the existing
   scope-glob/ledger-record-diff leakage check: it answers "whose
   frob:ticket fingerprint is physically in this diff", not "does a
   declared scope overlap a changed path".

2. Already-landed as a first-class outcome: `_check_already_landed`
   recognizes "this ticket's own scope has zero changes on this branch"
   and refuses with `LandError.AlreadyLandedOnMain`, naming the exact
   verify-then-`frob ticket close` recipe instead of falling through to a
   confusing BUG002/TEST016 refusal. Opt-in
   (`--check-already-landed`/`check_already_landed=True`) -- wiring it
   into the default land path regressed 20 tests in
   `tests/test_ticket_land.py`, because an empty scope-diff is ALSO the
   ordinary shape of a docs-only/ledger-only/Done-report-only ticket in
   this repo's own fixture population. Disclosed in the Done report and
   in `docs/modules/tickets.md`'s new section rather than silently
   dropped: this is real, tested, reachable code (both via direct unit
   test and the CLI flag), just not a default-on refusal.

3. Why `CrossTicketLeakage` did not fire for T-1579: two independent
   reasons, documented in `docs/modules/tickets.md#passenger-ticket-
   disclosure-t-1618`. `_find_leaked_tickets` exempts any sibling whose
   ledger state is DONE/DROPPED outright, and even for a non-exempt
   sibling its signal is a NET diff (`--name-only`) -- a file a revert
   commit brought back to byte-identical content simply stops appearing
   as changed, regardless of what OTHER files the same ticket's commits
   touched. Both gaps trace to the leakage check answering "does declared
   scope overlap a change" rather than "whose code is physically here" --
   which is exactly the question `_check_passenger_tickets` answers
   instead, deliberately as a second, complementary check rather than a
   patch to the first (T-1639's own IN_PROGRESS-only refinement is a
   separate, already-considered fix for a DIFFERENT false-positive class
   and must not regress).

Both checks share `_check_cross_ticket_leakage`'s existing
`--allow-cross-ticket` override rather than inventing a second flag.

Disclosed false-positive class for the passenger check (documented in
`docs/modules/tickets.md`, not hidden): a hunk that merely MOVES a
pre-existing `frob:ticket <id>` directive (e.g. a function relocated by
an unrelated refactor) can appear as a fresh addition and flag a
passenger that isn't really new work. The escape hatch exists for this;
the alternative (missing a genuine passenger silently, the actual
incident) is worse.

### Changed
```
 docs/modules/tickets.md                      | 251 ++++++++++++++++++++++
 src/frob/_cli_parsers/_ticket/_progress.py   |  32 +++
 src/frob/app/_config_external.py             |   4 +
 src/frob/app/config.py                       |  18 ++
 src/frob/app/ticket_runner/_land_cmd.py      | 105 +++++++++-
 src/frob/tickets/_land.py                    | 300 ++++++++++++++++++++++++++-
 src/frob/tickets/_land_git_ops.py            |  28 ++-
 src/frob/tickets/_leases.py                  | 240 ++++++++++++++++++++-
 src/frob/tickets/_models.py                  |  16 ++
 tests/test_ticket_leases.py                  | 185 +++++++++++++++++
 tests/test_ticket_work_and_land_finish.py    |  86 ++++++++
 tests/unit/test_land_already_landed.py       | 159 ++++++++++++++
 tests/unit/test_land_cross_ticket_leakage.py | 133 ++++++++++++
 tickets.md                                   | 123 ++++++++++-
 14 files changed, 1657 insertions(+), 23 deletions(-)
```

### Evidence
- `tests/unit/test_land_cross_ticket_leakage.py::TestPassengerTickets::test_refuses_and_lists_every_passenger_by_id` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_cross_ticket_leakage.py::TestPassengerTickets::test_allow_cross_ticket_logs_and_proceeds` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_cross_ticket_leakage.py::TestPassengerTickets::test_no_op_when_only_the_landing_tickets_own_directives_are_present` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_cross_ticket_leakage.py::TestPassengerTickets::test_a_dropped_siblings_still_present_code_is_still_reported` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_already_landed.py::TestAlreadyLandedOnMain::test_refuses_with_a_diagnostic_message_when_scope_diff_is_empty` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_already_landed.py::TestAlreadyLandedOnMain::test_no_op_when_the_ticket_has_real_changes_in_its_own_scope` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_already_landed.py::TestAlreadyLandedOnMain::test_no_op_when_the_ticket_declares_no_scope_at_all` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: 0 error(s), 8148 warning(s), 737 waived
- error-findings: none (measured, zero errors)
