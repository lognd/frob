## Done report

MEASURED: `frob cycle src/frob` on the current tree (post-T-3143) still
reports one 182-node SCC, unchanged from T-3086's own baseline -- the
node SET is the same across two independent runs (order differs, DFS
discovery order is not stable, membership is).

IMPORTANT CORRECTION before naming a cut: the printed cycle text is SCC
membership order (from `frob.cycle.graph.find_cycles`'s Tarjan pass), not
a validated walk of real edges between each consecutive printed pair --
checked several consecutive pairs directly (e.g.
`gates/_rule_id_scan.py` next to `tickets/_new_gate_rule_acceptance.py`
in the printout) and found no real Python import between them in either
direction, only a docstring mention of the dotted path. Any cut has to
be justified against an actual `import`/`from` statement, not adjacency
in the CLI's printed text.

Checked the three ticket read before proposing anything:
- T-2667 (serve/tickets/testing/app cycle, scope
  `src/frob/serve/_tools.py`) -- a DIFFERENT package quartet
  (serve<->tickets<->testing<->app._daemon_proxy), does not touch gates.
- T-2835 (`_close_cmd`/`_land_cmd`/`_lifecycle` decomposition seams) --
  a LARGE001 line-count concern about those three files' internal size,
  not an import-cycle concern.
- T-2202 (`frob check --only cycle` genuinely failing) -- names four
  real, import-verified leaf clusters via the SAME resolve_local_import
  path `frob cycle` also uses; Leaf 3 is tickets/-only
  (`_accept.py`/`_setters.py`/`_land_finalize.py`/`_land_verify.py`), no
  gates involvement.

None of the three cover the edge this ticket names, so a new sibling was
filed rather than duplicating: T-3155 -- "Extract
evidence_covers_scope out of frob.gates to break the gates<->tickets
edge" (renumbers to its real id at land). Real, line-verified edges
backing it:

1. `src/frob/gates/__init__.py:297` -- eager, top-level
   `from frob.tickets import Ticket, TicketQueue, TicketState,
   load_queue` (frob.gates' OWN package init depends on frob.tickets).
2. `src/frob/app/ticket_runner/_close_cmd.py:300` -- deferred,
   function-local `from frob.gates import evidence_covers_scope`, the
   SAME `frob.gates.__init__` module edge 1 lives in -- confirmed this
   is already a KNOWN, deliberately-deferred edge (its own author
   deferred the import specifically to avoid an eager cycle), per
   `evidence_covers_scope`'s own docstring naming
   `frob.app.ticket_runner`'s `_close`/`_land` as its only caller
   outside frob.gates.

Filed: T-3155 (renumbers at land)

Proposed cut (named, not attempted, per T-3086's own directive): move
`evidence_covers_scope` (and its private D-02 helpers) out of
`frob.gates.__init__` into `frob.tickets` (or a neutral leaf) -- it
operates on `Ticket`/scope data, and its one gates-side input
(`GraphSnapshot`) is already dependency-injected by its own design (the
docstring notes the RESULT is passed into
`frob.tickets.transition`/`land`'s `covers_scope` parameter, i.e. the
inverse direction already avoids an import). This removes
`_close_cmd.py`'s need to import `frob.gates` for this call without
touching `_tickets_gate.py`'s separate (likely inherent) gates->tickets
edge -- deliberately not addressed here, one cut at a time.

### Changed
```
 tickets/T-3142/done-report.md      |  74 +++++++++++++++++++++++++++
 tickets/T-3142/ticket.md           |  36 +++++++++++--
 tickets/T-3155/ticket.md | 102 +++++++++++++++++++++++++++++++++++++
 3 files changed, 209 insertions(+), 3 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 119 error(s), 677 warning(s), 872 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@.claude/hooks/frob-suggest.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@.claude/hooks/frob-suggest.py, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC005@docs/modules/cli.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-3139/ticket.md, DOC006@tickets/T-3155/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_process_reap.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_process_reap.py, DRIFT002@tests/unit/test_reopen_ticket.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, REF001@.claude-scratch/T-3122-close-guard-repro-capture.md, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/conftest.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, SUPPRESS001@src/frob/app/_config_external.py, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@src/frob/app/vet_runner.py, SYS003@src/frob/gates/_docblocks_refs.py, SYS003@src/frob/gates/_fix_engine_tier_c.py, SYS003@src/frob/gates/_fuzz.py, SYS003@src/frob/gates/_gate_cache.py, SYS003@src/frob/gates/_models.py, SYS003@src/frob/gates/_wire.py, SYS003@src/frob/vet/_models.py, SYS003@tests/gates/test_rule_id_scan_branches.py, SYS003@tests/gates/test_tdd_order.py, SYS003@tests/test_arch_gate.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_docblocks_gate.py, SYS003@tests/test_docptr_gate.py, SYS003@tests/test_fuzz.py, SYS003@tests/test_gates_suppress.py, SYS003@tests/test_ghio.py, SYS003@tests/test_lang_conformance_gate.py, SYS003@tests/test_narrative_migrate.py, SYS003@tests/test_pii_structural_gate.py, SYS003@tests/test_refs_gate.py, SYS003@tests/test_registry_exhaustiveness.py, SYS003@tests/test_registry_staleness.py, SYS003@tests/test_secrets_gate.py, SYS003@tests/test_todo_fmt_gate.py, SYS003@tests/test_vet.py, SYS003@tests/unit/gates/test_doc011.py, SYS003@tests/unit/gates/test_refs.py, SYS003@tests/unit/gates/test_sys_selfaudit.py, SYS003@tests/unit/security/test_redact.py, SYS003@tests/unit/strata/test_cve_fingerprint_scan.py, SYS003@tests/unit/test_arch_table_schema.py, SYS003@tests/unit/test_docblocks_table_schema.py, SYS003@tests/unit/test_dup_graph_table_schema.py, SYS003@tests/unit/test_flag_coverage_gate.py, SYS003@tests/unit/test_gates_table_schema.py, SYS003@tests/unit/test_native_table_schema.py, SYS003@tests/unit/test_profile_table_schema.py, SYS003@tests/unit/test_refs_schema.py, SYS003@tests/unit/test_test_table_schema.py, SYS003@tests/unit/test_testing_table_schema.py, SYS003@tests/unit/test_toplevel_scalar_schema.py, SYS003@tests/unit/vet/test_taint.py, TEST001@scripts/branch_stranded_work_analysis.py, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py, unknown-argument@tests/unit/test_app_runners_process.py, unknown-argument@tests/unit/test_pytest_spawn_env_wiring.py
