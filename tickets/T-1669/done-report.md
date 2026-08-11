## Done report

Delivered PROMOTION half of T-1669's design (part 2 of 2 in the ticket
body), scoped narrowly to a single, concrete, demonstrated race: `frob
ticket promote` (finalize_draft) and `frob ticket land`'s own draft
finalization (finalize_draft_for_land) allocated ids from two code paths
that shared NO lock at all. `ledger_lock(root)` only ever serialized
finalize_draft against ITSELF; finalize_draft_for_land deliberately never
takes main's ledger_lock (documented git-tracked-merge collision it
avoids). A concurrent promote and land could therefore compute and commit
the identical next id, each into its own tree (main vs. the landing
worktree) -- neither write itself errors, so the collision only surfaces
later, at squash time, as a forced re-renumber. This reproduces T-2060's
measured incident from today (ids T-2041 and T-2045 each claimed out from
under it).

Root cause found by reading, not guessing: `allocator_lock` (T-1253,
`.frob/tickets-allocator.lock`, a distinct path from `ledger_lock`'s own
`.frob/tickets.lock`) already existed in src/frob/tickets/_store.py,
already reentrant, already tested in isolation
(tests/unit/test_process_lock.py::TestAllocatorLock) -- but had never
actually been wired into any allocator. Fix wires it into both
finalize_draft and finalize_draft_for_land, keyed on the shared main
root, so the two paths now queue instead of colliding.

STOPPED SHORT of touching src/frob/tickets/_land.py (the ticket's original
declared scope included it) because T-2076 holds a live, currently-mid-edit
lease on that exact file (confirmed via `git worktree list` +
`git -C .claude/worktrees/t-2076 status --porcelain`, not stale). The fix
did not need _land.py at all once the real root cause was found, so scope
was narrowed rather than worked around per the playbook's lease rule.

NOT attempted (deliberately out of scope, disclosed rather than silently
dropped):
- The OWNERSHIP half of T-1669 (main must refuse to write a ticket a
  worktree leases) is untouched -- a distinct, separately-sized piece of
  work per the ticket's own two-part split.
- The citation-rewrite gap the brief flagged (`frob ticket renumber`
  rewrites `frob:ticket` directive comments and whole-word prose in
  tickets/**/*.md and code files, but NOT arbitrary docstring prose
  outside that glob, and never commit messages) is real (confirmed by
  reading `_scan_v2_reference_files`'s glob: `tickets_dir(root).rglob(
  "*.md")` only) but is a different mechanism than the allocation race
  and was not touched here.
- A residual, smaller-scope risk noted in the fix's own docstring: if a
  test fixture deliberately tracks `.frob/` in git (T-1006's own edge
  case, NOT true of this repo -- verified `.frob/` is gitignored here),
  a worktree branch could newly commit `.frob/tickets-allocator.lock`
  going forward wherever it did not before, same collision shape
  `_land_lock` already solved via a distinct filename. Not reproduced or
  fixed here; flagged for whoever owns that fixture if it exists.

Filed as follow-up (draft, not yet a real id): the citation-rewrite gap
above and the OWNERSHIP half, if the coordinator wants them tracked
separately from T-1669's own residue.

Verification: `frob check --ticket T-1669` scoped run is 0 errors (25
warnings, pre-existing). `frob check --land-parity` (cache-bypassed,
exact land-sweep evaluation) is clean -- 0 unscoped errors -- after
merging main a second time (a concurrent land, T-2070, fixed an
unrelated pre-existing docs/strata/kernel.md anchor that land-parity
had flagged moments earlier; confirmed via git show main at the earlier
commit that the anchor break predated this ticket's own diff).

### Changed
```
 src/frob/tickets/_draft_finalize.py      |  66 +++++++++++++--
 tests/test_tickets_ledger_concurrency.py | 133 +++++++++++++++++++++++++++++++
 tickets/T-1669/done-report.md            |  72 +++++++++++++++++
 tickets/T-1669/ticket.md                 |  87 ++++++++++++++++++--
 tickets/T-2079/ticket.md       |  47 +++++++++++
 5 files changed, 394 insertions(+), 11 deletions(-)
```

### Evidence
- `tests/test_tickets_ledger_concurrency.py::TestPromoteVsLandFinalizeAllocationRace::test_promote_and_land_finalize_never_allocate_the_same_id` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: none (measured, zero errors)
