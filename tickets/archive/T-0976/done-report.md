## Done report

ARCH001 burn-down (T-0976): 40 real hierarchical extractions + 1 honest
`frob:waive ARCH001` (arch/_python.py's `_py_collect_body_events`,
matching the kt/rust/ts body-event-walker precedent). `[gates.severity]
ARCH001 = "error"` promoted in frob.toml; 0 unwaived ARCH001 findings
repo-wide.

SEND-BACK 1 (TEST016, post-close): 5 surviving mutants in extracted
helpers pinned with real behavioral tests
(`tests/unit/test_app_runners_t0976_mutation_evidence.py`, 8 tests) --
`app/perf_runner.py::_collect_stacks_via_sampler`'s `argv and argv[0] ==
"--"` guard, `app/ticket_runner.py::_render_doable_dispatchable`'s
`parent_id is not None and parent_id in queue.tickets` guard, and
`app/ticket_runner.py::_close_guards_for_ticket`'s `mutation_evidence is
False and cfg.ticket_close_skip_mutation_evidence` guard. Every kill
hand-verified: apply mutation, test fails, `diff` back to byte-identical,
re-run green. No --skip-mutation-evidence.

SEND-BACK 2 (real 6-file merge conflict, main advanced while working):
`git merge main` resolved keeping BOTH sides semantically in every file:

- `frob.toml [gates.severity]`: keep-both union -- T-0976's own ARCH001
  promotion plus main's T-0977 ARCH101, T-0972 PERF001-004 promotions
  (all four now present, none dropped).
- `gates/_fmt_directives.py`: T-0984's off-by-one fix at the rfind budget
  bound (`rfind(" ", 0, budget)`, not `budget + 1`) lives in
  `_canonical_lines`, a shared helper untouched by T-0976's own
  extraction of `canonicalize_text`/`format_paths` into
  `_fmt_marker_entries_with_indents`/`_rewrite_lines_via_runs`/
  `_format_one_path` -- it auto-merged clean and
  `TestBoundaryOffByOneT0984` (4 cases) verified passing post-merge.
  Main's T-0972 `frob:ticket` tag and PERF003 two-pointer-scan waiver
  (on the run-rewrite while loop, moved main was still on the pre-split
  monolith) were folded into `_rewrite_lines_via_runs`'s own while loop;
  T-0976's own AFFECT001 waiver on `canonicalize_text` kept alongside.
- `arch/_lock_ordering.py`: main's T-0977 PERF004 waiver (on the
  `sorted(info.unresolved)[0]` re-sort) was on the pre-split monolithic
  loop; folded into `_lock_identity_unresolved_finding`, the T-0976
  extraction that now owns that exact line.
- `arch/_patterns.py`: main's T-0972 PERF001 fix (hoist `set(param_names)`
  once outside the per-statement loop instead of `in`-testing the list
  every iteration) was on the pre-split monolithic body; folded into
  `_stmts_are_1to1_self_assignments`, the T-0976 extraction that now owns
  that loop.
- `gates/_protocol_summary.py`: two conflicts, both main-vs-T-0976-split
  shape mismatches (main's edits still targeted the pre-extraction
  monolith) -- (1) main's T-0972 `frob:ticket` tag kept alongside
  T-0976's AFFECT001 waiver on `protocol_summary_gate` itself; (2) main's
  T-0977 PERF004 waiver (on `entrypoints = sorted(set(symrefs))`) folded
  into `_package_protocol_violations`, the T-0976 extraction that now
  owns that line -- `packages_scanned`'s counter (main still had it as a
  loop-local increment) stayed as T-0976's own `len(tagged_by_package)`
  top-level computation, unaffected by either side's edit.
- `app/perf_runner.py`: main's T-0977 `frob:waive ARCH103` reasoning was
  written against the pre-T-0976 monolithic `_collect_stacks` (the
  dispatch-mixing shape ARCH103 flags); T-0976's own split moved that
  exact dispatch point into `_collect_stacks` (now a 2-line delegator)
  with the sampler/file logic in two new private helpers, so the ARCH103
  shape this waiver targeted no longer exists on either function -- kept
  T-0976's split as-is (no re-add of the waiver; nothing to waive
  post-split) and added `frob:ticket T-0765` back alongside `frob:ticket
  T-0976` on `_collect_stacks_via_sampler`, the closest surviving home
  for that ticket tag.
- `app/ticket_runner.py`: auto-merged clean, no conflict.

Land-owned files (T-0731): `CHANGELOG.md`/`uv.lock`/`pyproject.toml`'s
version line auto-merged in main's own advances during `git merge main`;
reset to this worktree's pre-merge (HEAD) state before committing --
`frob ticket land` recomputes all three fresh at land time regardless of
what a worktree branch carries, so carrying main's bump forward here was
never required and the T-0731 pre-commit guard correctly refused it.

Post-merge verification: `git diff main --diff-filter=D` clean (no
unintended deletions); full touched-module suites green --
`tests/test_gates_fmt_directives.py` (incl. `TestBoundaryOffByOneT0984`),
`tests/unit/test_arch.py` (`TestLockOrderingHazards`,
`TestPatternRecommender`, `TestProtocolSummaryEngine`),
`tests/system/test_cli_perf.py`, `tests/unit/test_app_runners_batch6.py`,
`tests/unit/test_app_runners_t0976_mutation_evidence.py`,
`tests/test_gates.py` (Proto family) -- all passed. `ruff check` clean on
every merge-touched file.

### Changed
```
 .frob-release.json                                 |   4 +-
 CHANGELOG.md                                       |   8 -
 frob.lock                                          | 257 +++++++-
 frob.toml                                          |   8 +
 pyproject.toml                                     |   2 +-
 src/frob/app/perf_runner.py                        | 117 ++--
 src/frob/app/ticket_runner.py                      | 223 ++++---
 src/frob/arch/_layering.py                         |  75 ++-
 src/frob/arch/_lock_ordering.py                    | 184 +++---
 src/frob/arch/_mayraise.py                         |  88 ++-
 src/frob/arch/_patterns.py                         | 252 ++++----
 src/frob/arch/_python.py                           |   1 +
 src/frob/arch/_smells.py                           |  65 ++-
 src/frob/dup/_pipeline.py                          |   1 +
 src/frob/gates/__init__.py                         | 263 ++++++---
 src/frob/gates/_docptr.py                          |  93 +--
 src/frob/gates/_fmt_directives.py                  | 173 ++++--
 src/frob/gates/_pii_structural.py                  |  61 +-
 src/frob/gates/_prework.py                         | 107 ++--
 src/frob/gates/_protocol_summary.py                | 524 +++++++++++------
 src/frob/graph/__init__.py                         | 102 ++--
 src/frob/graph/dsl.py                              | 451 ++++++++------
 src/frob/graph/summary.py                          | 257 +++++---
 src/frob/mutate/__init__.py                        |  64 +-
 src/frob/natives/_build.py                         | 164 +++---
 src/frob/perf/_advisories.py                       |  46 +-
 src/frob/perf/_effect_summaries.py                 |  62 +-
 src/frob/tickets/__init__.py                       | 360 +++++++-----
 src/frob/tickets/_land.py                          | 648 +++++++++++++--------
 src/frob/tickets/_leases.py                        | 339 ++++++-----
 src/frob/tickets/_live_tracker.py                  |  39 +-
 src/frob/tickets/_models.py                        |  26 +-
 src/frob/tickets/_mutation_evidence.py             | 150 +++--
 .../test_app_runners_t0976_mutation_evidence.py    | 219 +++++++
 tickets.md                                         | 174 +++++-
 uv.lock                                            |   2 +-
 36 files changed, 3722 insertions(+), 1887 deletions(-)
```

### Evidence
- `tests/unit/test_arch.py::TestMayRaiseResolver::test_fixture_chain_own_raise_and_builtin_raiser_and_catch_subtraction` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestPatternRecommender::test_dataclass_boilerplate_recommends_dataclass` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestLayeringViolations::test_disallowed_cross_layer_edge_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestLockOrderingHazards::test_two_lock_ab_ba_cycle_fires_within_one_function` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestModuleDependencyCycles::test_two_file_import_cycle_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestProtocolSummaryEngine::test_leaf_function_summary_is_its_own_declarations` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestPreworkSweepBounds::test_sweep_ticket_honors_graph_excludes` (pytest node id, verified passing when recorded)
- `tests/test_gates_fmt_directives.py::TestFormatPaths::test_check_mode_reports_without_writing` (pytest node id, verified passing when recorded)
- `tests/test_pii_structural_gate.py::TestFieldNames::test_password_field_fires` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestSpliceLedger::test_same_id_newer_state_wins` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestArchiveRefusesDuringInFlightWork::test_archive_refuses_when_a_live_lease_exists` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestSweepWorktrees::test_expired_lease_clean_removed` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_advisories.py::TestNestedLoopFaninAdvisories::test_hot_loop_with_multiple_callers_fires` (pytest node id, verified passing when recorded)
- `tests/unit/test_natives_build.py::TestNativesRunner::test_build_reports_success` (pytest node id, verified passing when recorded)
- `tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence::test_adversarial_test_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_ticket_done_report_claims.py::TestSetDoneReportClaims::test_claims_captured_from_real_callables` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_t0976_mutation_evidence.py::TestCollectStacksViaSamplerArgvStripping::test_non_marker_first_arg_is_not_stripped` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_t0976_mutation_evidence.py::TestCollectStacksViaSamplerArgvStripping::test_marker_first_arg_is_stripped` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_t0976_mutation_evidence.py::TestCollectStacksViaSamplerArgvStripping::test_empty_argv_falls_back_to_dash_q` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_t0976_mutation_evidence.py::TestRenderDoableDispatchableByParentGrouping::test_parent_id_not_in_queue_falls_back_to_no_parent_bucket` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_t0976_mutation_evidence.py::TestRenderDoableDispatchableByParentGrouping::test_parent_id_present_in_queue_uses_its_title` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_t0976_mutation_evidence.py::TestCloseGuardsMutationEvidenceDowngrade::test_true_mutation_evidence_with_skip_flag_is_never_downgraded` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_t0976_mutation_evidence.py::TestCloseGuardsMutationEvidenceDowngrade::test_false_mutation_evidence_with_skip_flag_is_downgraded_to_none` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_t0976_mutation_evidence.py::TestCloseGuardsMutationEvidenceDowngrade::test_false_mutation_evidence_without_skip_flag_stays_false` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 24 passed (from 24 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
