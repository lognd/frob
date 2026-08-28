## Done report

Changed:
- src/frob/tickets/_models.py::scope_has_python_surface -- new shared
  predicate (real filesystem check via frob.excludes.iter_files, never
  inferred from ticket.kind or glob text alone).
- src/frob/gates/__init__.py::evidence_covers_scope -- close-time D-02:
  cmd: evidence now also counts when scope_has_python_surface is False.
- src/frob/tickets/_evidence.py::_check_cmd_evidence_kind (record-time,
  `frob ticket evidence --evidence-cmd`) and
  _done_transition_evidence_kind_and_scope_guard (close-time re-check):
  same widened condition.
- src/frob/tickets/_land_merge.py::_validate_evidence_kind_consistency
  (land-time re-check): same widened condition.
- docs/modules/tickets.md#public-api -- documents the new predicate and
  the widened add_cmd_evidence route (AFFECT001).
- tests: 6 new tests (3 must-fire/must-stay-quiet pairs, one per
  checkpoint layer: D-02 close-time, record-time CLI, land-time guard).

Deliberately the smallest fix, not a new evidence format: cmd: evidence
(T-0215, already generic -- any command's exit status + output digest)
is the existing channel; the only change is WHEN it is trusted. A scope
with even one real Python file still requires kind in
CMD_EVIDENCE_ALLOWED_KINDS, unchanged -- this can never loophole an
actual Python code change into closing on an unrelated command.

Both gaps T-3147's audit named turn out to reduce to the SAME root
cause (frob's obligation graph only ever indexes Python source, so
D-02's normal routes structurally cannot see a Rust crate or a plain
doc file) and are closed by the SAME single predicate -- no separate
mechanism needed for "Rust" vs "docs-only bug".

Considered and rejected: inferring "no Python surface" from ticket.kind
alone (the ORIGINAL, too-narrow carve-out T-3147 found the gap in) or
from scope glob TEXT alone (`strata-core/src/graph/**` and
`src/frob/gates/**` are both bare directory globs with no extension
info -- indistinguishable without touching the filesystem, so a
text-only heuristic would have to either reject T-3005's own exact
shape or accept an ambiguous glob that might really be Python). Settled
on a real `iter_files` check instead, threading `root` through the
three checkpoints that did not already have it -- the minimum needed
for correctness, not a new evidence format or ticket field.

An empty scope, or a non-empty scope resolving to NO real file at all
(a typo, a fixture path, work not yet committed), is treated as
UNMEASURABLE -> conservative True (Python-coverable, no exemption) --
confirmed against the pre-existing
test_evidence_covers_scope_false_for_code_kind_with_cmd_shaped_evidence
fixture (a fictional `src/pkg/` scope that resolves to nothing on
disk), which stays green.

Filed: none new (T-3162, filed while resolving T-3150,
carried to main by this same land).

Gates: `frob check --only affect_drift --ticket T-3156` clean for this
ticket's own touched symbols (0 unwaived AFFECT001 against
scope_has_python_surface/add_cmd_evidence/evidence_covers_scope).
Test suites run clean: tests/test_evidence_integrity.py (44 passed),
tests/test_tickets_cmd_evidence.py (36 passed),
tests/test_gates_tickets_hygiene.py + test_tickets*.py bundle (375
passed), tests/test_ticket_land.py (329 passed, 5 pre-existing failures
confirmed to reproduce IDENTICALLY against unmodified main at the
primary root -- TestGitSubprocessFailures::test_squash_command_failure/
test_final_commit_failure, TestSigkillMidStaging (x2),
TestSquashSpliceLedgerChurn::test_concurrent_write_between_squash_and_
splice_survives_land -- unrelated to this change, not caused by it).

### Changed
```
 docs/modules/tickets.md            |  22 +++++--
 rapid-debt.jsonl                   |   1 +
 src/frob/gates/__init__.py         |  23 ++++---
 src/frob/tickets/_evidence.py      |  49 ++++++++++-----
 src/frob/tickets/_land.py          |   2 +-
 src/frob/tickets/_land_merge.py    |  26 +++++---
 src/frob/tickets/_models.py        |  44 +++++++++++++
 tests/test_evidence_integrity.py   |  43 +++++++++++++
 tests/test_tickets.py              |   8 ++-
 tests/test_tickets_cmd_evidence.py | 123 ++++++++++++++++++++++++++++++++++---
 tickets/T-3150/done-report.md      |  67 ++++++++++++++++++++
 tickets/T-3153/ticket.md           |   5 ++
 tickets/T-3156/ticket.md           |   9 ++-
 tickets/T-3162/ticket.md |  61 ++++++++++++++++++
 14 files changed, 435 insertions(+), 48 deletions(-)
```

### Evidence
- `tests/test_evidence_integrity.py::TestD02ScopeBinding::test_evidence_covers_scope_true_for_bug_kind_with_no_python_surface` (pytest node id, verified passing when recorded)
- `tests/test_evidence_integrity.py::TestD02ScopeBinding::test_evidence_covers_scope_false_for_bug_kind_with_real_python_surface` (pytest node id, verified passing when recorded)
- `tests/test_tickets_cmd_evidence.py::TestKindGate::test_bug_kind_with_no_python_surface_scope_closes` (pytest node id, verified passing when recorded)
- `tests/test_tickets_cmd_evidence.py::TestKindGate::test_bug_kind_with_real_python_surface_scope_still_rejected` (pytest node id, verified passing when recorded)
- `tests/test_tickets_cmd_evidence.py::TestKindConsistencyAtClose::test_land_validate_closeable_accepts_bug_kind_no_python_scope` (pytest node id, verified passing when recorded)
- `tests/test_tickets_cmd_evidence.py::TestKindConsistencyAtClose::test_land_validate_closeable_refuses_bug_kind_real_python_scope` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 124 error(s), 930 warning(s), 881 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@.claude/hooks/frob-suggest.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@.claude/hooks/frob-suggest.py, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC005@docs/modules/cli.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-3155/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_process_reap.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT001@scripts/fleet_status.py, DRIFT001@src/frob/tickets/_evidence.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_process_reap.py, DRIFT002@tests/unit/test_reopen_ticket.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3156, REF001@.claude-scratch/T-3122-close-guard-repro-capture.md, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/conftest.py, SEC110@tests/test_worktree_guard.py, SEC110@tests/test_worktree_lease_env_ambient.py, SELFAUDIT001@design, SUPPRESS001@src/frob/app/_config_external.py, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@src/frob/app/vet_runner.py, SYS003@src/frob/gates/_docblocks_refs.py, SYS003@src/frob/gates/_fix_engine_tier_c.py, SYS003@src/frob/gates/_fuzz.py, SYS003@src/frob/gates/_gate_cache.py, SYS003@src/frob/gates/_models.py, SYS003@src/frob/gates/_wire.py, SYS003@src/frob/vet/_models.py, SYS003@tests/gates/test_rule_id_scan_branches.py, SYS003@tests/gates/test_tdd_order.py, SYS003@tests/test_arch_gate.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_docblocks_gate.py, SYS003@tests/test_docptr_gate.py, SYS003@tests/test_fuzz.py, SYS003@tests/test_gates_suppress.py, SYS003@tests/test_ghio.py, SYS003@tests/test_lang_conformance_gate.py, SYS003@tests/test_narrative_migrate.py, SYS003@tests/test_pii_structural_gate.py, SYS003@tests/test_refs_gate.py, SYS003@tests/test_registry_exhaustiveness.py, SYS003@tests/test_registry_staleness.py, SYS003@tests/test_secrets_gate.py, SYS003@tests/test_todo_fmt_gate.py, SYS003@tests/test_vet.py, SYS003@tests/unit/gates/test_doc011.py, SYS003@tests/unit/gates/test_refs.py, SYS003@tests/unit/gates/test_sys_selfaudit.py, SYS003@tests/unit/security/test_redact.py, SYS003@tests/unit/strata/test_cve_fingerprint_scan.py, SYS003@tests/unit/test_arch_table_schema.py, SYS003@tests/unit/test_docblocks_table_schema.py, SYS003@tests/unit/test_dup_graph_table_schema.py, SYS003@tests/unit/test_flag_coverage_gate.py, SYS003@tests/unit/test_gates_table_schema.py, SYS003@tests/unit/test_native_table_schema.py, SYS003@tests/unit/test_profile_table_schema.py, SYS003@tests/unit/test_refs_schema.py, SYS003@tests/unit/test_test_table_schema.py, SYS003@tests/unit/test_testing_table_schema.py, SYS003@tests/unit/test_toplevel_scalar_schema.py, SYS003@tests/unit/vet/test_taint.py, TEST001@scripts/branch_stranded_work_analysis.py, TEST001@src/frob/tickets/_models.py, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py, missing-argument@tests/unit/test_coordinator_scripts.py, unknown-argument@tests/unit/test_app_runners_process.py, unknown-argument@tests/unit/test_pytest_spawn_env_wiring.py
