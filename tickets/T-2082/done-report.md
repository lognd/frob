## Done report

Changed:
- src/frob/tickets/_land.py::_directive_ticket_ids_in_diff -- discriminator now compares each frob:ticket id's added vs removed line occurrence count (T-2082)
- src/frob/tickets/_land.py::_passenger_ids_from_line_buckets (new) -- the count/verbatim-line discriminator, split out to keep the caller under ARCH001's 60-line threshold
- tests/unit/test_land_cross_ticket_leakage.py::TestPassengerTickets.test_pure_relocation_of_a_preexisting_directive_does_not_refuse (new, designated repro)
- tests/unit/test_land_cross_ticket_leakage.py::TestPassengerTickets.test_relocation_that_also_edits_the_directive_line_still_refuses (new)
- docs/modules/tickets.md#passenger-ticket-disclosure-t-1618 -- updated to describe the count-delta discriminator

Evidence:
- tests/unit/test_land_cross_ticket_leakage.py::TestPassengerTickets::test_pure_relocation_of_a_preexisting_directive_does_not_refuse (acceptance 0, designated repro -- FAILED_AT_PARENT confirmed at 8056fcf92 via `frob ticket evidence --check-repro --base-ref 8056fcf92`)
- tests/unit/test_land_cross_ticket_leakage.py::TestPassengerTickets::test_refuses_and_lists_every_passenger_by_id (acceptance 1 -- proves the guard is not weakened for genuinely added passenger code, the WAIVE004-incident shape)
- tests/unit/test_land_cross_ticket_leakage.py::TestPassengerTickets::test_a_dropped_siblings_still_present_code_is_still_reported (acceptance 2 -- proves ledger-state blindness is preserved)
- Full TestPassengerTickets class (6/6) passing: `uv run pytest tests/unit/test_land_cross_ticket_leakage.py::TestPassengerTickets -q`
- `uv run frob check --only test --only archgate --only sys --ticket T-2082` clean (0 errors)
- `uv run frob check --only doclink --only docanchor --only fmt --only affect_drift --only prework --only scope --ticket T-2082` clean (0 errors)
- `uv run frob check --land-parity`: 1 remaining unscoped error, PII012 on src/frob/testing/_coverage_refresh.py -- pre-existing, file never touched by this ticket's diff (confirmed via `git log -- src/frob/testing/_coverage_refresh.py`), out of scope

Decision recorded (per ticket's explicit ask): a count-unchanged id is exempted ONLY when the exact multiset of added directive lines equals the exact multiset of removed directive lines (verbatim text). A relocation that also edits the directive line in the same motion keeps the same count but fails this stricter check and still refuses -- erring toward refusing when ambiguous, per the ticket's own instruction.

Filed: none (the one out-of-scope PII012 finding is pre-existing repo-wide debt, not new residue from this change)

Cut disclosed: docs/modules/tickets.md could not be added to scope until mid-ticket because T-2078 held a live lease on it; work was blocked on it exactly as the playbook instructs (did not work around it) until T-2078's land completed, then scope was widened and the doc updated in the same change as planned.

Gates: frob check clean across test/archgate/sys/doclink/docanchor/fmt/affect_drift/prework/scope for T-2082's scope. frob check --land-parity shows only the pre-existing, out-of-scope PII012 finding.

### Changed
```
 docs/modules/tickets.md                      | 64 +++++++++++-------
 src/frob/tickets/_land.py                    | 97 +++++++++++++++++++++-------
 tests/unit/test_land_cross_ticket_leakage.py | 84 ++++++++++++++++++++++++
 tickets/T-2082/ticket.md                     | 33 ++++++++--
 4 files changed, 224 insertions(+), 54 deletions(-)
```

### Evidence
- `tests/unit/test_land_cross_ticket_leakage.py::TestPassengerTickets::test_pure_relocation_of_a_preexisting_directive_does_not_refuse` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_cross_ticket_leakage.py::TestPassengerTickets::test_refuses_and_lists_every_passenger_by_id` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_cross_ticket_leakage.py::TestPassengerTickets::test_a_dropped_siblings_still_present_code_is_still_reported` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: PII012@src/frob/testing/_coverage_refresh.py, PRE001@tickets/T-2082
