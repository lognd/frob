## Done report

Measured the same way the ticket's own coordinator note did: walked all 153
orphaned-lock findings against full git history before touching code. Confirmed
138 never existed anywhere in git (the T-4339 allocate-then-never-write defect,
already fixed at source) and 15 were `T-draft-*` ids promoted to numbered tickets
by design. No real ticket was lost -- the recovery branch needed no work, per the
coordinator's own note.

Fixed `orphaned_ticket_locks` in `src/frob/tickets/_leases.py` with two
DIFFERENT exclusions, matching the two different shapes:

- `T-draft-*` ids are excluded UNCONDITIONALLY by prefix
  (`_ORPHAN_DRAFT_ID_PREFIX`), regardless of age. This is not baseline residue
  of a bug -- it recurs on every future promotion by design -- so a one-time
  baseline would not fix it; it must never be reported at all.
- Every other id is excluded only if its lock file's mtime predates a fixed
  historical constant (`_ORPHAN_LOCK_BASELINE_CUTOVER`, set to the moment this
  ticket measured the backlog). This IS a one-time baseline: T-4339 already
  stopped the defect that produced the 138, so the count can only shrink, and a
  lock created after the cutover reports exactly as before -- verified directly
  against a live fresh-orphan simulation (non-draft id, current mtime) which
  still reports.

Verified BOTH directions, per the ticket's explicit instruction:
- Against the real, live `.frob/tickets/` in the primary checkout:
  `orphaned_ticket_locks(Path("/home/logan/projects/frob"))` now returns `()` --
  zero findings on the healthy tree, the steady state the ticket asked for.
- Against a synthetic fresh non-draft lock (mtime after cutover, no live
  holder): still reports, with the same log line shape as before -- detection is
  not weakened.
- A synthetic `T-draft-*` lock, even with a fresh mtime: silent, confirming the
  unconditional-by-prefix exclusion (not just an age effect).

Also narrowed the WARNING message itself (`warn_orphaned_ticket_locks`), which
previously asserted the T-4313 rollback cause as fact for every finding --
demonstrably false for the draft-id class, which is no longer reported anyway,
but the wording is now stated conditionally ("if the id is unfamiliar") rather
than as an assumed conclusion, so a future finding this design has not
anticipated is not misdiagnosed with false confidence.

Extracted the two-exclusion check into `_is_ticket_lock_baseline_excluded` to
keep `orphaned_ticket_locks` under ARCH001's long-function threshold
(LANDPARITY002 caught this after the first pass).

Residual number on a healthy tree: 0, as the ticket asked. The only way this
count grows again is a genuinely new orphan (post-cutover mtime, non-draft id) --
exactly the T-4313 shape the detector exists to catch.

### Changed
```
 src/frob/tickets/_leases.py | 93 +++++++++++++++++++++++++++++++++++++++++----
 tests/test_ticket_leases.py | 61 +++++++++++++++++++++++++++++
 tickets/T-4348/ticket.md    | 13 +++++++
 3 files changed, 160 insertions(+), 7 deletions(-)
```

### Evidence
- `tests/test_ticket_leases.py::TestOrphanedTicketLocks::test_draft_id_never_reported` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestOrphanedTicketLocks::test_pre_cutover_lock_is_baseline_silent` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestOrphanedTicketLocks::test_post_cutover_lock_still_reports` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestOrphanedTicketLocks::test_lock_gone_ticket_is_orphaned` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestOrphanedTicketLocks::test_live_holder_not_orphaned` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 0 error(s), 4790 warning(s), 959 waived
- error-findings: none (measured, zero errors)
