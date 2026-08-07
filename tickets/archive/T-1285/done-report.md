## Done report

Changed:
src/frob/fleet/__init__.py (frob:tests directives added to load_manifest, _git_branch_and_dirty, _gate_summary_probe, _count_diagnostics, _doable_count, route_ticket)
tests/unit/fleet/test_manifest.py::TestLoadManifest.test_load_manifest_schema_invalid
tests/unit/fleet/test_status.py::TestCollectStatus.test_git_branch_and_dirty_subprocess_raises
tests/unit/fleet/test_status.py::TestCollectStatus.test_git_branch_and_dirty_clean_tree_stays_not_dirty
tests/unit/fleet/test_status.py::TestCollectStatus.test_gate_summary_probe_subprocess_raises
tests/unit/fleet/test_status.py::TestCollectStatus.test_gate_summary_probe_non_json_output
tests/unit/fleet/test_status.py::TestCollectStatus.test_count_diagnostics_ignores_unknown_severities
tests/unit/fleet/test_status.py::TestCollectStatus.test_doable_count_missing_ledger_returns_zero
tests/unit/fleet/test_status.py::TestCollectStatus.test_doable_count_delegates_to_tickets_api
tests/unit/fleet/test_route.py::TestRouteTicket.test_route_ticket_new_ticket_failure_wrapped

All 4 findings at 0.0% branch coverage (load_manifest, collect_status's
helpers _git_branch_and_dirty/_gate_summary_probe/_count_diagnostics/
_doable_count, and route_ticket) were live, reachable code -- none
routed to DEAD gate. Each got a real behavioral test exercising an
untested branch (schema-validation failure, subprocess raise paths,
clean-tree porcelain parsing, non-JSON stdout, unknown-severity
skipping, missing-ledger fallback, and route_ticket's new_ticket-failure
wrapping) -- no assert-True filler, no import-only tests.

Evidence: 9 pytest node ids bound above via frob:tests directives (code)
and `frob ticket evidence` (ticket, --accepts 0/1/2). Fresh
`pytest --collect-only` confirmed every id resolves; full
`tests/unit/fleet/` suite: 23 passed.

Filed: none (no out-of-scope work found).

Gates: `frob check --ticket T-1285` gate:TEST 0 errors (TEST005 fleet
findings resolved); gate:PRE cleared via `frob ticket sweep T-1285`
after the scope widen (tests/unit/fleet/**, docs/modules/fleet.md,
already recorded as scope_changes with actor=logan in a prior session
before this resume). Remaining full-check FAIL was pre-existing
unrelated repo state (a stale PRE001 that sweep fixed); no other errors
in the ticket-scoped run.

### Changed
```
 tickets.md | 44 +++++++++++++++++++++++++++++++++++++++-----
 1 file changed, 39 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/unit/fleet/test_manifest.py::TestLoadManifest::test_load_manifest_schema_invalid` (pytest node id, verified passing when recorded)
- `tests/unit/fleet/test_status.py::TestCollectStatus::test_git_branch_and_dirty_subprocess_raises` (pytest node id, verified passing when recorded)
- `tests/unit/fleet/test_status.py::TestCollectStatus::test_git_branch_and_dirty_clean_tree_stays_not_dirty` (pytest node id, verified passing when recorded)
- `tests/unit/fleet/test_status.py::TestCollectStatus::test_gate_summary_probe_subprocess_raises` (pytest node id, verified passing when recorded)
- `tests/unit/fleet/test_status.py::TestCollectStatus::test_gate_summary_probe_non_json_output` (pytest node id, verified passing when recorded)
- `tests/unit/fleet/test_status.py::TestCollectStatus::test_count_diagnostics_ignores_unknown_severities` (pytest node id, verified passing when recorded)
- `tests/unit/fleet/test_status.py::TestCollectStatus::test_doable_count_missing_ledger_returns_zero` (pytest node id, verified passing when recorded)
- `tests/unit/fleet/test_status.py::TestCollectStatus::test_doable_count_delegates_to_tickets_api` (pytest node id, verified passing when recorded)
- `tests/unit/fleet/test_route.py::TestRouteTicket::test_route_ticket_new_ticket_failure_wrapped` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 9 passed (from 9 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
