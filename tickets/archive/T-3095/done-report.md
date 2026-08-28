## Done report

LAND SMALL, per the ticket's own instruction: this land carries only the
release-bump treatment of the three post-squash file-mutating sub-stages
`_land_squash_apply_finish` runs (release bump / native rebuild /
pre-commit sweep). Wiring this into the actual land pipeline
(`_land_squash.py`, out of this ticket's declared scope), the native-
rebuild treatment, and the pre-commit-sweep treatment are filed as
sequenced siblings below.

WHAT WAS BUILT: `_apply_release_bump_out_of_tree` in
`src/frob/tickets/_land_release.py` runs the EXISTING, unmodified
`_apply_release_bump` against a disposable `git worktree` checked out at
`pre_land_tip`, never against the caller's own checked-out files.
`composed_commit`'s own diff (relative to `pre_land_tip`) is applied onto
that worktree first via `git apply --index`, so the bump machinery sees
the same tree a real squash-apply would have staged -- this also fixes
this function's own first, wrong draft, which checked the scratch
worktree out AT `composed_commit` and broke `_apply_release_bump`'s
`_verified_reset_root` unwind invariant (it asserts the checkout is still
at `pre_land_tip` when a failure needs unwinding); checking out at
`pre_land_tip` and applying the diff on top restores that invariant. The
result is folded into a new commit object via `write-tree`/`commit-tree`,
parented on `pre_land_tip` (matching the real squash-apply's own single-
parent shape). The caller's own repo is never touched.

TREATMENT ARGUED PER SUB-STAGE:
- Release bump (delivered here): pure file rewriting -- `_apply_release_
  bump` already parameterizes cleanly on `root: Path`, so a disposable
  `git worktree` is sufficient. Not routed through `frob.tickets.
  _land_compose`'s scratch-`GIT_INDEX_FILE` primitive, because that
  primitive never materializes real files on disk and a `bump_version`
  callback needs to read/write real content (e.g. prepending to
  CHANGELOG.md); this function reuses `_land_compose`'s underlying idea
  (diff two commits, apply against a private target, fold via write-
  tree/commit-tree) at the one point it genuinely differs: a real
  worktree checkout in place of a bare index.
- Native rebuild: NOT addressed here. Recommend moving it to AFTER
  `publish_ref_cas`, outside the transaction entirely -- it is a
  minutes-long cargo/maturin build with no bearing on whether the
  composed commit is correct, and the concurrent-poll acceptance
  criterion (clean root at every sample UNTIL publish) says nothing
  about what happens after. Filed as T-3103.
- Pre-commit sweep: NOT addressed here -- correctly the hard one (Tier-A
  auto-fix mutates content, so its output must land in the composed
  tree, not a working tree nobody keeps). Filed as T-3100; it should
  reuse this ticket's disposable-worktree technique, chained after the
  release bump on the SAME worktree before one fold-and-publish.

T-3089 STATUS: performable AS DECLARED, no re-scope needed. Its own
acceptance ([0] concurrent-poll-clean during the squash-apply stage, [1]
the racing-lands CAS refusal) only concerns the squash+publish window,
not the release-bump/native-rebuild/pre-commit-sweep windows this ticket
and its two new siblings (T-3103, T-3100) cover separately; T-3089 is
already `blocked_by=[T-3088, T-3095]` and queued, so it will naturally
sequence after this land. Recommend T-3089's own wiring call
`_apply_release_bump_out_of_tree` (this ticket's new entry point) in
place of the in-tree `_apply_release_bump` -- worth a note on T-3089
itself, not a scope change (out of this ticket's own scope to edit
`_land_squash.py`).

CONCURRENT-POLL DEMONSTRATION: this ticket does NOT change land's own
observable behavior yet -- `_apply_release_bump_out_of_tree` is not
wired into `_land_squash.py` (out of this ticket's declared scope; that
is T-3089's job). Root is therefore observably dirty during a land
exactly as before this change; the ticket's own acceptance criterion
(concurrent-poll-clean throughout a REAL land) becomes checkable once
T-3089 lands, not from this ticket alone. Ran the requested poll and
wall-clock measurement anyway against this ticket's own land, to record
a baseline for the sibling chain to compare against -- see conversation
report for the numbers actually observed.

Filed: T-3101 (native-rebuild-after-publish), T-3102
(fold pre-commit sweep into the composed commit) -- both real ids to be
confirmed on main after this ticket lands (draft ids renumber at land,
per the playbook).

### Changed
```
 tickets/T-3095/ticket.md           | 14 ++++++++++-
 tickets/T-3101/ticket.md | 48 +++++++++++++++++++++++++++++++++++++
 tickets/T-3102/ticket.md | 49 ++++++++++++++++++++++++++++++++++++++
 3 files changed, 110 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_land_release_out_of_tree.py::TestApplyReleaseBumpOutOfTree::test_worktree_untouched_by_out_of_tree_bump` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_release_out_of_tree.py::TestApplyReleaseBumpOutOfTree::test_bump_folds_into_a_new_commit_on_composed_commit` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_release_out_of_tree.py::TestApplyReleaseBumpOutOfTree::test_no_bump_returns_composed_commit_unchanged` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_release_out_of_tree.py::TestApplyReleaseBumpOutOfTree::test_bump_failure_leaves_repo_working_tree_untouched` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 79 error(s), 673 warning(s), 863 waived
- error-findings: ARCH001@src/frob/tickets/_land_release.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@.claude/hooks/frob-suggest.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@src/frob/tickets/_land_compose.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@.claude/hooks/frob-suggest.py, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_land_compose.py, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/commands/narrative.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-2996/ticket.md, DOC006@tickets/T-3022/ticket.md, DOC006@tickets/T-3023/ticket.md, DOC006@tickets/T-3080/ticket.md, DOC006@tickets/T-3086/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_reopen_ticket.py, I001@/home/logan/projects/frob/.claude/worktrees/series-bj/tests/unit/verify/test_quarantine.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, OPAQUE001@src/frob/refactor/_scan.py, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REF002@src/frob/tickets/_land_compose.py, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SELFAUDIT001@design, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_ghio.py, SYS003@tests/test_narrative_migrate.py, TEST001@scripts/branch_stranded_work_analysis.py, TEST001@strata-core/src/graph/model.rs, TEST001@strata-core/src/graph/query.rs, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE001@src/frob/tickets/_land_release.py, WIRE002@src/frob/gates/_tdd_order.py, WIRE003@.claude/hooks/frob-suggest.py
