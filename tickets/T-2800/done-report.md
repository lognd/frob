## Done report

Changed (pure import-order, no behavior change):
- tests/conftest.py
- tests/test_ticket_land.py
- tests/test_ticket_land_proof_claims.py
- tests/test_ticket_work_and_land_finish.py
- tests/test_tickets_acceptance.py
- tests/test_tickets_lease.py
- tests/test_tickets_organization.py
- tests/test_tickets_priority.py
- tests/unit/strata/test_selfconform.py
- tests/unit/test_app_runners_batch6.py
- tests/unit/test_app_runners_json_guard_t2492.py
- tests/unit/test_app_runners_t2395_contention.py

Re-measured (not trusted from the ticket body): 31 I001 findings across
24 files remained after batch 1 (T-2788) landed, via a fresh
`uv run frob check --json --budget 500` JSON filter for code=="I001" in
this worktree, 2026-08-21. This batch covers 12 of those 24.

Evidence: ran the 12 touched files' own test suites directly --
tests/test_tickets_acceptance.py/_lease.py/_organization.py/_priority.py
plus the 3 unit/test_app_runners_* files collected 191/191 passing.
tests/test_ticket_land_proof_claims.py and
tests/test_ticket_work_and_land_finish.py show real failures, but the
IDENTICAL failure set reproduces against unmodified main at the repo
root (no diff at all) -- confirmed pre-existing/environmental
(EMPTY-scope ticket-start and LAND-PROOF assertion issues unrelated to
import ordering), not caused by this change.

Filed: none -- remaining 12 I001 files (src/frob/tickets/_setters.py
plus 8 tests/ files) and the 3 src/frob/gates/ files already tracked
under the parent T-2373 for a future batch.

Gates: frob check --ticket scoped to this ticket clean for
gate:SCOPE/gate:PREWORK once scope was declared for these 12 files.

Severity promotion NOT part of this batch: still deferred until every
sibling batch of T-2373 lands (restated per coordinator direction --
flipping I001 to error early would red main for not-yet-fixed sibling
files that are already accounted for on the parent epic).

### Changed
```
 tests/conftest.py                               |   4 +-
 tests/test_ticket_land.py                       |   2 +-
 tests/test_ticket_land_proof_claims.py          |   7 +-
 tests/test_ticket_work_and_land_finish.py       |   3 +-
 tests/test_tickets_acceptance.py                |   6 +-
 tests/test_tickets_lease.py                     |   5 +-
 tests/test_tickets_organization.py              |   5 +-
 tests/test_tickets_priority.py                  |   3 +-
 tests/unit/strata/test_selfconform.py           |   2 +-
 tests/unit/test_app_runners_batch6.py           |   2 +-
 tests/unit/test_app_runners_json_guard_t2492.py |   3 +-
 tests/unit/test_app_runners_t2395_contention.py |   1 -
 tickets/T-2373/ticket.md                        |   2 +-
 tickets/T-2800/ticket.md              | 102 ++++++++++++++++++++++++
 14 files changed, 127 insertions(+), 20 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 18 error(s), 1315 warning(s), 712 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1688, COV003@tickets/T-2365, CYCLE001@src/frob/__init__.py, DOC006@docs/audits/test005-zero-classification-t1418.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, PERF004@src/frob/tickets/_evidence.py, REG002@docs/design/registry/check-coverage.yaml, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SYS003@src/frob/check/__init__.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md
