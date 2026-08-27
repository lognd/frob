## Done report

Flipped `frob ticket land`'s squash-apply transaction off the shared root
checkout: `_land_locked` now calls `_squash_apply_on_disposable_stage`,
which cuts a disposable worktree detached at `pre_land_tip`, runs the real
three-way `git merge --squash` in it via
`compose_squash_in_disposable_worktree` (T-3107), hands it to
`_land_squash_apply` as `stage` with `squash_precomposed=True` so the
merge cannot run twice, and seals the transaction with
`_publish_squash_apply`: `fold_worktree_into_commit` (T-3107) +
`publish_ref_cas` (T-3088) + `resync_root_to_published_tip` (T-3114).
`_commit_squash_apply`'s in-tree `git commit` is replaced wholesale on
this path.

MEASUREMENT (attributable by construction; the fleet was quiesced but the
headline number does not depend on that, because each arm runs in its own
throwaway repo under /tmp, never the shared root). Same repo shape, same
ticket, same operation; the only difference is which path seals the
transaction. A poller reads `git --no-optional-locks status --porcelain`
continuously (never a plain `git status`, which takes `.git/index.lock`
and has killed a real land), bracketing each status read with a HEAD read
on both sides so a sample straddling the publish is discarded rather than
miscounted:

  BEFORE (in-root path):   16/21 pre-publish samples dirty = 76.2%
  AFTER  (disposable stage): 0/41 pre-publish samples dirty =  0.0%

The BEFORE arm is the positive control: the instrument demonstrably fires,
so the AFTER zero is a measured zero and not an unmeasured one.

FAILURE SEMANTICS, as settled in T-3089's body and implemented here:
- A lost CAS means main moved since `pre_land_tip` -- the SAME condition
  `land()` already refuses for -- so it surfaces as `LandError.DirtyMain`,
  not a new error class.
- The post-publish resync is NOT a land failure. The commit is public and
  correct by then, so an Err is logged at ERROR with the ticket, the
  published sha and the `git read-tree -m -u <old> <new>` recovery
  command, surfaced as the new non-fatal `LandReport.root_resync_failed`,
  attempted EXACTLY once, and never reverted.

THE T-1036 TRADEOFF, MEASURED RATHER THAN ASSUMED: the v1 monofile splice
reads root's WORKING-TREE tickets.md as its base, so a concurrent
`frob ticket new` writer would be carried into the composed commit while
root still holds it uncommitted -- exactly the shape `read-tree -m -u`
refuses. This repo is NOT exposed: `_store_mode` reports `v2`, and
`_squash_and_splice_ledger_v2` performs no ledger splice at all and never
reads root's working-tree tickets.md. A concurrent `frob ticket new`
writes a NEW untracked ticket directory, and untracked paths do not block
`read-tree -m -u`; a concurrent `frob ticket evidence` modifies one
tracked `tickets/T-####/ticket.md`, which blocks only if this land's own
changeset touches that same ticket's file. The guaranteed-collision shape
is specific to v1 consumers and degrades to a loud, non-destructive,
operator-recoverable blocked resync rather than to data loss. Declared in
docs/modules/tickets-landing.md#the-disposable-stage-flip-t-3121 rather
than silently accepted.

THE CARVE-OUT, DECLARED NOT INFERRED: a supplied `pre_commit_sweep`
(T-1514 -- every profile except `rapid`) keeps the old in-root path. That
sweep spawns an unscoped `frob check` in whatever directory it is handed;
a freshly-cut disposable worktree has no `.venv`, no built natives and no
`.frob` cache, so it would either report `unmeasurable` -- silently
disabling a guard, the exact silent-zero shape that costs this repo
debugging sessions -- or report mass phantom findings and falsely refuse
every land. Handing it `root` instead would be worse: under the flip root
does not hold the staged changeset, so the sweep would return a clean
answer about the wrong tree. Shipping either would have been worse than
the contention being fixed. The carve-out is declared three ways: an
INFO log line naming it at runtime, its own branch and docstring
paragraph in `_squash_apply_on_disposable_stage`, and a dedicated "What
deliberately did NOT move" section in the doc. This repo runs
`profile = "rapid"`, so the flip does fire here.

PER-PATH CONFLICT SEMANTICS PRESERVED: nothing in the resolution path was
touched. `compose_squash_in_disposable_worktree` runs a REAL `git merge
--squash --no-commit` and treats a conflict as DATA, so
`_check_squash_conflicted[_v2]` still calls
`_auto_resolve_out_of_scope_conflicts(stage, ticket, keep="ours")`
verbatim -- T-0479 out-of-scope ours-resolution, T-1002 union zones,
T-1434 elementwise-max on frob-coverage.lock.json, T-1637 sibling
carry-forward, and the loud in-scope `SquashConflict` all reach exactly
the code they reached before. The only change to the splice helpers is a
`merge_already_composed` guard around the merge they used to perform
themselves.

UNWIND AUDIT (every path that could reset ROOT on a pre-publish failure):
- `_squash_and_splice_ledger[_v2]`, `_unwind_squash_apply`,
  `_apply_release_bump`, `_apply_gate_rule_sync`, `_assert_land_complete`,
  `_apply_pre_commit_sweep_or_unwind`, `_commit_squash_apply`: all already
  take `stage` (T-3089) and reset the disposable checkout, which is
  correct and cheap -- and redundant, since dropping the worktree IS the
  unwind.
- `_assert_still_on_expected_branch` was the ONE remaining root-side
  unwind: it called `_unstage_index_only(root)`. Under the flip root's
  index holds nothing of this land's, so that call could only have
  discarded a SIBLING's staged work. It is now suppressed via a new
  `unstage_on_drift=False` on the composed path. The CHECK itself still
  runs unchanged -- the CAS moves `refs/heads/<expected_branch>`, so
  verifying root's HEAD still names that branch is exactly as load-bearing
  as before.
- Nothing else in the pre-publish sequence writes to root.
- `_land_commit_details` / `_record_land_commit` /
  `_post_publish_native_rebuild` still run against root, AFTER the publish
  and resync, per T-3111's ordering.

ALSO: dropped the three `frob:waive WIRE001 follow_up="T-3121"` waivers on
`compose_squash_in_disposable_worktree`, `fold_worktree_into_commit` and
`resync_root_to_published_tip` -- they named this ticket as the caller
that would wire them, and it did.

ACCEPTANCE 3 is bound to an EXISTING land test that still passes
unmodified. It is deliberately NOT bound to a
`tests/test_ticket_land.py` node id: T-3123's in-process `FROB_WORKTREE`
leak makes those unbindable today (`frob ticket evidence` refuses them as
"did not pass on last run"). That criterion is instead bound by
measurement, recorded here: `tests/test_ticket_land.py` runs
150 failed / 330 collected on this branch and 150 failed / 330 collected
on unmodified main. The two failing SETS differ by 3 tests in each
direction, which is xdist ordering noise in that same leak class -- all
six were re-run in isolation on BOTH trees and produced byte-identical
outcomes. `TestOutOfScopeConflictAutoResolved` (the T-0479 per-path
resolution test) passes on both. No regression.

### Changed
```
 docs/modules/tickets-landing.md    | 113 +++++++++++++
 src/frob/tickets/_land.py          | 120 ++++++++++++-
 src/frob/tickets/_land_compose.py  |  16 --
 src/frob/tickets/_land_squash.py   | 232 +++++++++++++++++++++++---
 src/frob/tickets/_models.py        |  11 ++
 tests/unit/test_land_stage_flip.py | 334 +++++++++++++++++++++++++++++++++++++
 tickets/T-3121/ticket.md           |  37 +++-
 tickets/T-3126/ticket.md |  67 ++++++++
 tickets/T-3127/ticket.md |  61 +++++++
 9 files changed, 945 insertions(+), 46 deletions(-)
```

### Evidence
- `tests/unit/test_land_stage_flip.py::TestDisposableStageFlip::test_root_never_goes_dirty_during_the_squash_apply` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_stage_flip.py::TestPublishSquashApply::test_racing_publish_surfaces_dirtymain` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_stage_flip.py::TestPublishSquashApply::test_blocked_resync_is_not_a_land_failure` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_squash_stage.py::TestSquashApplyStageTarget::test_default_stage_runs_the_whole_transaction_in_root` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 86 error(s), 1219 warning(s), 864 waived
- error-findings: AFFECT001@src/frob/tickets/_land_squash.py, ARCH001@src/frob/tickets/_land_squash.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@.claude/hooks/frob-suggest.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@.claude/hooks/frob-suggest.py, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/commands/narrative.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-2996/ticket.md, DOC006@tickets/T-3022/ticket.md, DOC006@tickets/T-3023/ticket.md, DOC006@tickets/T-3086/ticket.md, DOC006@tickets/T-3115/ticket.md, DOC006@tickets/T-3122/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_process_reap.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_process_reap.py, DRIFT002@tests/unit/test_reopen_ticket.py, DUP001@tests/unit/test_land_stage_flip.py, I001@/home/logan/projects/frob/.claude/worktrees/t-3121/tests/unit/verify/test_quarantine.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3121, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, SUPPRESS001@src/frob/app/_config_external.py, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_ghio.py, SYS003@tests/test_narrative_migrate.py, TEST001@scripts/branch_stranded_work_analysis.py, TEST001@strata-core/src/graph/query.rs, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py, WIRE003@.claude/hooks/frob-suggest.py, unknown-argument@tests/unit/test_app_runners_process.py, unknown-argument@tests/unit/test_pytest_spawn_env_wiring.py
