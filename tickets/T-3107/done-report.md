## Done report

Delivered the primitive half of T-3089's re-scope: a genuine three-way
squash merge composed OFF the shared root.

VERDICT ON THE THREE-WAY-MERGE FINDING: confirmed, and it understates the
problem. Beyond `compose_tree_out_of_tree` being diff-and-apply where
`_squash_and_splice_ledger` is a three-way merge with per-path resolution
(T-0479 out-of-scope ours, T-1002 union zones, T-1434 coverage-lock merge),
SIX downstream stages in `_land_squash_apply_finish` read root's WORKING
TREE and INDEX -- `_splice_and_stage`, `_apply_release_bump`,
`_apply_gate_rule_sync`, `_assert_land_complete`/`_staged_files`,
`_apply_pre_commit_sweep_or_unwind`, `_commit_squash_apply`. Composing only
the squash out-of-tree leaves every one of them reading an index nothing
populated: a land that commits nothing while writing `state: done`.

DECISIVE ENVIRONMENTAL FACT: this machine runs git 2.34.1.
`git merge-tree --write-tree` needs 2.38+. 2.34's `merge-tree` prints a
textual preview and writes no tree and no index, so "extend the primitive
to a real out-of-tree three-way merge" has no plumbing available. A
disposable `git worktree` (T-3095's technique) is the only mechanism left,
and it is also the only one that can host T-3102's Tier-A auto-fix, which
must mutate real files on disk.

WHAT LANDED
- `compose_squash_in_disposable_worktree(repo, base_commit, branch_name)`,
  a context manager: detached worktree at `base_commit`, real
  `git merge --squash --no-commit`, yields `SquashStage(worktree,
  conflicted)`, always removes the worktree. Conflicts are DATA, not an
  `Err`, so the existing `_auto_resolve_out_of_scope_conflicts` can run
  against `stage.worktree` verbatim.
- `fold_worktree_into_commit(repo, worktree, base_commit, message)`:
  write-tree/commit-tree into a commit object parented on `base_commit`.
  Moves no ref -- `publish_ref_cas` still owns publishing.
- `LandComposeError.WorktreeSetupFailed`.

BUG THE FIXTURE CAUGHT, worth recording: `fold_worktree_into_commit`
originally relied on `git write-tree` refusing an unmerged index. It does
not get the chance -- `git add -A` RESOLVES each unmerged entry by staging
the conflict-marker text verbatim, after which write-tree succeeds and the
markers land in a real commit. The must-fire fixture
(`test_fold_refuses_while_paths_are_unmerged`) failed on exactly that. The
fold now checks for unmerged paths BEFORE staging; the docstring says why
the order cannot be swapped.

ALSO FIXED IN PASSING (in scope): all three T-3088 `frob:doc` anchors were
broken -- the slug dropped the underscores (`frobticketslandcompose`
instead of `frobtickets_land_compose`), so every one resolved to nothing
and DOC002 plus COV001 fired on `LandComposeError`,
`compose_tree_out_of_tree` and `publish_ref_cas`. Corrected.

NOT DELIVERED, deliberately: nothing is wired into the live land path, so
root is still dirty during a real land. A concurrent `git status` poll
would read DIRTY at every sample today, and saying otherwise would be a
false claim. That measurement belongs to T-3089, which is now blocked on
this ticket and whose body carries the corrected plan.

### Changed
```
 docs/modules/tickets-landing.md   |  40 ++++++
 frob.lock                         |  14 +++
 src/frob/tickets/_land_compose.py | 247 ++++++++++++++++++++++++++++++++++++--
 tests/unit/test_land_compose.py   | 159 ++++++++++++++++++++++--
 tickets/T-3107/ticket.md          |  18 ++-
 5 files changed, 462 insertions(+), 16 deletions(-)
```

### Evidence
- `tests/unit/test_land_compose.py::TestDisposableSquashWorktree::test_clean_squash_reports_no_conflicts` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_compose.py::TestDisposableSquashWorktree::test_conflicting_squash_reports_the_conflicted_paths` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_compose.py::TestDisposableSquashWorktree::test_root_worktree_untouched_by_clean_squash` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_compose.py::TestDisposableSquashWorktree::test_root_worktree_untouched_by_conflicted_squash` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_compose.py::TestFoldWorktreeIntoCommit::test_folded_commit_contains_both_sides` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_compose.py::TestFoldWorktreeIntoCommit::test_fold_refuses_while_paths_are_unmerged` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 80 error(s), 755 warning(s), 864 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@.claude/hooks/frob-suggest.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@.claude/hooks/frob-suggest.py, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/commands/narrative.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-2996/ticket.md, DOC006@tickets/T-3022/ticket.md, DOC006@tickets/T-3023/ticket.md, DOC006@tickets/T-3086/ticket.md, DOC006@tickets/T-3105/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_process_reap.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_process_reap.py, DRIFT002@tests/unit/test_reopen_ticket.py, I001@/home/logan/projects/frob/.claude/worktrees/t-3107/tests/unit/verify/test_quarantine.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, OPAQUE001@src/frob/refactor/_scan.py, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3107, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REF002@src/frob/tickets/_land_compose.py, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_ghio.py, SYS003@tests/test_narrative_migrate.py, TEST001@scripts/branch_stranded_work_analysis.py, TEST001@strata-core/src/graph/model.rs, TEST001@strata-core/src/graph/query.rs, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py, WIRE003@.claude/hooks/frob-suggest.py
