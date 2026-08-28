## Done report

Fix + audit for T-3137.

WHAT: `frob ticket fail` was the one exception to T-2603's fully-classified
LEDGER_VERB_STRATEGY table -- it is GENERIC_COMMIT_UNMIRRORED, which commits
the failure-log entry (and any IN_PROGRESS->QUEUED requeue) only to the
worktree's own branch. That is correct as long as a future `frob ticket land`
for the SAME ticket carries it; it silently fails to reach the fleet when the
series' own landing ticket has already landed and no further land ever
touches that branch (exactly the FOUND scenario).

Mirroring `fail` outright (matching `scope`/`block`/`requeue`) was considered
and rejected for this pass: `fail` writes TWO ledger effects (a failure-log
append plus an optional state transition/requeue), and T-2563's generic
mirror was built and tested only for the single-field-write shape `scope`/
`block`/`tier`/etc use. Folding `fail` in needs its own verification that a
transition-plus-append mirrors correctly under a concurrent worktree merge,
which is real, separate work -- attempting it here risked exactly the kind
of half-verified change T-2603 warned against ("a bad unification is worse
than the status quo"). Filed as residue (see below) instead of forced here.

Implemented instead, matching promote's own T-2197 precedent
(`_warn_if_promote_not_visible_on_primary`):
`_warn_if_fail_not_visible_on_primary` in _close_cmd.py, called after `_fail`'s
own commit. A no-op when `root` IS the resolved primary checkout (root ==
primary, the common case); otherwise a loud, greppable `_log.error` naming the
primary checkout and the exact follow-up (`frob ticket fail --path <primary>
...`, or landing the branch). This satisfies T-3137's acceptance directly:
"either mirror to main ... or report plainly that it has not, naming the
follow-up."

PER-VERB MIRROR AUDIT (T-3137's second bullet): T-2603 (already landed, see
LEDGER_VERB_STRATEGY in src/frob/app/ticket_runner/_ledger_mirror.py) is
ALREADY this audit, enumerated exhaustively and enforced by
TestVerbStrategy::test_all_classified. Read fresh against current main:

  verb          | mirrors | announces when it does not
  --------------|---------|----------------------------
  promote       | yes (OWN_TRANSACTION_LEDGER_MIRROR, T-2587) | yes (T-2197's own warning)
  scope         | yes (GENERIC_COMMIT_MIRRORED) | n/a (always reaches main)
  block/unblock | yes | n/a
  attach        | yes | n/a
  requeue       | yes (T-2840 reclassified FROM unmirrored, exactly this trap) | n/a
  tier/priority/kind/label/... | yes (GENERIC_COMMIT_MIRRORED) | n/a
  new/plan/start/work/sweep/reconcile/close/reverify/drop/evidence/
  done-report/archive | no (GENERIC_COMMIT_UNMIRRORED -- land carries it) | NO warning (residue below)
  fail          | no (GENERIC_COMMIT_UNMIRRORED) | YES (this ticket's fix)
  milestone     | no (T-2574, flagged in its own comment as possibly wrong) | no

So `fail` was the ONLY GENERIC_COMMIT_UNMIRRORED verb capable of running
standalone against an already-superseded ticket (a genuine dead end after
the series landed) with zero future land ever touching that branch again.
`new`/`drop`/`evidence`/`done-report`/etc all either always precede a land
for the SAME ticket by construction, or (drop) terminate the ticket so no
"next agent repeats the dead end" risk exists the way `fail`'s does. Their
own reachability gap is real but lower-severity and out of this ticket's
scope; recorded as residue.

FILED: none of my own -- the remaining unmirrored-verb reachability gap for
new/drop/evidence/done-report is real but is T-2563/T-2603's own documented,
accepted design (land-carries-it), not a NEW gap this ticket found. No new
ticket filed for it.

GATES: `frob check --ticket T-3137` -- zero errors/warnings attributable to
the touched files (src/frob/app/ticket_runner/_close_cmd.py,
tests/unit/test_ticket_runner_ledger_mirror.py); every FAIL row in the full
summary table is pre-existing repo-wide baseline noise (ruff-format CRLF,
ty, frob-cycle's known 182-node SCC, claude-config-drift), verified by
diffing HEAD's own copy of each touched file through the same tool and by
grepping the --json output for the touched files among error-severity
diagnostics (zero hits). `TestVerbStrategy::test_all_classified` fails on
current main independent of this change (T-3162's own "reopen" gap, not
mine) -- confirmed against a fresh copy of the parent commit's test file.

### Changed
```
 tickets/T-3137/ticket.md | 27 ++++++++++++++++++++++++++-
 1 file changed, 26 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_ticket_runner_ledger_mirror.py::TestFailNotVisibleOnPrimaryWarning::test_fail_from_worktree_warns_when_not_visible_on_primary` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_ledger_mirror.py::TestFailNotVisibleOnPrimaryWarning::test_fail_from_primary_is_quiet` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 125 error(s), 847 warning(s), 873 waived
- error-findings: ARCH103@src/frob/app/_version_guard.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@.claude/hooks/frob-suggest.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@.claude/hooks/frob-suggest.py, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC005@docs/modules/cli.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-3155/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_process_reap.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT001@scripts/fleet_status.py, DRIFT001@src/frob/tickets/_evidence.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_process_reap.py, DRIFT002@tests/unit/test_reopen_ticket.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3137, REF001@.claude-scratch/T-3122-close-guard-repro-capture.md, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/conftest.py, SEC110@tests/test_worktree_guard.py, SEC110@tests/test_worktree_lease_env_ambient.py, SELFAUDIT001@design, SUPPRESS001@src/frob/app/_config_external.py, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@src/frob/__init__.py, SYS003@src/frob/app/vet_runner.py, SYS003@src/frob/gates/_docblocks_refs.py, SYS003@src/frob/gates/_fix_engine_tier_c.py, SYS003@src/frob/gates/_fuzz.py, SYS003@src/frob/gates/_gate_cache.py, SYS003@src/frob/gates/_models.py, SYS003@src/frob/gates/_wire.py, SYS003@src/frob/vet/_models.py, SYS003@tests/gates/test_rule_id_scan_branches.py, SYS003@tests/gates/test_tdd_order.py, SYS003@tests/test_arch_gate.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_docblocks_gate.py, SYS003@tests/test_docptr_gate.py, SYS003@tests/test_fuzz.py, SYS003@tests/test_gates_suppress.py, SYS003@tests/test_ghio.py, SYS003@tests/test_lang_conformance_gate.py, SYS003@tests/test_narrative_migrate.py, SYS003@tests/test_pii_structural_gate.py, SYS003@tests/test_refs_gate.py, SYS003@tests/test_registry_exhaustiveness.py, SYS003@tests/test_registry_staleness.py, SYS003@tests/test_secrets_gate.py, SYS003@tests/test_todo_fmt_gate.py, SYS003@tests/test_vet.py, SYS003@tests/unit/gates/test_doc011.py, SYS003@tests/unit/gates/test_refs.py, SYS003@tests/unit/gates/test_sys_selfaudit.py, SYS003@tests/unit/security/test_redact.py, SYS003@tests/unit/strata/test_cve_fingerprint_scan.py, SYS003@tests/unit/test_arch_table_schema.py, SYS003@tests/unit/test_docblocks_table_schema.py, SYS003@tests/unit/test_dup_graph_table_schema.py, SYS003@tests/unit/test_flag_coverage_gate.py, SYS003@tests/unit/test_gates_table_schema.py, SYS003@tests/unit/test_native_table_schema.py, SYS003@tests/unit/test_profile_table_schema.py, SYS003@tests/unit/test_refs_schema.py, SYS003@tests/unit/test_test_table_schema.py, SYS003@tests/unit/test_testing_table_schema.py, SYS003@tests/unit/test_toplevel_scalar_schema.py, SYS003@tests/unit/vet/test_taint.py, TEST001@scripts/branch_stranded_work_analysis.py, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py, missing-argument@tests/unit/test_coordinator_scripts.py, unknown-argument@tests/unit/test_app_runners_process.py, unknown-argument@tests/unit/test_pytest_spawn_env_wiring.py
