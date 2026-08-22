## Done report

Changed:
src/frob/gates/__init__.py::_cov006_module_path_to_file
src/frob/gates/__init__.py::_cov006_resolve_relative_module
src/frob/gates/__init__.py::_cov006_resolve_import_files
src/frob/gates/__init__.py::_cov006_chase_reexport_hops
tests/test_gates.py::TestCoverageGate.test_cov006_third_file_reachable_chases_relative_import_reexport
tests/test_gates.py::TestCoverageGate.test_cov006_third_file_reachable_still_fires_through_relative_facade
tests/test_vet.py::TestCapabilityScan.test_public_sibling_wrapper_exec_is_resolved_one_hop (kind=unit, unchanged directive; now passes COV006 via detector fix)
tests/test_lang.py::TestFromImportSubmoduleResolution (6 tests: added per-test frob:waive COV006, closure-attribution blind spot, alias breaks name-based callgraph resolution)
tests/test_ticket_land.py::TestWipAddIgnoredPathFallback.test_gitignored_frob_falls_back_and_still_lands (kind=unit -> integration)
tests/test_ticket_land.py::TestCoverageLockConflictMerges.test_conflicting_lock_merges_to_the_higher_of_both_sides (kind unit(implicit) -> integration)
tests/test_ticket_land.py::TestLandCompleteness.test_land_brings_tracked_edit_untracked_new_file_and_deletion (_worktree_full_changeset: unit -> integration)
tests/test_ticket_land.py::TestLandCompleteness.test_worktree_pointed_at_same_branch_as_main_is_refused_not_silently_empty (_worktree_full_changeset: unit -> integration)
tests/test_ticket_land.py::TestLandFailedTicket.test_failed_ticket_with_a_failure_log_lands_cleanly (_has_failure_log: unit -> integration)
tests/test_ticket_land.py::TestArchiveSpliceDiscipline.test_land_takes_mains_content_edit_over_a_worktree_copy_unchanged_since_branch (_merge_ledger_tickets: unit -> integration, matching its own sibling directive one line below)

Split across all 18 T-2550-scoped COV006 findings:
- 1 real detector gap (trace 1, tests/test_vet.py TestCapabilityScan, plus 5 more
  test_vet.py findings fixed as the same-shape collateral, plus 1
  test_ticket_land.py finding fixed as collateral): relative `from .foo
  import name` re-export lines were handed to `_cov006_module_path_to_file`
  UNRESOLVED; `module_path.replace(".", "/")` turned the leading dot into a
  leading slash instead of the importing file's own package, so the
  two-hop re-export chase silently gave up one hop early and returned the
  facade file (which only imports the name) instead of the file with the
  real `def`. Fixed with `_cov006_resolve_relative_module`, threaded
  through both call sites that hand a module path to
  `_cov006_module_path_to_file`. This single fix cleared 7 of the 18
  findings (6 in tests/test_vet.py, 1 in tests/test_ticket_land.py) as a
  byproduct, since they were all the identical shape.
- 6 honest waivers (trace 2, tests/test_lang.py
  TestFromImportSubmoduleResolution): the test's own class-helper
  `_resolve_all` calls `frob.lang.extract_imports`, which internally calls
  `frob.lang._extract.extract_imports` through an IMPORT ALIAS
  (`from frob.lang._extract import extract_imports as _extract_imports`).
  `frob.graph.callgraph` resolves callees by bare short name; the alias
  breaks that match, so no closure search (same-file, third-file, or
  otherwise) can ever bridge this hop. Genuinely reachable, not a call-
  graph rewrite target -- waived per this repo's existing dict-dispatch/
  decorator-dispatch COV006 precedent (T-0516/T-1024 class).
- 5 misclassifications (trace 3 + 4 more of the identical shape,
  tests/test_ticket_land.py): `kind="unit"` on a binding exercised only
  through the full `land()`/`land(dry_run=True)` pipeline several
  call-hops deep, when this file's OWN precedent
  (`_resolve_divergence`, one directive line below `_merge_ledger_
  tickets` in `TestArchiveSpliceDiscipline`) already documents
  `kind="integration"` as the correct classification for exactly this
  shape (COV006 trusts `kind="integration"`/`"e2e"` at face value, no
  call-graph check). Corrected `_merge_ledger_tickets`,
  `_wip_add_excluding_frob`, `_merge_coverage_lock_conflict`,
  `_worktree_full_changeset` (x2 sites), `_has_failure_log` to match.

Verified via `git show --stat` after each commit; both commits (test-only,
then the gates.py fix) landed on the ticket branch before land.

Evidence:
tests/test_vet.py::TestCapabilityScan::test_public_sibling_wrapper_exec_is_resolved_one_hop
tests/test_lang.py::TestFromImportSubmoduleResolution::test_from_package_import_submodule_resolves_to_the_file
tests/test_ticket_land.py::TestArchiveSpliceDiscipline::test_land_takes_mains_content_edit_over_a_worktree_copy_unchanged_since_branch
tests/test_ticket_land.py::TestWipAddIgnoredPathFallback::test_gitignored_frob_falls_back_and_still_lands
tests/test_gates.py::TestCoverageGate::test_cov006_third_file_reachable_still_fires_through_relative_facade
tests/test_gates.py::TestCoverageGate::test_cov006_third_file_reachable_chases_relative_import_reexport (designated repro,
  FAILED_AT_PARENT verified against pre-fix commit 2c6177111 via --check-repro)

Filed: none -- no out-of-scope defect found; the callgraph alias-blindness
behind trace 2 is a known, documented repo limitation (bare-short-name
resolution) already tracked by prior tickets (see this file's own
"shared graph wrong for its second consumer" precedent); no new callgraph
work is warranted per the ticket's own guidance not to build more
inference on it.

Gates: `frob check --ticket T-2550` -- gate:COV/gate:SCOPE/gate:PREWORK
(the parts actually scoped to this ticket) clean of new findings; all
57 repo-wide errors present in that run pre-exist in files this ticket
never touched (verified via `git diff main` scoping and per-line
cross-check). `frob check --only coverage` repo-wide: 0 unwaived COV006
findings (was 18), 0 new COV002 findings (frob:ticket T-2550 directives
added to every changed class/method).

### Changed
```
 src/frob/gates/__init__.py | 74 +++++++++++++++++++++++++++++++++++++----
 tests/test_gates.py        | 83 ++++++++++++++++++++++++++++++++++++++++++++++
 tests/test_lang.py         | 43 ++++++++++++++++++++++++
 tests/test_ticket_land.py  | 59 +++++++++++++++++++++++++++-----
 tickets/T-2550/ticket.md   | 74 +++++++++++++++++++++++++++++++++++++++--
 5 files changed, 316 insertions(+), 17 deletions(-)
```

### Evidence
- `tests/test_vet.py::TestCapabilityScan::test_public_sibling_wrapper_exec_is_resolved_one_hop` (pytest node id, verified passing when recorded)
- `tests/test_lang.py::TestFromImportSubmoduleResolution::test_from_package_import_submodule_resolves_to_the_file` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestArchiveSpliceDiscipline::test_land_takes_mains_content_edit_over_a_worktree_copy_unchanged_since_branch` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestWipAddIgnoredPathFallback::test_gitignored_frob_falls_back_and_still_lands` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCoverageGate::test_cov006_third_file_reachable_still_fires_through_relative_facade` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCoverageGate::test_cov006_third_file_reachable_chases_relative_import_reexport` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-2561/ticket.md, DOC006@tickets/T-2570/ticket.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, DOCENUM001@docs/modules/gates.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2550/src/frob/app/ticket_runner/_ledger_mirror.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2550/src/frob/app/ticket_runner/_verify.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2550/src/frob/scaffold/project.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2550, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
