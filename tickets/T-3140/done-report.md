## Done report

RE-RUN COUNT: all 10 items still failed at the START of this ticket (no
reduction from the ~15 lands that happened since T-3140 was filed --
measured, not assumed: re-ran all 10 node ids before touching anything).
After this ticket: 6 of 10 fixed, 4 of 10 remain (need production fixes
outside this ticket's declared scope; filed as follow-ups below).

Per-item verdicts:

1. test_clean.py::test_makefile_coverage_recipe_never_escalates_clean_tier
   -- TEST STALE. The safety property (coverage must never escalate to a
   `clean --all`/`--deep` tier) did NOT move into `frob coverage --full`'s
   internals as a bounded-tier clean call, as the ticket body speculated --
   it holds VACUOUSLY: measured that neither the Makefile's `coverage:`
   recipe nor `frob.app.coverage_runner.run` nor
   `frob.testing._coverage_refresh.native_coverage_refresh` call
   `frob.clean` at all any more. Rewrote the test to check the current
   recipe text (loosened regex) plus both modules' source for any future
   `clean` call, still bounded to the SAFE tier if one is ever added.

2/3. test_makefile_lock_sync.py (both tests) -- TEST STALE. The `upload:`
   recipe no longer contains `bump_version.py`/`frob release sync`/`git
   add` text to parse (rewritten to a single `frob release publish`
   call). Measured `src/frob/release/_publish.py`'s `publish()`: bump ->
   stamp -> `_sync_derived_artifacts` (re-locks via `uv lock`) -> `git add
   <_COMMIT_FILES>` (includes both `pyproject.toml` and `uv.lock`) ->
   commit, in that order -- the T-0789 property held throughout, fully
   inlined into Python. Rewrote both tests to assert that shape directly
   against `_publish.py` instead of parsing now-absent Makefile text.

4. test_gates.py::TestRuleFixability::test_checked_in_literal_matches_a_fresh_scan
   -- confirmed still failing (checked-in `_KNOWN_RULE_FIXABILITY`
   missing SYS100). Fix is in src/frob/gates/ (production, out of this
   ticket's scope) -- filed T-3148.

5. test_exports.py::test_all_nine_packages_report_zero_missing_symbols
   -- confirmed still failing (real missing __init__.py exports across
   several packages). Fix is in several packages' __init__.py files
   (production, out of scope) -- filed T-3151.

6. test_gates.py::TestWireGate::test_new_cli_dest_present_in_config_external_is_not_flagged
   -- confirmed still failing; MEASURED as a genuine WIRE001 false
   positive (the fixture's CLI dest IS present in _config_external.py
   exactly as the test expects, wire_gate still flags it) -- not test
   staleness. Fix is in src/frob/gates/_wire.py (production, out of
   scope) -- filed T-3149.

7. test_coordinator_scripts.py::test_live_worktree_with_lease_file_removed_is_not_leaked
   -- confirmed still failing; MEASURED as a genuine regression in the
   coordinator's lease fallback scan (reproduces byte-for-byte with real
   git state: a real worktree, a real commit touching the ticket's
   declared scope, an empty leases dir -- the fallback scan reports
   leaked=True/worktree=None instead of resolving the live worktree).
   Fix is in scripts/fleet_status.py (production script, out of scope,
   and T-3128 already holds a live lease on that exact file) -- filed
   T-3150.

8. test_app_daemon_proxy.py::TestDifferentialParity::test_check_delta_gates_only_json_daemon_matches_in_process
   -- TEST STALE (normalizer gap, not a product leak). MEASURED
   (frob.check._python._label_replay, T-2585): `[REPLAY age=Ns, unchanged
   tree]` is a deliberate, intentional daemon-only disclosure label so a
   cache-replayed gate-summary is never visually indistinguishable from a
   freshly computed one -- the in-process path has no daemon cache to
   replay from and structurally can never emit it. Taught
   `_normalize_gate_timing` to also strip this label, alongside the
   pre-existing `[gate=Ns]` timing-blob strip it already did.

9. test_app_runners_t1822_already_landed.py::test_no_markers_prints_nothing_and_returns_empty
   -- TEST BUG (assertion too broad, not a product issue). `caplog.
   records` is unscoped and captures every record reaching the root
   handler, not just the function's own `frob.app.ticket_runner` logger
   the test's own `caplog.at_level(..., logger="frob.app.ticket_runner")`
   already scoped intent to. The leaking record is an UNRELATED
   `over_broad_literal_globs` WARNING (frob.tickets._models) fired
   incidentally while loading the queue in this fixture (no
   pyproject.toml present) -- not output from the function under test.
   Narrowed the assertion to `frob.app.ticket_runner`-only records,
   matching the sibling test in the same class
   (`test_flagged_ticket_prints_one_summary_line_and_is_returned`), which
   already filters by message content for the identical reason.

10. test_gates.py::TestDoc004ConsoleCommandDrift::test_real_subcommand_unanchored_warns_unbound
    -- TEST STALE. MEASURED (src/frob/gates/_docblocks_shared.py::
    _doc004_violation's own docstring): T-2374 (the v1.0.0 severity
    freeze) deliberately promoted BOTH DOC004 tiers ("stale" and
    "unbound") to ERROR -- "unbound" shipped at WARN and was burned to
    zero alongside DOC006 before promotion. This test's WARN expectation
    predates that freeze. Independently corroborated: T-2906's own Done
    report already flagged this exact test as "PRE-EXISTING, unrelated
    failure ... a stale test expectation, not caused by this change, not
    in this ticket's scope" -- this ticket is that follow-up. Updated the
    assertion to ERROR; kept the test's own name unchanged since it is
    cited as evidence on archived tickets (T-0443, T-2777, T-2843).

Changed:
- tests/test_clean.py
- tests/test_makefile_lock_sync.py
- tests/test_app_daemon_proxy.py
- tests/unit/test_app_runners_t1822_already_landed.py
- tests/test_gates.py

Evidence:
- tests/test_clean.py::test_makefile_coverage_recipe_never_escalates_clean_tier
- tests/test_makefile_lock_sync.py::test_upload_relocks_after_version_bump
- tests/test_makefile_lock_sync.py::test_upload_commits_uv_lock_with_pyproject
- tests/test_app_daemon_proxy.py::TestDifferentialParity::test_check_delta_gates_only_json_daemon_matches_in_process
- tests/unit/test_app_runners_t1822_already_landed.py::TestRenderAlreadyLandedMarkers::test_no_markers_prints_nothing_and_returns_empty
- tests/test_gates.py::TestDoc004ConsoleCommandDrift::test_real_subcommand_unanchored_warns_unbound

Filed (renumber at land, verified real ids before citing here):
- T-3148 -- item 4, _KNOWN_RULE_FIXABILITY missing SYS100
- T-3151 -- item 5, frob-exports gap across several packages
- T-3149 -- item 6, WIRE001 false positive in wire_gate
- T-3150 -- item 7, coordinator lease fallback scan regression

Gates: frob check --ticket T-3140 to be run before close; rapid profile
so LAND-PROOF verified is expected to read SKIPPED-UNMEASURED, matching
T-3141's own land.

### Changed
```
 tests/test_app_daemon_proxy.py                     | 22 ++++++-
 tests/test_clean.py                                | 41 ++++++++++---
 tests/test_gates.py                                | 13 +++-
 tests/test_makefile_lock_sync.py                   | 69 ++++++++++------------
 .../unit/test_app_runners_t1822_already_landed.py  | 16 ++++-
 tickets/T-3140/ticket.md                           |  9 ++-
 tickets/T-3148/ticket.md                 | 59 ++++++++++++++++++
 tickets/T-3149/ticket.md                 | 45 ++++++++++++++
 tickets/T-3150/ticket.md                 | 62 +++++++++++++++++++
 tickets/T-3151/ticket.md                 | 58 ++++++++++++++++++
 10 files changed, 341 insertions(+), 53 deletions(-)
```

### Evidence
- `tests/test_clean.py::test_makefile_coverage_recipe_never_escalates_clean_tier` (pytest node id, verified passing when recorded)
- `tests/test_makefile_lock_sync.py::test_upload_relocks_after_version_bump` (pytest node id, verified passing when recorded)
- `tests/test_makefile_lock_sync.py::test_upload_commits_uv_lock_with_pyproject` (pytest node id, verified passing when recorded)
- `tests/test_app_daemon_proxy.py::TestDifferentialParity::test_check_delta_gates_only_json_daemon_matches_in_process` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_t1822_already_landed.py::TestRenderAlreadyLandedMarkers::test_no_markers_prints_nothing_and_returns_empty` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDoc004ConsoleCommandDrift::test_real_subcommand_unanchored_warns_unbound` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 119 error(s), 1851 warning(s), 873 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@.claude/hooks/frob-suggest.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@.claude/hooks/frob-suggest.py, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC005@docs/modules/cli.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-3139/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_process_reap.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_process_reap.py, DRIFT002@tests/unit/test_reopen_ticket.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3140, REF001@.claude-scratch/T-3122-close-guard-repro-capture.md, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/conftest.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, SUPPRESS001@src/frob/app/_config_external.py, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@src/frob/app/vet_runner.py, SYS003@src/frob/gates/_docblocks_refs.py, SYS003@src/frob/gates/_fix_engine_tier_c.py, SYS003@src/frob/gates/_fuzz.py, SYS003@src/frob/gates/_gate_cache.py, SYS003@src/frob/gates/_models.py, SYS003@src/frob/gates/_wire.py, SYS003@src/frob/vet/_models.py, SYS003@tests/gates/test_rule_id_scan_branches.py, SYS003@tests/gates/test_tdd_order.py, SYS003@tests/test_arch_gate.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_docblocks_gate.py, SYS003@tests/test_docptr_gate.py, SYS003@tests/test_fuzz.py, SYS003@tests/test_gates_suppress.py, SYS003@tests/test_ghio.py, SYS003@tests/test_lang_conformance_gate.py, SYS003@tests/test_narrative_migrate.py, SYS003@tests/test_pii_structural_gate.py, SYS003@tests/test_refs_gate.py, SYS003@tests/test_registry_exhaustiveness.py, SYS003@tests/test_registry_staleness.py, SYS003@tests/test_secrets_gate.py, SYS003@tests/test_todo_fmt_gate.py, SYS003@tests/test_vet.py, SYS003@tests/unit/gates/test_doc011.py, SYS003@tests/unit/gates/test_refs.py, SYS003@tests/unit/gates/test_sys_selfaudit.py, SYS003@tests/unit/security/test_redact.py, SYS003@tests/unit/strata/test_cve_fingerprint_scan.py, SYS003@tests/unit/test_arch_table_schema.py, SYS003@tests/unit/test_docblocks_table_schema.py, SYS003@tests/unit/test_dup_graph_table_schema.py, SYS003@tests/unit/test_flag_coverage_gate.py, SYS003@tests/unit/test_gates_table_schema.py, SYS003@tests/unit/test_native_table_schema.py, SYS003@tests/unit/test_profile_table_schema.py, SYS003@tests/unit/test_refs_schema.py, SYS003@tests/unit/test_test_table_schema.py, SYS003@tests/unit/test_testing_table_schema.py, SYS003@tests/unit/test_toplevel_scalar_schema.py, SYS003@tests/unit/vet/test_taint.py, TEST001@scripts/branch_stranded_work_analysis.py, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py, unknown-argument@tests/unit/test_app_runners_process.py, unknown-argument@tests/unit/test_pytest_spawn_env_wiring.py
