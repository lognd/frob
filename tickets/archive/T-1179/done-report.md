## Done report

Two independent guards, matching the acceptance criteria and the 2026-07-29
incident (46a115c4 clobbered by 17c6ca89):

Guard 1 (acceptance [0]): new frob.tickets._new_renumber.finalize_draft_for_land
(worktree, draft_id, main_root) replaces plain finalize_draft on the land path
(frob.tickets._land._finalize_draft_id / _finalize_sibling_drafts, threaded
through _land_finalize_and_close / _finalize_and_close_ticket, all now taking
root explicitly). It reads BOTH ledgers fresh from disk (main_root's CURRENT
on-disk copy, not a stale snapshot) and computes the next-id ceiling from
their union, under worktree's own ledger_lock.

Implementation note / honest disclosure: the first version of this also
acquired main_root's OWN ledger_lock (nested, main-first) to make the read
provably atomic against a concurrent new_ticket on main. That version was
REVERTED after it reproduced a real regression: locking main_root creates
main_root/.frob/tickets.lock as an untracked artifact on root's working
tree; on any repo/fixture where .frob/ is not gitignored (the worktree
branch legitimately tracks its OWN .frob/tickets.lock, T-1006), the
subsequent `git merge --squash` from the worktree branch then refuses with
git's own "untracked working tree files would be overwritten by merge"
error, which silently degrades the later ticket-scoped splice (root's
tickets.md never receives the squash's changes, main=0 tickets instead of
main=1) -- caught by tests/test_ticket_land.py::TestWipCommit and
TestWipCommitNormalizationOnlyDirty going red. Reproduced and bisected via
a standalone repro script before landing. The shipped version reads
main_root's ledger WITHOUT holding its lock (same lock footprint as plain
finalize_draft -- only worktree's lock), closing the staleness gap that
caused the incident while leaving zero new regression surface. The narrow
residual race this leaves (no ticket needed -- closed in this same Done
report, not a deferred cut; a new_ticket landing on main in the tiny window
between this unlocked read and the eventual squash-apply) is closed by
Guard 2 below, which runs under a REAL lock at the point that actually
commits to main -- the two guards are deliberately complementary, not each
independently sufficient, matching the ticket's own "defense in depth"
framing (no ticket needed -- Guard 2, in the same Done report, is the
closure, not a deferred cut).

Guard 2 (acceptance [1], defense in depth): _land._overlay_landed_ticket
(split out of _splice_only_ticket to stay under the ARCH001 line budget)
refuses (TicketError.IdTitleMismatch) instead of calling _newer when the
ticket-scoped land-time splice's overlay id already exists on main under a
DIFFERENT title -- the exact shape of the incident: a landing block would
otherwise silently replace an unrelated main-side block sharing the same id.
A same-id/same-title divergence (a genuine same-ticket state advance) still
resolves via _newer exactly as before. This runs inside
_squash_and_splice_ledger's own ledger_lock(root) span, at the point that
actually commits to main -- the atomic backstop Guard 1's unlocked read
cannot itself be.

Reproduced the 2026-07-29 shape directly: a ticket filed on a "main" fixture
after a "worktree" fixture branched off is invisible to finalize_draft's old
worktree-only view (would collide); finalize_draft_for_land's main-fresh
ceiling picks the next free id instead. A companion pair of splice tests
proves the id/title-mismatch refusal and its same-title control case.

Unplanned but necessary fix, filed and disclosed (T-1184, renumbers
at land): _do_wip_commit's `git add -A -- . :!.frob` unconditionally failed
on this environment's git (2.34.1) the moment .frob is actually gitignored
(a real repo, not just a test fixture) -- naming an ignored path in a NEGATED
pathspec still trips git's "explicitly named ignored path" refusal, aborting
the entire add. Reproduced against a clean main checkout with zero
ticket-related changes staged. This blocked EVERY `frob ticket land` in this
environment outright, including this ticket's own land, so it had to be
fixed to complete T-1179's own acceptance -- landing IS how T-1179 exercises
its own fix. Fixed with a detect-and-fallback: try the original exclusion
pathspec first (byte-identical behavior/staging semantics for the T-1006
bare-fixture case that has no .gitignore at all, where the pathspec never
hits the refusal); only on the specific ignored-path refusal, fall back to
staging everything and unstaging .frob as a separate `git reset` step, never
naming an ignored path in a pathspec. Filed T-1184 to track this
fix on its own record.

tests/test_ticket_land.py::TestLandDeeperBranches::test_finalize_draft_failure
needed a one-line update: it now monkeypatches `finalize_draft_for_land`
(the symbol land's own finalize step actually calls) instead of the now-
bypassed `finalize_draft`.

docs/modules/tickets.md's "Provisional ids" section and error-types sample
gained a T-1179 paragraph/entry (including the locking trade-off above);
design/frob.strata was synced (SYS104) for the two new test classes plus the
new finalize_draft_for_land public symbol.

### Changed
```
 tickets.md | 118 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++--
 1 file changed, 115 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/test_tickets_collision.py::TestFinalizeDraftForLandMainFreshCeiling::test_id_ceiling_reads_current_main_not_stale_worktree_view` (pytest node id, verified passing when recorded)
- `tests/test_tickets_collision.py::TestSpliceOnlyTicketIdTitleMismatchRefusal::test_id_title_mismatch_is_refused_not_silently_overwritten` (pytest node id, verified passing when recorded)
- `tests/test_tickets_collision.py::TestSpliceOnlyTicketIdTitleMismatchRefusal::test_same_id_same_title_still_resolves_via_newer` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLandDeeperBranches::test_finalize_draft_failure` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 1 error(s), 931 warning(s), 501 waived
- error-findings: PRE001@tickets/T-1179
