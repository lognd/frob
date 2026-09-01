## Done report

Round 3 fix landed; see prior Done report narrative above for full detail.

### Changed
```
 src/frob/graph/cache.py       | 385 ++++++++++++++++++++++++++++++------------
 tickets/T-3634/done-report.md |  68 ++++++++
 2 files changed, 349 insertions(+), 104 deletions(-)
```

### Evidence
- `tests/unit/test_graph_cache.py::TestRecreateNeverExposesASchemaIncompleteDb::test_two_processes_connecting_concurrently_never_see_no_such_table_meta` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 27 error(s), 4193 warning(s), 903 waived
- error-findings: ARCH102@src/frob/process/_lock.py, ARCH102@src/frob/tickets/_land_squash.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV003@tests/test_ci_workflow_matrix.py, COV007@src/frob/strata/_capacity.py, DEPR006@frob-deprecated-baseline.lock.json, DOC006@tickets/T-3628/ticket.md, DOC006@tickets/T-3629/ticket.md, DRIFT002@tests/ticket_land_suite/test_archive.py, DRIFT002@tests/ticket_land_suite/test_claim_close.py, DRIFT002@tests/ticket_land_suite/test_dirt_ownership.py, DRIFT002@tests/ticket_land_suite/test_land_core.py, DRIFT002@tests/ticket_land_suite/test_land_lock.py, DRIFT002@tests/ticket_land_suite/test_land_plan.py, DRIFT002@tests/ticket_land_suite/test_ledger_splice.py, DRIFT002@tests/ticket_land_suite/test_push.py, DRIFT002@tests/ticket_land_suite/test_release.py, DRIFT002@tests/ticket_land_suite/test_verify_intent.py, DRIFT002@tests/ticket_land_suite/test_verify_reset.py, DRIFT002@tests/ticket_land_suite/test_waive_deletion.py, DRIFT002@tests/ticket_land_suite/test_wip.py, F401@/home/logan/projects/frob/.claude/worktrees/t-3634/tests/test_ticket_land.py, OPAQUE001@src/frob/app/_config_external.py, REL001@src/frob/__init__.py, SEC110@tests/ticket_land_suite/test_wip.py, TEST001@src/frob/strata/_models.py, WAIVE011@frob-ratchet.lock.json
