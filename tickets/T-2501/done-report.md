## Done report

(rollup close)

All five findings converged on frob.graph.summary as the single provenance
engine, verified today against real code, not just child-ticket state:

- T-2502 (strata fragments): 15 pytest node ids in
  tests/unit/strata/test_fragments.py.
- T-2503 (ambient-vs-enumerated + SYS112 gate): wired into
  src/frob/gates/_sys_selfaudit.py (grep confirms `frob:enforces
  CHK-GATE-SYS112` and the SYS112 dispatch at line 287) and registered in
  src/frob/gates/_waive.py's _KNOWN_GATE_RULES; design/frob.strata carries
  39 `because=` reasons (T-2523 backfill of all 27 pre-existing ambient
  grants plus the new declarations).
- T-2504 (confined-to census, report-only per the epic's own sequencing
  directive): src/frob/graph/summary.py hosts ConfinementState/
  FunctionConfinement/scan_confinement_facts/compute_confinement_summaries
  on the SAME SCC worklist compute_protocol_summaries already builds --
  `git grep -n "scan_confinement_facts\|compute_confinement_summaries" --
  src/frob` shows zero OTHER call sites, confirming no second traversal
  was built ("one engine, not two" held). Real census run: 11545 functions
  scanned, 2989 fs.write sites, 2248 ROOTED / 1 ESCAPED / 740 UNKNOWN,
  committed at tickets/archive/T-2504/census-2026-08-18-raw.json.
  Deliberately never wired into a gate -- disclosed, not silently dropped.
- T-2519 (parameter-position credit follow-up): re-ran the same census,
  measured delta 68 of 727 UNKNOWN closed (9.2%), with the remaining gap
  (public-named helper resolution) disclosed as a real, honest limit
  rather than closed by inflating the credit rule.
- T-2505 (DOC006/COV003/REF001 historical-record scoping): evidenced via
  tests/test_docptr_gate.py::TestDoc006TicketHistoricalExclusion.
- T-2507 (vet resolved-identity boundary matching): evidenced via
  tests/test_vet.py::TestNeedleMatchesResolvedTokenBoundary.
- T-2530 (sealed grant set, structural not just tested): SealedGrantSet's
  only construction path is from_root_node; 4 new pytest node ids plus all
  34 pre-existing T-2502 tests stay green (38 total).

This ticket (T-2501) is an epic with no independent acceptance criteria of
its own (tier: epic, no_scope_declared_reason: "epic: coordination only,
children carry the scopes") -- its claim is the unifying "one engine, not
two" design constraint, verified above against the actual current
src/frob/graph/summary.py content, not merely against child-ticket
close-state.

Verification commands run today:
  git grep -n "parent: T-2501" -- tickets
    -> T-2502, T-2503, T-2504, T-2505, T-2507 (all archived, state: done)
  git grep -n "scan_confinement_facts\|compute_confinement_summaries\|ConfinementState" -- src/frob
    -> all hits confined to src/frob/graph/summary.py itself (no second engine)
  git grep -n "SYS112" -- src/frob
    -> src/frob/gates/_sys_selfaudit.py (frob:enforces + dispatch), src/frob/gates/_waive.py (_KNOWN_GATE_RULES)
  grep -c "because" design/frob.strata
    -> 39

Gates: no new code in this closing change; nothing to run frob check
against beyond the ticket-ledger write itself.
Filed: none new -- all prior findings in this area were already filed and
resolved by the children above.

### Changed
(no changed files detected)

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 60 error(s), 643 warning(s), 863 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/commands/narrative.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-2996/ticket.md, DOC006@tickets/T-3022/ticket.md, DOC006@tickets/T-3023/ticket.md, DOC006@tickets/T-3066/ticket.md, DOC006@tickets/T-3069/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/stats/_agentic.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SELFAUDIT001@design, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_ghio.py, SYS003@tests/test_narrative_migrate.py, TEST001@scripts/branch_stranded_work_analysis.py, TEST001@strata-core/src/graph/model.rs, TEST001@strata-core/src/graph/query.rs, TICK004@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py
