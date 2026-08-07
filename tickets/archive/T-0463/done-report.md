## Done report

frob ticket land now asserts COMPLETENESS. src/frob/tickets/_land.py:
_worktree_full_changeset() computes the worktree's complete changeset
(tracked edits + untracked new files + deletions); _assert_land_complete()
compares it against what the squash-apply actually staged in root BEFORE the
landing commit, and on any missing file aborts loudly with
Err(LandError.IncompleteLand), fully unwinding the squash (root HEAD +
git status byte-identical -- no partial commit). Wired into
_land_squash_apply() before the commit. LandReport gains worktree_changeset;
docs/modules/tickets.md documents the new step 9.5.

Evidence (2 tests): a worktree with a tracked edit + untracked new file +
deletion lands ALL THREE; a simulated dropped file -> Err(IncompleteLand),
missing path logged, nothing committed. This is the frob fix for the
untracked-file-drop bug that cost docs/modules/render.md AND (discovered
during this land) silently un-tracked the ENTIRE src/frob/render/ package via
a shared .git/info/exclude (T-0465) -- exactly the class this assertion
catches. Coordinator inline-reviewed and landed via 3-way (all tracked).
