---
id: T-1331
title: Pre-existing tests/test_ticket_land.py .frob/ leakage into git add -A causes
  IncompleteLand/merge-conflict failures
state: done
kind: bug
origin: human
created: '2026-07-29'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_ticket_land.py::TestFrobDirNeverLeaksIntoGitAdd::test_frob_scratch_files_are_gitignored_not_tracked
- tests/test_ticket_land.py::TestFrobDirNeverLeaksIntoGitAdd::test_two_branches_with_divergent_frob_scratch_never_add_add_conflict
- tests/test_ticket_land.py::TestArchiveV2::test_archive_v2_regression_two_sided_divergence_no_clobber
designated_repro_test: null
threat: null
component: null
---
Confirmed on main HEAD (bbacb65d, prior to T-1258's own changes -- verified
in an isolated scratch clone, unrelated to any worktree agent's changes):
at least 4 existing tests in tests/test_ticket_land.py fail with
LandError.IncompleteLand or a raw `.frob/tickets-index.json`/
`.frob/tickets-archive-cache.json` merge conflict:

- TestArchiveResurrection::test_archived_id_never_resurrected
- TestArchiveSpliceDiscipline::test_land_preserves_mains_newly_archived_blocks_over_a_stale_worktree_archive
- TestArchiveSpliceDiscipline::test_land_takes_mains_content_edit_over_a_worktree_copy_unchanged_since_branch
- TestClaimDivergencePostMerge::test_unmeasured_fresh_check_skips_gate_reverification_land_proceeds
- TestArchiveV2::test_archive_v2_regression_two_sided_divergence_no_clobber

Root cause (from the captured IncompleteLand message): the worktree's
`_commit_all`-style blanket `git add -A` in these fixtures commits `.frob/`
scratch state (cache.db, derived.lock, prework/*.json, the T-1257 v2 index
cache / archive cache files) as TRACKED files, because these fixture repos
never write a `.gitignore` for `.frob/`. Land's T-0463 completeness
assertion then correctly flags the root checkout as missing those files
after the squash-apply (or, in the raw-git-merge case, git itself hits an
add/add conflict on `.frob/tickets-index.json`). This looks like recently
introduced `.frob/` scratch artifacts (T-1257's v2 index/archive cache
files in particular) tipped previously-marginal fixtures over into a real
failure -- these fixtures likely worked before those files existed.

Fix: either (a) have every `tests/test_ticket_land.py` fixture repo write
a `.gitignore` with `.frob/` at init (mirrors what T-1258 had to add to
its own new `v2_repo` fixture to avoid the identical class of failure), or
(b) make the frob-internal `git add -A` call sites (`_wip_commit`, land's
finalize-commit step) exclude `.frob/` explicitly regardless of the
target repo's own `.gitignore`. Filed by T-1258 (ledger v2 land merge
story) -- out of that ticket's own scope (pre-existing failure, unrelated
to its diff, confirmed via a clean main-HEAD scratch clone).