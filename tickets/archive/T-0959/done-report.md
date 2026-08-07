## Done report

Root cause confirmed: `tickets-archive.md` had no per-id splice discipline
at all in `frob ticket land` -- unlike `tickets.md` (`_splice_and_stage`,
T-0740's `_check_ledger_id_integrity` backstop), the archive file rode
along on whatever git's raw merge/checkout produced at both land merge
points (`_merge_main_into_worktree`'s conflict auto-resolve, and
`_squash_and_splice_ledger`'s final squash-apply onto root). A reproducible
regression case shows the real loss shape: when the worktree ALSO
independently archives its own ticket (a genuine two-sided divergence on
tickets-archive.md, not a one-sided fast-forward git resolves for free),
the pre-fix code silently drops that side's addition entirely -- confirmed
by running the new regression test against the pre-fix `_land.py` (fails)
and post-fix `_land.py` (passes).

Fix: added `_splice_and_stage_archive` (mirrors `_splice_and_stage`'s
tickets.md discipline) -- parses both sides as ledgers, unions by id
keeping newest (`_merge_ledger_tickets`/`_newer`), then refuses loudly
(`Err(GitFailed)`) if any id present in the AUTHORITATIVE side (root/main's
current archive at that call site) would vanish from the merged result --
the T-0959 id-integrity assertion extending T-0740's
`_check_ledger_id_integrity` pattern to this file. Wired into both land
merge points: `_merge_main_into_worktree` (worktree gets main's archive
splice) and `_squash_and_splice_ledger` (root gets the final archive
splice, using root's freshest tip captured right before the squash as
authoritative). `tickets-archive.md` also added to the out-of-scope-
conflict exclusion set in `_auto_resolve_out_of_scope_conflicts`
(previously only `tickets.md` was excluded from raw `git checkout`
auto-resolution).

Changed:
- src/frob/tickets/_land.py
  - `_read_archive_text_or_empty` (new)
  - `_splice_and_stage_archive` (new)
  - `_merge_main_into_worktree` (now also splices tickets-archive.md)
  - `_squash_and_splice_ledger` (now also splices tickets-archive.md)
  - `_auto_resolve_out_of_scope_conflicts` (excludes tickets-archive.md too)
  - docstring fixes on `_check_only_tickets_conflicted`/
    `_check_squash_conflicted` (mention tickets-archive.md)
- tests/test_ticket_land.py
  - `TestArchiveSpliceDiscipline` (new): two unit tests on
    `_splice_and_stage_archive` directly (union-by-id merge, id-integrity
    refusal) plus one end-to-end `land()` regression test reproducing the
    T-0703 incident shape (worktree with a stale archive + main with newer
    archived blocks, PLUS the worktree independently archiving its own
    sibling ticket -- the two-sided-divergence shape that actually fails
    pre-fix) -> land preserves both sides' archived blocks.

Evidence (collected via `pytest --collect-only`, 3/3 resolve):
- tests/test_ticket_land.py::TestArchiveSpliceDiscipline::test_splice_and_stage_archive_merges_by_id_never_overwrites
- tests/test_ticket_land.py::TestArchiveSpliceDiscipline::test_splice_and_stage_archive_refuses_when_authoritative_id_would_vanish
- tests/test_ticket_land.py::TestArchiveSpliceDiscipline::test_land_preserves_mains_newly_archived_blocks_over_a_stale_worktree_archive
  (acceptance criterion 0 bound to this evidence id)

`uv run pytest tests/test_ticket_land.py -q -p no:cacheprovider -k TestArchiveSpliceDiscipline`
-> 3 passed. Manually confirmed the end-to-end test fails against the
pre-fix `_land.py` (git-diff-and-revert-only-that-file, no test changes)
and passes against the post-fix file.

`uv run pytest tests/test_ticket_land.py -q -p no:cacheprovider` (full
module, minus 6 pre-existing-on-main env-artifact failures unrelated to
this change -- confirmed independently failing against unmodified
`_land.py` too: TestLand::test_dry_run_lands_cleanly_and_leaves_no_trace,
TestMergeConflictOutsideLedger::test_real_conflict_outside_tickets_md_aborts,
TestGitSubprocessFailures::test_unowned_deletions_diff_failure_after_merge,
TestWipCommitNormalizationOnlyDirty::test_normalization_only_dirty_worktree_treated_as_no_op_not_git_failed
(all four: stray `.frob/derived.lock` untracked file trips a "leaves no
trace" assertion), and
TestClaimDivergencePostMerge::test_unmeasured_fresh_check_skips_gate_reverification_land_proceeds,
TestDoneReportThenLandRealClosuresEndToEnd::test_real_closures_done_report_then_land_succeeds
(both: `uv run pytest --collect-only` subprocess spawned inside a fixture
worktree fails to collect in this sandboxed environment)) -> all remaining
tests pass.

`uv run ruff check src/frob/tickets/_land.py tests/test_ticket_land.py`
and the PATH `ruff check` (same two files) -> both clean.

Filed: none (no out-of-scope work found).

Gates: not run repo-wide (chunked `frob check` not needed for this
scoped, test-verified fix); scoped test suite and ruff both clean as
above. `frob ticket close` will re-verify evidence/Done-report from
scratch.
