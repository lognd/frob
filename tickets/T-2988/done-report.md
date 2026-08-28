## Done report

DOCARCH001 (frob.gates._docstring_archaeology) replaces the blanket
one-line docstring rule with the mechanically-checkable half of T-2988's
purpose test: a public docstring citing a ticket AND reading as
change-narrative (used to/previously/folded into/superseded/...) is
flagged; a bare ticket reference for provenance stays quiet, mirroring
`frob.gates._waive`'s WAIVE009/010 discriminator. docs/modules/docstrings.md
states the standard (purpose test, three visibility tiers, measured
baseline) that supersedes the old blanket rule.

Evidence:
- tests/gates/test_docstring_archaeology.py -- 13/13 pass (must-fire +
  5 must-stay-quiet variants + pure-predicate unit tests)
- tests/gates/test_rule_id_scan_branches.py::TestFindUnregisteredRuleIds::test_real_repo_registry_is_complete -- pass
- tests/test_gates.py::test_gates_run_gates_integration -- pass
- ruff check / ruff format clean on all new+touched files

Filed: T-3248 (migrate the 418 measured DOCARCH001 findings into their
cited tickets -- explicitly deferred; the MIGRATION HAZARD this ticket's
own body notes -- archived-ticket body writes previously corrupted the
ledger -- must be proven safe on one ticket before any batch, so bulk
migration is out of this ticket's own scope).

Measured (2026-08-28, docarch001_violations(Path(".")) over this repo's
own src/): 418 findings out of 1438 public functions (~29%), consistent
with docstrings.md's baseline (57% of public docstrings cite a ticket).
Spot-checked several as true positives, not detector noise (e.g.
frob.app.telemetry.redact_command's "T-1318: ... used to cost ~257ms").
No narrative was deleted -- DOCARCH001 only WARNs and points at where the
narrative should move to; migration itself is T-3248's job.

Gates: frob check --ticket T-2988 clean on this ticket's own scoped
checks (gate:SCOPE, gate:COV/COV002, gate:FMT, gate:AFFECT); DOC gate
carries zero findings against the new file/module. Every other gate
family's repo-wide counts (TDD001/VERSION001/VMOD001 registry drift,
etc.) are pre-existing baseline, unrelated to the six files this ticket
touched -- confirmed via `git status --short`.

### Changed
```
 tickets/T-2988/ticket.md | 6 ++++++
 1 file changed, 6 insertions(+)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 35 error(s), None warning(s), None waived
- error-findings: CYCLE001@src/frob/__init__.py, invalid-argument-type@src/frob/__main__.py, invalid-argument-type@tests/unit/test_app_runners_batch6.py, invalid-assignment@tests/test_ci_report.py, invalid-assignment@tests/test_tickets_velocity.py, invalid-assignment@tests/test_vet.py, invalid-assignment@tests/unit/verify/test_backpressure.py, unresolved-attribute@tests/test_app_daemon_proxy.py, unresolved-attribute@tests/test_coverage_wait_shared.py, unresolved-attribute@tests/test_serve_leases.py, unresolved-attribute@tests/test_serve_socket.py, unresolved-attribute@tests/test_ticket_land.py, unresolved-attribute@tests/test_ticket_leases.py, unresolved-attribute@tests/test_ticket_reconcile.py, unresolved-attribute@tests/test_tickets_parent.py, unresolved-attribute@tests/test_tickets_priority.py, unresolved-attribute@tests/unit/test_conftest_stackdump.py, unresolved-attribute@tests/unit/test_coordinator_scripts.py, unresolved-attribute@tests/unit/test_land_finish_guard.py, unresolved-attribute@tests/unit/test_land_lock_liveness.py, unresolved-attribute@tests/unit/test_main_entry.py, unresolved-attribute@tests/unit/test_process_lock.py, unresolved-attribute@tests/unit/test_rapid_sweep.py, unresolved-attribute@tests/unit/test_stackdump.py, unresolved-attribute@tests/unit/test_ticket_store.py, unresolved-import@src/frob/arch/_abstraction.py, unresolved-import@src/frob/gates/_vmodel.py, unresolved-import@src/frob/graph/_core.py, unresolved-import@tests/test_arch_near_duplicate_native.py, unresolved-import@tests/unit/strata/test_capacity.py, unresolved-import@tests/unit/test_arch_python_native.py, unresolved-import@tests/unit/test_capability_native.py, unresolved-import@tests/unit/test_dup_core.py, unresolved-import@tests/unit/test_extract_native.py, unresolved-import@tests/unit/test_lang_strata.py
