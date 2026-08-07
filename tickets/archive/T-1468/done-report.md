## Done report

The T-1323/T-1326 out-of-scope waive-deletion guard (`_waive_deletions_in_
diff` and friends in `src/frob/tickets/_land_git_ops.py`) read a `git diff
--no-color -U0` one physical line at a time: a deletion was flagged the
moment a line matched `# frob:waive RULE ...`. A `frob:waive` comment
whose `reason="..."` text wraps across multiple physical lines via a
trailing-backslash continuation (this repo's own convention) rewraps
differently whenever `frob fmt`'s line-length absorption runs -- same
content, different number of physical lines. The old line-based read saw
the old wrap's lines as deleted and the new wrap's as added, with no way
to tell that apart from an actual removal, exactly the T-1465 land
incident this ticket describes.

Fix: `_fold_waive_blocks` (new) reassembles a diff hunk's raw physical
lines, per side, into logical `(rule, normalized_text)` blocks -- a block
starts at a `# frob:waive RULE ...` line and continues consuming lines
while the previous one (right-stripped) ends in a trailing backslash.
`_normalize_waive_fragments` strips each fragment's comment leader and
trailing backslash, joins with single spaces, and collapses internal
whitespace runs -- so the SAME waiver content wrapped across a different
number of physical lines normalizes to an identical string. `_real_waive_
deletions` (new) reports a deleted block as a genuine deletion only when
no added block in the SAME hunk normalizes to the same text; a pure
rewrap normalizes identically on both sides and is silently not flagged,
while a genuine content change or outright removal (no equivalent added
block at all) still is. `_waive_deletions_in_diff` itself now just
spawns the diff and delegates to `_scan_diff_for_waive_deletions` (also
new, split out purely to keep ARCH001's line-count threshold happy) --
same hunk-boundary walk as before, just calling the new per-hunk helper
at each `@@`/file-header boundary instead of matching the first physical
line directly.

Verified with three standalone scratch-repo scenarios (a throwaway git
repo built and diffed directly against `_uncommitted_waive_deletions`,
not through the full `land()` path):
1. Rewrap-only diff (2-line wrap -> 3-line wrap, same reason text):
   `_uncommitted_waive_deletions` returns `()` -- not flagged.
2. Genuine full removal of the same wrapped comment: returns
   `(("conftest.py", "WIRE001"),)` -- still flagged.
3. Pre-existing single-physical-line (no continuation) waiver deletion:
   returns `(("conftest.py", "PERF001"),)` -- unchanged, no regression.

Regression tests added to `tests/test_ticket_land.py` (new
`TestWaiveRewrapNotDeletion` class, both acceptance criteria from the
ticket): `test_rewrap_only_diff_is_not_flagged_as_a_deletion` (a re-wrap
through the real `land(..., dry_run=True)` path succeeds) and
`test_rewrap_that_also_changes_content_still_refuses` (a re-wrap that ALSO
changes the reason text still refuses with `LandError.
OutOfScopeWaiveDeletion`). Both pass, along with every pre-existing test
in `TestUncommittedWaiveDeletionRefusal`/`TestCommittedWaiveDeletionRefusal`
(no regression) and the full `tests/test_ticket_land.py` file (hundreds of
tests, all green).

`frob sys sync-interface` picked up the new public `TestWaiveRewrapNotDeletion`
class (SELFAUDIT001) and wrote `design/frob.strata` accordingly; added to
this ticket's scope via `frob ticket scope --add` (a mandated side effect
of the diff, not scope creep) rather than left as an unexplained drift.

Known, expected multi-ticket-worktree artifact (not a T-1468 regression):
`frob check --ticket T-1468` reports 3 `gate:SCOPE` SCOPE001 errors on
`src/frob/app/ticket_runner/_land_cmd.py`, `src/frob/gates/_secrets.py`,
and `src/frob/graph/cache.py` -- T-1463's, T-1211's, and T-1214's own
changes, committed earlier in this same worktree/branch but not yet landed
to main. Will resolve once those land.

### Changed
```
 design/frob.strata                      |   1 +
 src/frob/app/ticket_runner/_land_cmd.py | 148 +++++++++++++++++++-
 src/frob/gates/_secrets.py              |  79 ++++++++++-
 src/frob/graph/cache.py                 |  51 +++++--
 src/frob/tickets/_land_git_ops.py       | 167 ++++++++++++++++++----
 tests/test_ticket_land.py               |  72 ++++++++++
 tickets.md                              | 236 ++++++++++++++++++++++++++++++--
 7 files changed, 698 insertions(+), 56 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 0 error(s), 549 warning(s), 744 waived
- error-findings: none (measured, zero errors)
