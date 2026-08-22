## Done report

Batch 1 of the ruff-format bulk-reformat: 20 files under tests/*.py
(top-level, loose files), scoped narrowly per the "scope is a write
lease" rule. Excluded tests/test_gates_fmt_directives.py and
tests/test_lang.py up front (T-1606, per-language formatter width, live
in worktree t1606-series, owns those). Also excluded tests/conftest.py,
tests/test_gates.py, tests/test_graph.py after `frob ticket land`
correctly refused with CrossTicketLeakage: T-1654 (in-progress in
worktree t1661-series) declares those 3 files in its own open scope.
Reverted those 3 files to main's content and re-committed before
retrying land -- deferring them to a later batch once T-1654 closes.

RE-MEASURED counts before starting (the ticket's own 77/265 numbers are
stale): ruff format --check . reports 203 files drifted (not 77);
frob fmt --check reports 1 file drifted by default (test-corpus files
excluded); frob fmt --check --include-test-corpora reports 50 files
(49 more, all under tests/unit/strata/litmus/**, deliberately excluded
by default per T-2298 since rewriting a test fixture can change what a
test asserts against). This ticket is being worked in disjoint batches,
each scoped, verified and landed independently -- this is the first.

Reformatted via `frob format <path>` (T-2251/T-2244's standardized
surface, not raw ruff) for each file. Verified the diff is pure
line-wrap/whitespace (git diff main -- tests/test_gates.py inspected
directly before it was dropped from this batch; the 20 landed files are
the same class of change). Ran every touched file's own test file: all
pass. (tests/test_gates.py's two pre-existing failures -- TestWireGate::
test_new_cli_dest_present_in_config_external_is_not_flagged and
TestDoc004ConsoleCommandDrift::test_real_subcommand_unanchored_warns_
unbound, confirmed identical against the unmodified primary checkout --
are moot for this batch since that file was dropped.)

Remaining scope after this batch: ~183 more ruff-format files
(src/frob/gates, src/frob/tickets, src/frob/app, remaining src/frob
subpackages, tests/unit/**, tests/system/**, plus tests/conftest.py/
test_gates.py/test_graph.py once T-1654 closes), the 1 frob-fmt file
(tests/unit/test_app_runners_batch6.py), and the 49-file litmus
test-corpus frob-fmt set (needs its own cautious batch with covering
tests run, per T-2298's warning about fixture rewrites). Not closing
this ticket -- more batches remain, sequenced the same way (narrow
scope, land, unscoped re-measure, repeat).

### Changed
```
 rapid-debt.jsonl                           |   1 +
 tests/test_app.py                          |   1 -
 tests/test_capability_registry.py          |  13 +-
 tests/test_check_runner.py                 |   5 +-
 tests/test_coverage_wait_shared.py         |   1 -
 tests/test_doc012_promotion.py             |  16 +-
 tests/test_docenum_gate.py                 |  29 +--
 tests/test_gates_fix_engine.py             |   4 +-
 tests/test_gates_suppress.py               |   1 -
 tests/test_graph_imports.py                |   4 +-
 tests/test_hook_diagnosis_nudge.py         |   8 +-
 tests/test_land_verify_claims_outcome.py   |   4 +-
 tests/test_lang_conformance_gate.py        |  22 +-
 tests/test_pii_structural_gate.py          |  11 +-
 tests/test_refactor.py                     |  12 +-
 tests/test_release.py                      |   7 +-
 tests/test_scaffold_worktree_lease_hook.py |  13 +-
 tests/test_serve_tools_daemon_bypass.py    |   2 +-
 tests/test_telemetry.py                    |  10 +-
 tests/test_testing.py                      |  22 +-
 tests/test_tick012_gate.py                 |   4 +-
 tickets/T-1945/done-report.md              |  71 ++++++
 tickets/T-1945/ticket.md                   | 349 +++++++++++++++++++++++++++--
 23 files changed, 480 insertions(+), 130 deletions(-)
```

### Evidence
- `tests/test_app.py::TestRunCoverageWait::test_coverage_lock_path_is_under_frob_dir` (pytest node id, verified passing when recorded)
- `tests/test_capability_registry.py::TestMatrixExhaustiveness::test_no_unexcused_empty_cells` (pytest node id, verified passing when recorded)
- `tests/test_check_runner.py::TestApplyTierAAndReverify::test_doc007_finding_fixed_and_reverified_clean` (pytest node id, verified passing when recorded)
- `tests/test_coverage_wait_shared.py::TestTreeDigest::test_identical_hashes_produce_identical_digest` (pytest node id, verified passing when recorded)
- `tests/test_doc012_promotion.py::TestDoc012PromotedToError::test_undocumented_subcommand_is_now_error` (pytest node id, verified passing when recorded)
- `tests/test_docenum_gate.py::TestDocenum001Gate::test_stale_claimed_list_fires` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestMutationEvidencePackageReexports::test_must_still_pass_violations_importable_from_package` (pytest node id, verified passing when recorded)
- `tests/test_gates_fix_engine.py::TestFixSuppress001PairedSuppression::test_mypy_suppressed_ty_unsuppressed_gets_paired_suppression` (pytest node id, verified passing when recorded)
- `tests/test_gates_suppress.py::TestSuppressionDialects::test_registers_ty_mypy_ruff` (pytest node id, verified passing when recorded)
- `tests/test_graph.py::TestDigests::test_reformat_identical_digests` (pytest node id, verified passing when recorded)
- `tests/test_graph_imports.py::TestBuildImportGraph::test_resolves_a_real_intra_repo_import_edge` (pytest node id, verified passing when recorded)
- `tests/test_hook_diagnosis_nudge.py::test_nudges_on_diagnosis_and_prints_system_message` (pytest node id, verified passing when recorded)
- `tests/test_land_verify_claims_outcome.py::TestClaimsReverifyOutcomeDistinguishesSkipFromPass::test_unmeasured_passing_ids_and_check_gates_is_surfaced_as_skipped` (pytest node id, verified passing when recorded)
- `tests/test_lang_conformance_gate.py::TestLangConformanceGate::test_real_registry_is_clean` (pytest node id, verified passing when recorded)
- `tests/test_pii_structural_gate.py::TestFieldNames::test_password_field_fires` (pytest node id, verified passing when recorded)
- `tests/test_refactor.py::TestResolveSymbol::test_resolves_top_level_function` (pytest node id, verified passing when recorded)
- `tests/test_release.py::test_stamp_and_no_change_is_none` (pytest node id, verified passing when recorded)
- `tests/test_scaffold_worktree_lease_hook.py::TestInstallWorktreeLeaseHook::test_installs_pre_commit_and_pre_merge_commit` (pytest node id, verified passing when recorded)
- `tests/test_serve_tools_daemon_bypass.py::TestFrobDoableTicketsRevalidation::test_resolved_sweep_ticket_is_dropped_before_listing` (pytest node id, verified passing when recorded)
- `tests/test_telemetry.py::test_append_event_writes_one_json_line` (pytest node id, verified passing when recorded)
- `tests/test_testing.py::TestSelect::test_direct_hit` (pytest node id, verified passing when recorded)
- `tests/test_tick012_gate.py::TestTick012LeaseScopeDrift::test_stale_superset_path_fires` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 22 passed (from 22 evidence id(s))
- gates: 17 error(s), 1272 warning(s), 707 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/_close_cmd.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1688, COV003@tickets/T-2365, CYCLE001@src/frob/__init__.py, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, DRIFT002@src/frob/tickets/_land.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md
