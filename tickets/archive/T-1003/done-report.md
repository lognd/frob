## Done report

Churn item 4 (docs/audits/coordination-churn.md#4): every land required
the ritual `git checkout -- uv.lock` on both sides, cd to the ROOT
checkout (the root==worktree guard fired on any chained cd), then the
land command -- the uv.lock half was reduced by T-0789's Makefile target
but the cwd half burned a round-trip whenever an agent forgot it (~15
occurrences).

`land()` (`frob.tickets._land`) now resolves `root` from `worktree`
itself, transparently, whenever they resolve to the identical path:
`git -C <worktree> rev-parse --git-common-dir` (git's own, cwd-
independent answer to "where is this clone's primary checkout") gives
the true root. When that resolves to something OTHER than `worktree` --
a real linked worktree, the common "ran land from inside the worktree"
case -- `root` is redirected there and the land proceeds normally, no
manual cd required. When it resolves back to `worktree` itself (no
linked worktree exists at all, `--worktree` genuinely pointed at the
primary checkout), `root` is left unchanged and the existing T-0795
`_refuse_if_root_is_worktree` guard still refuses exactly as before --
this never weakens that guard, only retires the chained-cd case it used
to also (mis-)catch. `ticket_runner.py`'s `_land` CLI wrapper resolves
the same way (via the same shared `_resolve_primary_checkout` helper)
before calling `land()`, so its own post-land reporting/`--push` steps
stay pointed at the real root too.

`_wip_commit` (the worktree side) now also auto-restores a `uv.lock`
frob-version-only flap before its own dirty check, mirroring the
existing `root`-side restore (`_refuse_if_main_dirty`, T-0793) -- the
same flap shape on the WORKTREE side used to get silently wip-committed
as noise and squash-applied into the landing commit, needing the
identical manual `git checkout -- uv.lock` on that other side too.

`docs/modules/tickets.md#frob-ticket-land` (added to scope, T-0731/
AFFECT001 requires the touch since this ticket directly changed `land`'s
own body) documents the new root-resolution step 0, the amended
wip-commit step 3, and (recording T-1001's already-landed change for
completeness, since it also touches this same section) the stacked-
sibling absorption step 9.8.

### Changed
```
 src/frob/tickets/_land.py | 265 +++++++++++++++++++++++++++++++++++++++++++---
 tests/test_ticket_land.py |  81 ++++++++++++++
 tickets.md                | 112 +++++++++++++++++++-
 3 files changed, 440 insertions(+), 18 deletions(-)
```

### Evidence
- `tests/test_ticket_land.py::TestLandChainedCdRootResolution::test_root_equal_to_a_real_linked_worktree_resolves_and_lands` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLandChainedCdRootResolution::test_root_equal_to_the_primary_checkout_itself_still_refuses` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestUvLockSync::test_worktree_side_lock_flap_auto_restored_before_wip_commit` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestUvLockSync::test_dirty_lock_version_line_only_does_not_refuse` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLandRefusesWhenRootIsWorktree::test_refused_before_any_git_mutation_names_the_real_mistake` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 1 error(s), 4932 warning(s), 322 waived
- error-findings: DOC001@docs/audits/coordination-churn.md
