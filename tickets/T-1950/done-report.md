## Done report

Root cause: LAND-PROOF and scripts/verify_lands.py both only ever check ANCESTRY
(is this commit reachable from main, and does the ticket read done) -- neither
checks CONTENT (does this specific commit actually contain the change its own
ticket claims). `_check_already_landed` (T-1618/T-1675) already existed to
catch the confusing consequence of a passenger-ticket land, but its only
positive signal (T-1675: the ticket's own ledger record already reads `done`
on base_ref) cannot see the complementary shape this ticket measured for real:
T-1720's land (48f49d78b8db) contained ONLY rapid-debt.jsonl and a one-line
ticket.md change, because its real feature had already ridden onto main under
T-1922's earlier, `--allow-cross-ticket` land (b508b0ad3eec) -- BEFORE T-1720
itself ever landed, so T-1720's own record was still non-done on base_ref at
land time, and T-1675's signal stayed silent. Both lands reported `LAND-PROOF
verified=True` and both passed `verify_lands.py`.

Fix: added a second, independent positive signal to `_check_already_landed`:
`_ticket_directive_present_on_ref` checks whether base_ref's current tree
already contains a literal `frob:ticket <ticket.id>` directive anywhere under
src/ -- written by this repo's own convention onto every touched public
symbol, never by an external replacement, and never present for a ticket that
has contributed no code anywhere yet (so a docs-only/ledger-only first-time
land, T-1675's own regression target, stays unaffected). Refusing on EITHER
signal (extracted into a shared `_refuse_already_landed` helper so the two
share one message/remedy) closes the T-1950 gap without touching T-1675's
existing false-positive guard.

Also hit and fixed a self-inflicted ARCH001 (`_check_already_landed` grew past
the 60-line function-length threshold after the new signal was added) by
trimming the docstring and inline comments -- the function's full history and
both signals' rationale now live in docs/modules/tickets.md's already-landed
section instead of being repeated in the source docstring.

Verification: tests/unit/test_land_already_landed.py (6 of 6 pass, including
two new tests: one constructing a land whose commit touches nothing in its own
scope because a sibling carried it first (asserts refusal, naming the
ticket), one confirming the check stays a no-op when neither positive signal
is present). tests/test_ticket_land.py, tests/unit/test_land_step_ordering.py,
tests/unit/test_land_cross_ticket_leakage.py all pass alongside it (294 total).
`frob check --ticket T-1950` clean across gates-fast/gates-native/gates-
security. `frob check --land-parity` clean.

Evidence disclosure (BUG002/T-1929 footgun, documented per playbook section
0.6, not silently waived): `--check-repro` on the new refusal test returns
NO_VERDICT (exit 5, collection failure) at this ticket's own parent commit --
a brand-new test node cannot collect against a checkout that predates the
symbols it exercises (`_ticket_directive_present_on_ref`, `_refuse_already_
landed` do not exist there), the same structural gap T-1907/T-1884/T-1882/
T-1911 already hit. Not designated as the repro id; the other three evidence
ids (two existing regression tests plus the new no-op guard test) are real,
observed-passing evidence for this land.

### Changed
```
 tickets/T-1950/ticket.md | 38 ++++++++++++++++++++++++++++++++++++--
 1 file changed, 36 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/test_land_already_landed.py::TestAlreadyLandedOnMain::test_refuses_when_a_sibling_carried_this_tickets_content_before_it_ever_landed` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_already_landed.py::TestAlreadyLandedOnMain::test_no_op_when_no_frob_ticket_directive_for_this_id_exists_on_main` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_already_landed.py::TestAlreadyLandedOnMain::test_no_op_when_the_ticket_has_real_changes_in_its_own_scope` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_already_landed.py::TestAlreadyLandedOnMain::test_no_op_for_a_docs_only_ticket_whose_scope_diff_is_empty_but_not_yet_landed` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 0 error(s), 1367 warning(s), 706 waived
- error-findings: none (measured, zero errors)
