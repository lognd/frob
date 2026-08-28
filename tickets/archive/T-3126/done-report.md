## Done report

`_record_land_commit` no longer writes, stages or commits in `root`. It
now composes the follow-up bookkeeping commit in a disposable worktree
checked out at the landing commit (`_add_scratch_worktree`, reused from
T-3095 rather than re-cut), folds it with `fold_worktree_into_commit`,
publishes it onto `root`'s own `HEAD` symref with `publish_ref_cas`
against the landing sha, and brings root forward with
`resync_root_to_published_tip`. So the post-publish ref move is now
compare-and-swap protected exactly like T-3121 made the landing commit,
and the post-publish dirty window is gone.

Decision on the ticket's question 1 (fold the record INTO the landing
commit): still not possible, and for the unchanged reason -- a commit
cannot embed its own future hash. T-3121's fold+CAS shape does not
answer it differently: the sha is known before the ref MOVES, but not
before the TREE is written, and it is the tree that would have to carry
it. Question 2 is what shipped.

MEASURED, positive-controlled, in throwaway repos under /tmp, each
porcelain sample bracketed by a HEAD read on both sides so torn samples
are discarded rather than counted:
  BEFORE (in-root write+add+commit): 8/22 untorn samples dirty = 36.4%
  AFTER  (out-of-tree + CAS):        0/61 untorn samples dirty =  0.0%
The BEFORE arm is the probe's own positive control and ships as
`test_probe_catches_the_in_root_write_positive_control`.

Must-fire proof: both new behavioral tests FAIL against the unmodified
parent tree (029d92c77) with the new module copied in -- the dirty poll
sees the in-root write, and the CAS test sees the old code fast-forward
straight past a sibling's tip. `--check-repro` itself cannot render this
verdict (T-2025: land squashes test and fix into one commit), so it was
run directly against a detached checkout of the parent.

Unwind audit: this function runs entirely POST-publish, so there is no
state of this land's left in `root` to roll back and nothing here calls
`_verified_reset_root` or `_unstage_index_only` -- the exact shape
T-3121's audit found wrong in `_assert_still_on_expected_branch`, where a
root-side unstage could only have discarded a SIBLING's staged work. Every
failure path (worktree setup, write, fold, lost CAS, blocked resync) logs
loudly and returns `None`, never a `LandError`: the land is already
sealed. A lost CAS now leaves the sibling's tip untouched instead of
clobbering it by fast-forward.

T-2274's "never absorbs a bystander's dirty file" property is now
STRUCTURAL rather than computed: the record is written into a fresh
checkout that never contained a bystander's edit, so the before/after
porcelain diffing (and `_pathspec_targets`) is gone rather than merely
still correct.

Not done here, and filed as residue: the T-3121 section of
docs/modules/tickets-landing.md still says `_record_land_commit` makes
its own follow-up commit in root and that a post-publish dirty window
remains. That file is under a LIVE lease held by T-3116, so `frob ticket
scope --add` refused it and no doc edge was bound rather than faking one.

### Changed
```
 src/frob/tickets/_land_squash.py      | 255 ++++++++++++++++++++++------------
 tests/unit/test_land_record_commit.py | 230 ++++++++++++++++++++++++++++++
 tickets/T-3126/ticket.md              |  18 ++-
 3 files changed, 416 insertions(+), 87 deletions(-)
```

### Evidence
- `tests/unit/test_land_record_commit.py::TestRecordLandCommitOutOfTree::test_root_never_goes_dirty_while_the_record_is_made` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_record_commit.py::TestRecordLandCommitOutOfTree::test_probe_catches_the_in_root_write_positive_control` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_record_commit.py::TestRecordLandCommitOutOfTree::test_record_publishes_by_cas_and_refuses_a_moved_ref` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestRecordLandCommit::test_record_land_commit_never_absorbs_a_bystanders_dirty_file` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 84 error(s), 756 warning(s), 865 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/_land_cmd.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@.claude/hooks/frob-suggest.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@.claude/hooks/frob-suggest.py, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/commands/narrative.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-2996/ticket.md, DOC006@tickets/T-3022/ticket.md, DOC006@tickets/T-3023/ticket.md, DOC006@tickets/T-3086/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_process_reap.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_process_reap.py, DRIFT002@tests/unit/test_reopen_ticket.py, DUP001@tests/unit/test_land_record_commit.py, I001@/home/logan/projects/frob/.claude/worktrees/series-bv/tests/unit/verify/test_quarantine.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3126, REF001@.claude-scratch/T-3122-close-guard-repro-capture.md, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, SUPPRESS001@src/frob/app/_config_external.py, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@src/frob/gates/_wire.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_ghio.py, SYS003@tests/test_narrative_migrate.py, TEST001@scripts/branch_stranded_work_analysis.py, TEST001@strata-core/src/graph/query.rs, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE001@tests/unit/test_land_record_commit.py, WIRE002@src/frob/gates/_tdd_order.py, unknown-argument@tests/unit/test_app_runners_process.py, unknown-argument@tests/unit/test_pytest_spawn_env_wiring.py
