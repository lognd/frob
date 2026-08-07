## Done report

Changed:
src/frob/tickets/_land_git_ops.py (new)::_land_internal_git_env
src/frob/tickets/_land_git_ops.py::_describe_git_failure
src/frob/tickets/_land_git_ops.py::_is_ignored_path_refusal
src/frob/tickets/_land_git_ops.py::_verified_reset_root
src/frob/tickets/_land_git_ops.py::_porcelain_dirty
src/frob/tickets/_land_git_ops.py::_diff_is_frob_version_line_only
src/frob/tickets/_land_git_ops.py::_restore_lock_version_only_drift
src/frob/tickets/_land_git_ops.py::_conflicted_files
src/frob/tickets/_land_git_ops.py::_deletion_glob_too_broad
src/frob/tickets/_land_git_ops.py::_deletion_owned
src/frob/tickets/_land_git_ops.py::_abort_merge
src/frob/tickets/_land_git_ops.py::_archived_ids
src/frob/tickets/_land_git_ops.py::_splice_and_stage
src/frob/tickets/_land_git_ops.py::_read_ledger_text_or_empty
src/frob/tickets/_land_git_ops.py::_read_archive_text_or_empty
src/frob/tickets/_land_git_ops.py::_read_text_at_ref
src/frob/tickets/_land_git_ops.py::_parse_archive_side
src/frob/tickets/_land_git_ops.py::_verify_archive_merge
src/frob/tickets/_land_git_ops.py::_splice_and_stage_archive
src/frob/tickets/_land_git_ops.py::_merge_main_into_worktree
src/frob/tickets/_land_git_ops.py::_auto_resolve_out_of_scope_conflicts
src/frob/tickets/_land_git_ops.py::_checkout_and_stage
src/frob/tickets/_land_git_ops.py::_check_only_tickets_conflicted
src/frob/tickets/_land_git_ops.py::_unowned_deletions
src/frob/tickets/_land_git_ops.py::_waive_deletions_in_diff
src/frob/tickets/_land_git_ops.py::_uncommitted_waive_deletions
src/frob/tickets/_land_git_ops.py::_committed_waive_deletions
src/frob/tickets/_land_git_ops.py::_waive_deletion_declared_in_done_report
src/frob/tickets/_land_git_ops.py::_uncommitted_out_of_scope_waive_deletions
src/frob/tickets/_land_git_ops.py::_committed_out_of_scope_waive_deletions
src/frob/tickets/_land_git_ops.py::_wip_commit
src/frob/tickets/_land_git_ops.py::_wip_add_excluding_frob
src/frob/tickets/_land_git_ops.py::_do_wip_commit
src/frob/tickets/_land_git_ops.py::_rev_parse
src/frob/tickets/_land_git_ops.py::_true_merge_base
src/frob/tickets/_land_merge.py::_validate_closeable (kept, verbatim)
src/frob/tickets/_land_merge.py::_validate_acceptance_bound (kept, verbatim)
src/frob/tickets/_land_merge.py::_validate_evidence_kind_consistency (kept, verbatim)
src/frob/tickets/_land_merge.py::_commit_message (kept, verbatim)
src/frob/tickets/_land_merge.py (re-exports _archived_ids/_deletion_owned/splice_ledger for backward compat)
src/frob/tickets/_land.py (import sites updated: _land_git_ops for git-plumbing family, _land_merge for _validate_closeable)
src/frob/tickets/_land_finalize.py (import sites updated: _land_git_ops for git-plumbing family, _land_merge for _commit_message; one stale module-path comment fixed)
tests/test_ticket_land.py (added `import frob.tickets._land_git_ops as _land_git_ops_mod`, removed now-unused `_land_merge_mod` import, repointed monkeypatch targets and frob:tests directives for every moved symbol)

Split: T-1251 moved the git-plumbing/wip-commit family (main-into-worktree
merge staging, out-of-scope conflict auto-resolution, the wip-commit trio,
ledger/archive splice-and-stage, the deletion-authorization pair, and the
frob:waive-deletion laundering guards, plus their shared git primitives)
out of _land_merge.py into a new src/frob/tickets/_land_git_ops.py.
_land_merge.py: 1183 -> 172 lines (clears LARGE001; only the closeability-
validation family and the commit-message helper remain). Every moved
function kept its original body, docstring, and frob:ticket/frob:tests
directives verbatim -- pure move, zero behavior change.

_land_finalize.py's own split (T-1251's second named seam:
draft-finalization/sibling-renumbering vs. squash-apply/close vs.
release-bump/uv.lock/native-rebuild) was NOT started -- budget did not
extend to it in this pass, matching T-1194's own partial-completion
pattern. Re-filed as T-1334 rather than left as silent residue,
per TICK011.

Evidence: tests/test_ticket_land.py -- 176/176 pass (verified twice; one
xdist-parallel flake in TestClaimDivergencePostMerge unrelated to this
diff, reproduced pass in isolation both times). Bound node ids:
- tests/test_ticket_land.py::TestArchiveSpliceDiscipline::test_splice_and_stage_archive_merges_by_id_never_overwrites
- tests/test_ticket_land.py::TestArchiveSpliceDiscipline::test_splice_and_stage_archive_refuses_when_authoritative_id_would_vanish
- tests/test_ticket_land.py::TestUvLockSync::test_worktree_side_lock_flap_auto_restored_before_wip_commit
- tests/test_ticket_land.py::TestWipCommitNormalizationOnlyDirty::test_normalization_only_dirty_worktree_treated_as_no_op_not_git_failed

Filed: T-1334 (arch: split _land_finalize.py's draft/squash/release families -- T-1251 residue)

Gates: `frob check --ticket T-1251 --only arch` clean for both split
files -- no LARGE001/seam findings on _land_merge.py or _land_git_ops.py;
only pre-existing repo-wide DUP/pattern-recommendation noise (unrelated
to this ticket's files) remains in the report.

### Changed
```
 src/frob/tickets/_land.py          |    4 +-
 src/frob/tickets/_land_finalize.py |    6 +-
 src/frob/tickets/_land_git_ops.py  | 1064 +++++++++++++++++++++++++++++++++++
 src/frob/tickets/_land_merge.py    | 1085 ++----------------------------------
 tests/test_ticket_land.py          |   68 +--
 tickets.md                         |  237 +++++++-
 6 files changed, 1376 insertions(+), 1088 deletions(-)
```

### Evidence
- `tests/test_ticket_land.py::TestArchiveSpliceDiscipline::test_splice_and_stage_archive_merges_by_id_never_overwrites` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestArchiveSpliceDiscipline::test_splice_and_stage_archive_refuses_when_authoritative_id_would_vanish` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestUvLockSync::test_worktree_side_lock_flap_auto_restored_before_wip_commit` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestWipCommitNormalizationOnlyDirty::test_normalization_only_dirty_worktree_treated_as_no_op_not_git_failed` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
