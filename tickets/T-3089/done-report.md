## Done report

Landed the RETARGETING half of T-3089 and deferred the switch-flip.

WHAT LANDED. `_land_squash_apply` now takes a `stage: Path` naming the ONE
checkout the whole six-stage squash-apply transaction is performed in, and
all six stages were retargeted onto it together:

  1. the `git merge --squash --no-commit` itself and the per-path conflict
     resolution over the unmerged index it leaves
     (`_check_squash_conflicted[_v2]` ->
     `_auto_resolve_out_of_scope_conflicts`);
  2. the ledger + archive splice and `git add`
     (`_splice_and_stage`, `_splice_and_stage_archive`);
  3. the REL001 release bump (`_apply_release_bump`);
  4. the gate-rule registry sync (`_apply_gate_rule_sync`);
  5. the T-0463 completeness assertion, which reads `git diff --cached`
     (`_assert_land_complete` / `_staged_files`);
  6. the T-1514 Tier-A pre-commit sweep and the landing commit
     (`_apply_pre_commit_sweep_or_unwind`, `_commit_squash_apply`).

`stage` defaults to `root`, so this land changes no observable behavior:
the transaction still happens in the shared checkout today. What it buys is
that the flip is now a caller-side change instead of a rewrite of nine
helpers.

WHY ALL SIX AT ONCE. Composing only some of them leaves the rest reading an
index nothing populated -- a land that commits nothing while still writing
`state: done`, which has actually occurred in this repo. So `stage` is
deliberately one switch over the whole sequence, never a per-stage option.

WHAT DELIBERATELY DID NOT FOLLOW `stage`, and why. `ledger_lock(root)` and
the ledger/archive base texts re-read under it stay on `root`: T-1036's
lost-update fix is about capturing whichever concurrent `frob ticket
new`/`evidence` writer got to root's working-tree tickets.md first, and such
a writer never touches a disposable stage. The stacked-sibling absorption
EVIDENCE (`_absorption_verified`, `_report_stacked_sibling_absorption`)
stays on `root` because "a prior land already did this" is a claim about
root's landed history; only the emptiness check that triggers it reads
`stage`'s index. `_assert_still_on_expected_branch` (T-1920) stays on `root`
because a disposable stage is detached by construction. Every unwind path
follows `stage`: `_verified_reset_root` against a disposable worktree
detached at `pre_land_tip` resets exactly the throwaway tree.

PER-PATH CONFLICT SEMANTICS PRESERVED EXACTLY. Nothing about the merge or
its resolution changed -- it is still `git merge --squash --no-commit`
followed by `_auto_resolve_out_of_scope_conflicts` VERBATIM, so T-0479's
out-of-scope ours-resolution, T-1002's union zones, T-1434's elementwise-max
merge of frob-coverage.lock.json, T-1637's sibling carry-forward and the
loud `SquashConflict` for a genuine in-scope conflict all survive untouched.
Only WHICH checkout the unmerged index lives in is now a parameter. This is
why the re-scope notice rules out substituting `compose_tree_out_of_tree`'s
diff-and-apply for the three-way merge: that substitution deletes all of it.

WHAT I DEFERRED, AND WHY. The flip itself -- composing the squash in a
disposable worktree, folding it into a commit object, publishing by CAS, and
resyncing root -- is a second, larger change touching `_land.py`'s
orchestration, `_commit_squash_apply`'s replacement by
`fold_worktree_into_commit` + `publish_ref_cas`, the post-publish resync's
non-fatal reporting on `LandReport`, and the unwind audit. Landing it
together with this retargeting would be exactly the large-unlanded-branch
shape five prior agents on this epic correctly refused. It is filed as a
sequenced sibling carrying acceptance criteria 0 and 1, with the full recipe
and the settled resync semantics written into its body.

ACCEPTANCE STATUS, honestly. AC0 ("no intermediate dirty state observable in
root") is proven for `_land_squash_apply` as a unit -- the must-fire fixture
asserts root's HEAD, index and working tree are untouched while the landing
commit lands on the stage -- but NOT yet end-to-end through `frob ticket
land`, because the caller still passes the default. AC1 (two lands racing
the same base tip get the DirtyMain-class refusal) is entirely the flip
ticket's; nothing here touches ref publication. I bound evidence to AC0 only
and left AC1 unbound rather than claiming it.

FIXTURES. A must-stay-quiet / must-fire pair in a NEW module,
tests/unit/test_land_squash_stage.py: omitting `stage` lands on `root`
exactly as before; passing a disposable worktree leaves root's HEAD, index,
working tree and file contents all untouched while the real landing commit
with the real changeset appears on the stage. They live in their own module
because tests/test_ticket_land.py leaks FROB_WORKTREE in-process -- measured
145 WorktreeLeaseViolation refusals on an UNMODIFIED main versus 143-144
with this diff, so it is pre-existing -- and evidence bound there does not
resolve. That is filed as its own bug rather than worked around silently.

### Changed
```
 tickets/T-3089/ticket.md           |  89 +++++++++++++++++++++++++++++-
 tickets/T-3123/ticket.md |  71 ++++++++++++++++++++++++
 tickets/T-3121/ticket.md | 109 +++++++++++++++++++++++++++++++++++++
 3 files changed, 266 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/unit/test_land_squash_stage.py::TestSquashApplyStageTarget::test_explicit_stage_leaves_root_completely_untouched` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_squash_stage.py::TestSquashApplyStageTarget::test_default_stage_runs_the_whole_transaction_in_root` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 86 error(s), 1178 warning(s), 866 waived
- error-findings: AFFECT001@src/frob/tickets/_land_squash.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@.claude/hooks/frob-suggest.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@.claude/hooks/frob-suggest.py, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/commands/narrative.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-2996/ticket.md, DOC006@tickets/T-3022/ticket.md, DOC006@tickets/T-3023/ticket.md, DOC006@tickets/T-3086/ticket.md, DOC006@tickets/T-3110/ticket.md, DOC006@tickets/T-3115/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_process_reap.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_process_reap.py, DRIFT002@tests/unit/test_reopen_ticket.py, I001@/home/logan/projects/frob/.claude/worktrees/series-bs/tests/unit/verify/test_quarantine.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3089, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REF002@src/frob/tickets/_land_compose.py, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, SUPPRESS001@src/frob/app/_config_external.py, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_ghio.py, SYS003@tests/test_narrative_migrate.py, TEST001@scripts/branch_stranded_work_analysis.py, TEST001@strata-core/src/graph/model.rs, TEST001@strata-core/src/graph/query.rs, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE001@tests/unit/test_land_squash_stage.py, WIRE002@src/frob/gates/_tdd_order.py, WIRE003@.claude/hooks/frob-suggest.py, unknown-argument@tests/unit/test_app_runners_process.py, unknown-argument@tests/unit/test_pytest_spawn_env_wiring.py
