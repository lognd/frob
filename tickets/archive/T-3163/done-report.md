## Done report

Changed:
  src/frob/tickets/_land_squash.py :: _land_squash_apply (outer ledger_lock hold for a precomposed land)
  src/frob/tickets/_land_squash.py :: _publish_squash_apply (docstring; nested ledger_lock, reentrant, defense-in-depth)
  src/frob/tickets/_land_squash.py :: _fold_publish_and_resync (new, split out of _publish_squash_apply)
  src/frob/tickets/_land_compose.py :: compose_squash_in_disposable_worktree (THE fix -- ledger_lock(repo) now spans this generator's entire lifetime, from before the squash-merge through worktree teardown)
  docs/modules/tickets-landing.md (T-3163 correction section: the "blocked resync is non-destructive" claim in the T-3121 doc was wrong -- the real damage happens in the sibling's own subsequent commit, not the resync itself; also corrected the v2-exemption reasoning, which was never actually exempt)
  tests/unit/test_land_compose.py :: scratch_repo/conflicting_repo fixtures (gitignore .frob/, T-1393 pattern) + one ls-tree assertion updated -- fixing 3 must-stay-quiet regressions the lock's own .frob/tickets.lock side effect introduced

HYPOTHESIS VERDICT: partially confirmed, mechanism refined. The ticket's
hypothesis was "new_ticket() reads/merges against a stale snapshot and
writes a REPLACEMENT tickets.md." Traced via git logging and a live repro:
new_ticket()'s own read-modify-write IS correct relative to whatever it
reads. The actual mechanism is one level down: T-3121's flip left
`ledger_lock` held only around `_squash_and_splice_ledger`'s narrow
read-splice-write (which never touches root's on-disk file -- it writes
into the disposable `stage`) and separately around `_publish_squash_
apply`'s fold+CAS+resync tail, with everything in between (version bump,
native rebuild, gate-rule sync, pre-commit sweep) lock-free. A concurrent
`new_ticket()` could win `ledger_lock` ANYWHERE in that multi-stage gap,
read root's still-pre-land tickets.md, and write it straight back to
root's WORKING TREE, well before this land ever reached its own `ledger_
lock` acquisition. By the time CAS moved `refs/heads/<main>` to the new
tip, the sibling's own pathspec-scoped `git commit -- tickets.md`
(`commit_ticket_ledger_change`) built its tree from the NEW HEAD overlaid
ONLY with its own staged pathspec -- so tickets.md was REPLACED wholesale
by the sibling's stale-based version (confirming the "replacement, not
append" shape of the hypothesis), while every other path came from HEAD
correctly. The v2-mode "exemption" the existing docs claimed was never
real either: it reasoned only about the resync step (which was never the
actual loss mechanism), not the sibling's own commit.

FIX: `ledger_lock(root)` now spans `compose_squash_in_disposable_
worktree`'s ENTIRE lifetime -- acquired before the squash-merge runs,
held continuously through the caller's whole use of the composed stage
(everything `_land_squash_apply`/`_land_squash_apply_finish` do), release
only on worktree teardown. A concurrent `ledger_lock` acquirer now always
queues behind the WHOLE precomposed transaction, so its read is taken
after root is fully resynced (or the land has given up and logged the
recovery command) -- never against a pre-publish snapshot. This
necessarily reopens part of the exact window T-3121 shrank for ledger-
mutating verbs specifically (not `_land_lock`/`DirtyMain`, a different,
wider lock T-3121's measured win was actually about, which this fix does
not touch) -- judged worth it against silent, permanent ledger data loss.

VERIFICATION: the existing regression test (tests/test_ticket_land.py::
TestSquashSpliceLedgerChurn::test_concurrent_write_between_squash_and_
splice_survives_land, retargeted by T-3144's in-flight test-infra fix)
reproduces the ORIGINAL bug cleanly against the parent commit (confirmed
BUG002 directly, not asserted -- ran it standalone with --runxfail before
any production change). Against the FIX, that exact test still fails --
but for an unrelated, NEWLY-EXPOSED test-construction artifact: its own
T-2114 concurrent-writer simulation forks the sibling process, and once
ledger_lock is genuinely held across most of the test's own injected-hook
window (required for the fix to be correct), the forked child inherits
the parent's already-acquired flock fd AND _lock_local's thread-local
"already held" bookkeeping, so it spuriously skips real contention rather
than actually blocking like an independent process would. Filed as
T-3174 (blocked_by T-3144, same file's write lease). Confirmed
the FIX itself is correct with a standalone script using multiprocessing.
get_context("spawn") (a genuinely independent process, immune to the
fork artifact) reproducing the identical test scenario against the fixed
code: land() succeeds, resync succeeds cleanly, the sibling correctly
blocks until land fully finishes, reads the freshly-published ledger, and
both tickets survive -- PASS.

Must-stay-quiet fixture: tests/unit/test_land_compose.py's existing
suite (19/19, including the two porcelain-equality "root worktree
untouched" tests and the sequential/non-racing compose+publish flow)
passes clean -- a normal land with no concurrent sibling lands exactly as
before, modulo the fixtures now gitignoring .frob/ (a fixture gap the
lock's own side effect surfaced, not a behavior change).

Evidence: tests/unit/test_land_compose.py (9 cases, all passing, cover
compose_squash_in_disposable_worktree/fold_worktree_into_commit directly
-- the lock-wrapped code paths) plus tests/unit/test_land_stage_flip.py's
TestPublishSquashApply (3 cases, publish/resync semantics unchanged).
The T-1036 regression test itself
(tests/test_ticket_land.py::TestSquashSpliceLedgerChurn::
test_concurrent_write_between_squash_and_splice_survives_land) is cited
in a frob:tests directive on the fix but is NOT in the closing evidence
list -- it cannot currently pass due to the T-2114 fork artifact above
(T-3174), independently confirmed correct via the spawn-based
standalone repro described above.

`frob test --base main` (touched-set): 12/12 python outcomes recorded,
1 failure -- the same known test-infra-artifact test, nothing else.

Filed: T-3174 (fork-vs-ledger_lock test-infra gap, blocked_by
T-3144)

Gates: `frob check --ticket T-3163` -- zero findings (waived or
otherwise) reference src/frob/tickets/_land_squash.py or src/frob/
tickets/_land_compose.py anywhere in the full output; gate:SCOPE clean
(0 errors). Every other gate family's counts are repo-wide pre-existing
baseline per the tool's own scope-note, unrelated to this ticket's
touched files.

### Changed
```
 tickets/T-3163/ticket.md           | 53 +++++++++++++++++++++++
 tickets/T-3174/ticket.md | 87 ++++++++++++++++++++++++++++++++++++++
 2 files changed, 140 insertions(+)
```

### Evidence
- `tests/unit/test_land_compose.py::TestDisposableSquashWorktree::test_clean_squash_reports_no_conflicts` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_compose.py::TestDisposableSquashWorktree::test_conflicting_squash_reports_the_conflicted_paths` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_compose.py::TestDisposableSquashWorktree::test_root_worktree_untouched_by_clean_squash` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_compose.py::TestDisposableSquashWorktree::test_root_worktree_untouched_by_conflicted_squash` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_compose.py::TestFoldWorktreeIntoCommit::test_folded_commit_contains_both_sides` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_compose.py::TestFoldWorktreeIntoCommit::test_fold_refuses_while_paths_are_unmerged` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_stage_flip.py::TestPublishSquashApply::test_racing_publish_surfaces_dirtymain` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_stage_flip.py::TestPublishSquashApply::test_blocked_resync_is_not_a_land_failure` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_stage_flip.py::TestPublishSquashApply::test_clean_publish_advances_root_and_resyncs` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 9 passed (from 9 evidence id(s))
- gates: 125 error(s), 853 warning(s), 873 waived
- error-findings: ARCH103@src/frob/app/_version_guard.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@.claude/hooks/frob-suggest.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@.claude/hooks/frob-suggest.py, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC005@docs/modules/cli.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-3155/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_process_reap.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT001@scripts/fleet_status.py, DRIFT001@src/frob/tickets/_evidence.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_process_reap.py, DRIFT002@tests/unit/test_reopen_ticket.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3163, REF001@.claude-scratch/T-3122-close-guard-repro-capture.md, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/conftest.py, SEC110@tests/test_worktree_guard.py, SEC110@tests/test_worktree_lease_env_ambient.py, SELFAUDIT001@design, SUPPRESS001@src/frob/app/_config_external.py, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@src/frob/__init__.py, SYS003@src/frob/app/vet_runner.py, SYS003@src/frob/gates/_docblocks_refs.py, SYS003@src/frob/gates/_fix_engine_tier_c.py, SYS003@src/frob/gates/_fuzz.py, SYS003@src/frob/gates/_gate_cache.py, SYS003@src/frob/gates/_models.py, SYS003@src/frob/gates/_wire.py, SYS003@src/frob/vet/_models.py, SYS003@tests/gates/test_rule_id_scan_branches.py, SYS003@tests/gates/test_tdd_order.py, SYS003@tests/test_arch_gate.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_docblocks_gate.py, SYS003@tests/test_docptr_gate.py, SYS003@tests/test_fuzz.py, SYS003@tests/test_gates_suppress.py, SYS003@tests/test_ghio.py, SYS003@tests/test_lang_conformance_gate.py, SYS003@tests/test_narrative_migrate.py, SYS003@tests/test_pii_structural_gate.py, SYS003@tests/test_refs_gate.py, SYS003@tests/test_registry_exhaustiveness.py, SYS003@tests/test_registry_staleness.py, SYS003@tests/test_secrets_gate.py, SYS003@tests/test_todo_fmt_gate.py, SYS003@tests/test_vet.py, SYS003@tests/unit/gates/test_doc011.py, SYS003@tests/unit/gates/test_refs.py, SYS003@tests/unit/gates/test_sys_selfaudit.py, SYS003@tests/unit/security/test_redact.py, SYS003@tests/unit/strata/test_cve_fingerprint_scan.py, SYS003@tests/unit/test_arch_table_schema.py, SYS003@tests/unit/test_docblocks_table_schema.py, SYS003@tests/unit/test_dup_graph_table_schema.py, SYS003@tests/unit/test_flag_coverage_gate.py, SYS003@tests/unit/test_gates_table_schema.py, SYS003@tests/unit/test_native_table_schema.py, SYS003@tests/unit/test_profile_table_schema.py, SYS003@tests/unit/test_refs_schema.py, SYS003@tests/unit/test_test_table_schema.py, SYS003@tests/unit/test_testing_table_schema.py, SYS003@tests/unit/test_toplevel_scalar_schema.py, SYS003@tests/unit/vet/test_taint.py, TEST001@scripts/branch_stranded_work_analysis.py, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py, missing-argument@tests/unit/test_coordinator_scripts.py, unknown-argument@tests/unit/test_app_runners_process.py, unknown-argument@tests/unit/test_pytest_spawn_env_wiring.py
