## Done report

## Done report

ROOT CAUSE (confirmed by forensic replay of the actual T-0640 land commits
on this repo's history, then reproduced deterministically in a test): the
T-0640 land was run with `--worktree` pointing at the SAME checkout/branch
`root` had checked out -- no distinct feature branch was ever created for
it (the ticket's own Done report says work happened via "a manual
acceptance-binding + finalize sequence"). Proof: the final land commit
dbae6f2f's sole parent is fa709967 ("finalize and close T-0640 for
landing"), a commit that only exists on what should have been the
WORKTREE's branch -- meaning root's HEAD and the "worktree" HEAD were
literally the same ref the whole time.

With `worktree` and `root` on the identical branch, `main_branch_name`
(root's checked-out branch name, e.g. "main") and `worktree`'s `HEAD`
resolve to the exact same commit throughout `land()`:
- `_merge_main_into_worktree`'s `git merge --no-commit --no-ff main` was a
  self-merge no-op (`did_merge=False`).
- `_squash_and_splice_ledger`'s `git merge --squash --no-commit
  branch_name` (branch_name == main_branch_name here) was likewise a
  self-merge no-op -- it staged nothing.
- The T-0463 completeness assertion's `_worktree_full_changeset` diffed
  `main_branch_name...HEAD`, a branch against itself: an empty set. The
  assertion (`staged superset of expected`) passed VACUOUSLY because
  `expected` was empty, not because anything was actually verified. Only
  the release-bump write and the ledger splice (which unconditionally
  write+stage tickets.md/version files regardless of the diff) ended up in
  the final commit -- exactly the observed 4-file false-green.

FIX (`src/frob/tickets/_land.py`): `_worktree_full_changeset` now computes
the merge-base explicitly via a new `_true_merge_base` helper (`git
merge-base main_branch_name HEAD`, run in the worktree) instead of
implicitly inside a triple-dot diff, and a new `_rev_parse` helper resolves
both that merge-base and `HEAD`'s own sha. If the two are identical --
meaning the worktree branch carries not one commit beyond
`main_branch_name` -- `_worktree_full_changeset` now refuses immediately
with `Err(LandError.IncompleteLand)` and a log line naming the T-0640
false-green condition and its likely cause (same-checkout landing) before
ever reaching the diff/squash/commit steps. A genuine landing always has at
least the finalize-and-close commit uniquely on the worktree branch by the
time this runs, so merge-base == HEAD is never a legitimate "nothing to
land" case -- only this misconfiguration reproduces it. This closes the
"a NEW file the branch added that is absent from the squash is exactly the
T-0235 case it claims to cover but missed here" gap named in the ticket:
the assertion no longer degrades to "nothing to check" silently.

REGRESSION TEST (`tests/test_ticket_land.py::TestLandCompleteness::
test_worktree_pointed_at_same_branch_as_main_is_refused_not_silently_empty`):
reproduces the exact incident shape deterministically -- a new source file
is committed directly onto the fixture repo's own checked-out branch (no
`git worktree add` at all, mirroring T-0640's actual land path), the
ticket is made closeable and its state committed the same way, then
`land(repo, tid, repo)` is called (worktree == root). Verified FAILING
against the pre-fix code (via a temporary `git stash` of only
`src/frob/tickets/_land.py`, confirmed pre-fix `land()` returns
`Ok(LandReport(worktree_changeset=(), files_changed=('tickets.md',), ...))`
-- code silently dropped, ticket falsely reported landed -- then `git
stash pop` to restore the fix) and PASSING after the fix (`Err(LandError.
IncompleteLand)`, no "land T-XXXX" commit ever made, working tree clean,
`new_feature.py`'s content untouched).

### Changed
```
src/frob/tickets/_land.py   | +99 -18 (net; adds _rev_parse, _true_merge_base,
                               hardens _worktree_full_changeset)
tests/test_ticket_land.py   | +47 (one new regression test)
```

### Evidence
- `tests/test_ticket_land.py::TestLandCompleteness::test_worktree_pointed_at_same_branch_as_main_is_refused_not_silently_empty` (pytest node id, verified passing post-fix, verified failing pre-fix)

### Gates
- `uv run frob check --ticket T-0761 --only lint` clean
- `uv run frob check --ticket T-0761 --only static` clean (pre-existing waived-through export/dup/arch warnings only, no new findings)
- `uv run frob check --ticket T-0761 --only gates-fast` clean (0 errors; DRIFT/PRE errors seen mid-session were my own directive-syntax typo (`::` instead of `.` between class and method) and a stale pre-work sweep -- both fixed and re-verified clean)
- `uv run frob check --ticket T-0761 --only gates-native` clean
- `uv run frob check --ticket T-0761 --only gates-security` clean
- `uv run pytest tests/test_ticket_land.py -q` -- 59 passed
- `uv run frob test --base main` -- python suite selected+run, exit=0

### Filed
none -- no out-of-scope work discovered.

### Deviations
none. Did not run `frob ticket land` or `frob ticket close` per the
dispatch instructions; ticket is left in `in-progress` with evidence and
this Done report recorded, for a reviewer to close.

### Changed
(no changed files detected)

### Evidence
- `tests/test_ticket_land.py::TestLandCompleteness::test_worktree_pointed_at_same_branch_as_main_is_refused_not_silently_empty` (pytest node id, verified passing when recorded)
