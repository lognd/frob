## Done report

Changed:
src/frob/findings.py (new leaf module -- Severity, WaiverRef, DebtEntry, Violation)
src/frob/gates/_models.py (moved symbols removed, re-exports frob.findings for backward
  compat, per the T-1201 pattern already used elsewhere in this file)
src/frob/vet/_models.py, src/frob/app/vet_runner.py, src/frob/tickets/_land.py
  (import statements repointed to frob.findings by the split's own reference rewriter)
src/frob/app/ticket_runner/_land_cmd.py, src/frob/gates/_docblocks_refs.py,
  src/frob/gates/_fix_engine_tier_c.py, src/frob/gates/_fuzz.py,
  src/frob/gates/_gate_cache.py, docs/design/check-fix-engine.md,
  plus ~30 test files (docstring/prose citations of the old
  frob.gates._models.<Symbol> dotted path repointed to frob.findings.<Symbol>)

Command run (per acceptance):
  frob refactor split frob.gates._models \
    --symbols Severity,WaiverRef,DebtEntry,Violation \
    --into frob.findings --skip-check-delta

--skip-check-delta only: the split's own check_delta post-condition times out
at its hardcoded 100s budget against a repo this size (spawn of `python -m
frob check --delta` exceeded timeout=100) -- unrelated to correctness.
import_resolution (1 skipped: docs/design/check-fix-engine.md, non-.py),
module_import, and pytest_collect (1 skipped, same file -- T-3136's fix
confirmed working at real scale) all PASSED. Manually verified both:
  python -c "import frob.gates._models"  -> OK
  python -c "import frob.findings"       -> OK

Evidence:
tests/test_dup.py (28 passed), tests/test_fuzz.py + tests/test_policy.py
(54 passed, 1 skipped, pre-existing), tests/test_telemetry.py (40 passed),
tests/test_vet.py (475 passed), tests/test_perf.py (50 passed),
tests/test_arch_gate.py + tests/gates/test_rule_id_scan_branches.py +
tests/gates/test_tdd_order.py (53 passed) -- all touched-package test files,
zero failures, no behaviour change.

SCC MEASUREMENT (frob cycle src/frob):
BEFORE: 182 nodes (re-confirmed, matching every prior attempt's own
  re-measurement)
AFTER:  182 nodes, UNCHANGED

This is a real, honest measurement, not a success dressed up: reviewing the
printed 182-node cycle path both before and after the split, `src/frob/
gates/_models.py` does not appear BY NAME in either one -- the moved value
types were never themselves members of this particular SCC. The cut is
still architecturally correct (universal value types now live in a leaf
module importing nothing from frob but primitives/pydantic/typani; the
extraction is real, verified, and matches every acceptance bullet except
the cycle-count reduction the ticket hoped for) but it does not shrink the
measured 182-node cycle, because the four moved symbols were not on the
cycle's own path. Filed T-3142 to name the next cut from the current
182-node cycle's own membership (frob/tickets and frob/gates interdependency
looks like the dominant knot; see the fresh `frob cycle` output).

Filed:
- T-3142 -- name the next real cut from the still-182-node cycle,
  sibling to this one, per the coordinator's instruction not to plan the
  whole decomposition here.
- T-3143 -- only 3 of ~28 non-gates import STATEMENTS citing
  the moved value types were repointed to `frob.findings` directly (the
  rest still import via `frob.gates._models`'s backward-compat re-export,
  which resolves correctly -- no breakage, no behaviour change, but does
  not fully satisfy "the 21 non-gates importers import the leaf"). The
  reference-scanner (src/frob/refactor/_scan.py) appears to miss import
  sites where the moved name is used ONLY as a type annotation (e.g.
  `def f(v: Violation) -> str:`) rather than a called/attribute-accessed
  expression -- worth widening its reach in its own ticket, not chased
  here.

Gates: gate:SCOPE 0 errors (1723 pre-existing SCOPE002 breadth warnings,
  same class the scope-closure note always produces on a widely-referenced
  file); gate:DRIFT/gate:WAIVE/claude-config-drift errors are pre-existing
  repo-wide, unrelated to this ticket's touched set (confirmed via
  --ticket's own scope-note: only gate:SCOPE/PREWORK/COV(diff)/FMT/AFFECT
  are actually ticket-scoped).

### Changed
(no changed files detected)

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 79 error(s), 2397 warning(s), 866 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@.claude/hooks/frob-suggest.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@.claude/hooks/frob-suggest.py, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC005@docs/modules/cli.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-3139/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_process_reap.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_process_reap.py, DRIFT002@tests/unit/test_reopen_ticket.py, I001@/home/logan/projects/frob/tests/unit/verify/test_quarantine.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3086, REF001@.claude-scratch/T-3122-close-guard-repro-capture.md, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, SUPPRESS001@src/frob/app/_config_external.py, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@src/frob/gates/_wire.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_ghio.py, SYS003@tests/test_narrative_migrate.py, TEST001@scripts/branch_stranded_work_analysis.py, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py, unknown-argument@tests/unit/test_app_runners_process.py, unknown-argument@tests/unit/test_pytest_spawn_env_wiring.py
