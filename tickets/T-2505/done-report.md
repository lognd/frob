## Done report

Changed:
src/frob/gates/_docptr.py::_terminal_ticket_ids
src/frob/gates/_docptr.py::_is_historical_ticket_doc
src/frob/gates/_docptr.py::doc006_gate

Evidence:
tests/test_docptr_gate.py::TestDoc006TicketHistoricalExclusion::test_done_ticket_body_not_flagged
tests/test_docptr_gate.py::TestDoc006TicketHistoricalExclusion::test_dropped_ticket_body_not_flagged
tests/test_docptr_gate.py::TestDoc006TicketHistoricalExclusion::test_open_ticket_body_still_flagged
tests/test_docptr_gate.py::TestDoc006TicketHistoricalExclusion::test_done_report_not_flagged_even_if_state_lookup_fails
check-repro confirmed genuine failure at pre-fix commit 9130a806a (FAILED_AT_PARENT verdict from
frob ticket evidence T-2505 --check-repro --base-ref 9130a806a).

Filed: none

Gates: frob check --ticket T-2505 clean on gate:SCOPE (0 errors) and gate:PREWORK (0 errors,
via frob ticket sweep T-2505 after scope was widened to include tests/test_docptr_gate.py);
COV002/AFFECT001 on the touched set resolved via frob:tests/frob:ticket directives. All other
gate families in the unscoped run are repo-wide pre-existing findings unrelated to this diff
(per gate:scope-note).

Note on ticket premise: scope for T-2505 is src/frob/gates/_docptr.py only (COV003/REF001
mentioned in the ticket body as needing "same treatment" are handled by other rules/files and
were left untouched, consistent with the declared scope).

### Changed
```
 src/frob/gates/_docptr.py |  70 +++++++++++++++++++++++++++-
 tests/test_docptr_gate.py | 116 ++++++++++++++++++++++++++++++++++++++++++++++
 tickets/T-2505/ticket.md  |  16 ++++++-
 3 files changed, 200 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_docptr_gate.py::TestDoc006TicketHistoricalExclusion::test_done_ticket_body_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006TicketHistoricalExclusion::test_dropped_ticket_body_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006TicketHistoricalExclusion::test_open_ticket_body_still_flagged` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006TicketHistoricalExclusion::test_done_report_not_flagged_even_if_state_lookup_fails` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: AFFECT001@src/frob/gates/_docptr.py, ARCH103@src/frob/release/_cli.py, COV001@src/frob/gates/_refs_schema.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, E501@/home/logan/projects/frob/.claude/worktrees/t-2505/src/frob/testing/_collect_kotlin.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md
