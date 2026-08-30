## Done report

T-3466: implemented CrossTicketLeakage (T-1355) as a real frob check gate rule, CROSSTICKET001, the smallest version that lets frob check --ticket <id> inside a worktree run it -- no new CLI plumbing needed, frob.tickets._land._resolve_primary_checkout (T-1003) already answers 'which checkout is the ledger authoritative copy' from the worktree alone. cross_ticket_leakage_gate(root, ticket_id) lives in frob.tickets._land (not frob.gates._land_parity, since unlike LANDPARITY001/002 it needs a ticket_id), split into three functions (_cross_ticket_leakage_findings/_cross_ticket_leakage_violations/cross_ticket_leakage_gate) to stay under LANDPARITY002's own ARCH001 threshold -- LANDPARITY002 refused the first single-function draft, confirming the new gate is itself wired correctly. Reuses _check_cross_ticket_leakage's own pure pieces (_branch_changed_files/_machinery_owned_leakage_exempt_paths/_load_leakage_ledgers/_find_leaked_tickets) to build Violations instead of re-invoking the log-and-refuse land-time function. Wired into frob.gates.__init__'s dispatch (_ALL_GATES/_CANONICAL_GATE_ORDER/dispatch dict) with st.ticket.id threaded through, mirroring release_gate's ticket_id-optional shape. Registered CROSSTICKET001 in frob.gates._waive's _KNOWN_GATE_RULES and docs/design/registry/check-coverage.yaml's CHK-GATE-CROSSTICKET001 entry, and documented in docs/modules/gates.md. Land-time enforcement (_check_cross_ticket_leakage's preflight and the T-1932 post-mutation re-check) is unchanged -- this only makes the same finding visible earlier.

### Changed
```
 tickets/T-3466/done-report.md | 19 +++++++++++++++++++
 tickets/T-3466/ticket.md      | 38 +++++++++++++++++++++++++++++++++++++-
 2 files changed, 56 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_cross_ticket_leakage_gate.py::TestCrossTicketLeakageGate::test_leaked_sibling_scope_fires` (pytest node id, verified passing when recorded)
- `tests/unit/test_cross_ticket_leakage_gate.py::TestCrossTicketLeakageGate::test_no_ticket_id_is_quiet` (pytest node id, verified passing when recorded)
- `tests/unit/test_cross_ticket_leakage_gate.py::TestCrossTicketLeakageGate::test_no_leaked_tickets_is_quiet` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 18 error(s), 4886 warning(s), 908 waived
- error-findings: AFFECT001@src/frob/tickets/_land.py, COV003@tests/unit/test_scaffold_project.py, DEPR006@frob-deprecated-baseline.lock.json, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, LARGE001@.claude/hooks/root-write-guard.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PRE001@tickets/T-3466, REL001@src/frob/__init__.py, SELFAUDIT001@src/frob/gates/_land_parity.py, SELFAUDIT001@src/frob/gates/_policy_weakening_gate.py, SELFAUDIT001@tests/unit/strata/test_strata_core_gil.py, SELFAUDIT001@tests/unit/test_cross_ticket_leakage_gate.py, SELFAUDIT001@tests/unit/test_land_parity_gate.py, SELFAUDIT001@tests/unit/test_sync_claude_config_stale_guard_t3408.py, SELFAUDIT001@tests/unit/verify/test_worker.py, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
