---
id: T-1913
title: LAND-PROOF is_ancestor_of_main=False for a non-anchor ticket whose land fully
  succeeded (T-1895)
state: in-progress
kind: bug
origin: human
created: '2026-08-09'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_land_cmd.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
Split from T-1884 (its own "ADDITIONAL MEASUREMENT" block, 2026-08-09,
coordinator). T-1884's original scope (anchor tickets left queued/blocked
on main by design) is fixed and closed. This is the SEPARATE, non-anchor
false-negative the coordinator reproduced on top of it:

`frob ticket land T-1895 --worktree .../t1895-t1893` printed:

  land T-1895: landed as T-1895 at 18b82c8cab4c74d2f5457b738486a129321602e8 (14 file(s) changed)
  land T-1895: REL001 bumped to 0.419.0
  LAND-PROOF: ticket=T-1895 commit=18b82c8... is_ancestor_of_main=False state_on_main=done verified=False

The land had in fact FULLY SUCCEEDED (independently verified: `git
merge-base --is-ancestor 18b82c8... HEAD` -> true; tickets/T-1895/
ticket.md on main reads `state: done`; the actual code change is
present). LAND-PROOF's `is_ancestor_of_main` read False about a commit
that IS an ancestor of main -- a false negative.

INVESTIGATION SO FAR (T-1884 implementer, 2026-08-09). Looked for the
most likely structural cause -- `_land`'s own `root` CLI-local staying
pointed at `--worktree` instead of the resolved primary checkout when
invoked with cwd defaulted inside the worktree (T-1003's own documented
gap: `_resolve_land_root`'s docstring already claimed the CLI wrapper
resolves its own `root` local a second time after `land()` returns, but
no such call site actually existed anywhere in `_land_cmd.py` -- only
`_land_core_prepare`'s internal, non-propagated resolution). Fixed that
real gap (now covered by
`tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish::test_cli_land_invoked_with_root_equal_to_worktree_still_verifies`)
-- BUT could not reproduce the T-1895 shape with it: `git worktree add`
-linked worktrees share ONE common `.git` dir and thus the SAME ref
database, so `git -C <linked-worktree> merge-base --is-ancestor <sha>
main` sees the true, current main tip synchronously regardless of which
worktree the query runs from. Deliberately reverting the root-resolution
fix and re-running the same repro test still passed -- confirming the
"wrong checkout" theory does not explain this shape when the worktree
is a genuine `git worktree add` linked checkout (the normal case per
the agent playbook).

WHAT REMAINS UNEXPLAINED: a genuine timing/visibility race (or some
other mechanism) between the commit landing on `root`'s `main` and the
immediately-following `git merge-base --is-ancestor` query, in the REAL
dispatch environment, that a synchronous in-process pytest fixture does
not reproduce. Possible directions for whoever picks this up: (a)
whether the coordinator's dispatch harness uses something OTHER than a
plain `git worktree add`-linked checkout for `--worktree` (a separate
clone, a bind-mounted filesystem, a network filesystem with write-back
caching) where ref visibility genuinely is not synchronous; (b) whether
`REL001`'s bump step (logged between "landed as ..." and the
LAND-PROOF line) does anything that could leave `report.commit_sha`
pointing at a commit later amended/rebased away rather than the final
tip -- traced `_apply_release_bump`'s callback ordering and it appears
to stage into the SAME pre-final-commit squash, not a later amend, but
this was read, not executed end-to-end under real dispatch conditions;
(c) instrumenting `_print_land_proof`'s own `git merge-base` call with a
retry-with-backoff or a `git update-ref` read-back assertion immediately
after the landing commit, to catch the race directly if it exists.

A regression test for this ticket needs either a real dispatch-shaped
reproduction (not achievable in a synchronous fixture) or a concrete
mechanism, once found, that CAN be reproduced synchronously.
