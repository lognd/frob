## Done report

Narrowed the FEATURE-kind implicit CLI-wiring grant from a whole-package
glob (`src/frob/app/ticket_runner/**`) to the single dispatch/re-export hub
(`src/frob/app/ticket_runner/__init__.py`), which is the one file a new
`frob ticket <verb>` structurally requires per the package's own module
docstring. This directly shrinks the incident this ticket was filed from:
an in-progress FEATURE ticket that never writes under `ticket_runner/`
still claimed the entire package under the old rule and blocked unrelated
lands with CrossTicketLeakage.

The remaining required items (disclose effective scope in `frob ticket
show`, name WHY a file is claimed in the CrossTicketLeakage refusal, make
`scope --remove` refuse/warn on a still-implicitly-covered glob, and the
"better" grant-on-use redesign) all require touching `_land.py`,
`ticket_runner`'s query/show path, and `_cli_parsers/**`, none of which
this ticket's declared scope (`src/frob/tickets/_models.py`) covers.
Filed as a follow-up draft rather than expanding scope silently.

### Changed
```
 rapid-debt.jsonl                   |  1 +
 src/frob/tickets/_models.py        | 13 ++++++++++++-
 tests/test_tickets.py              | 31 +++++++++++++++++++++++++++++++
 tickets/T-1848/done-report.md      | 35 +++++++++++++++++++++++++++++++++++
 tickets/T-1848/ticket.md           | 19 ++++++++++++++++---
 tickets/T-1855/ticket.md | 23 +++++++++++++++++++++++
 6 files changed, 118 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/test_tickets.py::TestScopeMatching::test_feature_kind_implies_cli_wiring_files_in_scope` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestScopeMatching::test_cli_wiring_files_resolve_to_real_paths_on_disk` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestScopeMatching::test_non_feature_kind_does_not_imply_cli_wiring_files` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestScopeMatching::test_cli_wiring_grant_does_not_cover_arbitrary_ticket_runner_files` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 5 error(s), 783 warning(s), 742 waived
- error-findings: DOCENUM001@docs/modules/gates.md, PRE001@tickets/T-1848, SEC110@.claude/hooks/dispatch-telemetry.py, invalid-argument-type@src/frob/strata/_sync_may.py, invalid-type-form@src/frob/strata/_sync_may.py
