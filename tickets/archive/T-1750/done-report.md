## Done report

Addressed all three defects the ticket named, adjusted where the fix
conflicted with existing, correct test coverage.

1. ARCHIVE DOES NOT ENFORCE ITS OWN PRECONDITION -- fixed for the v1
   monofile path (`src/frob/tickets/_archive.py::archive`): a new guard,
   `_refuse_archive_if_other_worktrees_live`, refuses (reusing
   `TicketError.ArchiveLiveLeaseExists`, no new error variant needed)
   whenever `git worktree list` (via `frob.tickets._reconcile.
   _live_worktrees`, reused not reimplemented) shows any linked worktree
   besides the primary checkout, naming every one found; `--force`
   overrides. Deliberately NOT added to `archive_v2` (see item 2) --
   `_write_archived_and_active`'s docstring/comment explains why the two
   paths get different treatment.

2. THE MERGE DRIVER DOES NOT UNDERSTAND AN ACTIVE->ARCHIVE MOVE --
   investigated, not re-fixed: v2's `archive_v2` (design section 4.3)
   already does `git mv tickets/T-#### tickets/archive/T-####` per
   ticket, a real git rename between two disjoint paths that a
   concurrent worktree's plain `git merge` resolves correctly with NO
   custom splice code -- structurally impossible for the v1 duplicate-id
   class to recur there (verified against the existing regression test,
   `TestArchiveV2.test_archive_v2_regression_two_sided_divergence_no_
   clobber`, which already reproduces the exact two-sided-divergence
   shape unforced with a live sibling worktree throughout, and passes).
   The actual 2026-08-07 incident happened via the v1 monofile path
   (`tickets.md`/`tickets-archive.md`), which is where item 1's guard
   now applies; `splice_ledger`'s existing `archived_ids`-based
   resurrection-drop (T-1437) is the pre-existing v1-path mitigation,
   confirmed still working via `TestArchiveResurrection.test_archived_
   id_never_resurrected` and `TestArchiveSpliceDiscipline.test_land_
   preserves_mains_newly_archived_blocks_over_a_stale_worktree_archive`
   (both re-run and passing).

3. TICK003 FORCES A QUIET-WINDOW OPERATION AT A NON-QUIET MOMENT --
   `_TICK003_DEFAULT_WARN`/`_TICK003_DEFAULT_ERROR` moved from (20, 60)
   to (10, 400): WARN fires earlier (housekeeping visible/schedulable
   well before urgent), ERROR moves far above anything a real drive
   organically reaches, so TICK003 can no longer itself force an unsafe
   `frob ticket archive` call mid-drive. The hard ERROR tier is kept as
   an absolute backstop, not removed.

`docs/modules/tickets.md` gained a new "Archive: the live-worktree
guard (T-1750)" subsection documenting all three points and why v2 is
exempt from item 1's guard.

Regression coverage: added `TestArchiveRefusesLiveWorktrees` (3 tests,
`tests/test_tickets_organization.py`) covering refuse/force/clean-path
for the new guard, matching the ticket's own demand for "a worktree
branched BEFORE an archive pass, merging main AFTER it" shape (the two
pre-existing v2 tests in `tests/test_ticket_land.py` already cover that
exact shape for the v2 path and were re-verified passing).

Scope was widened twice via `frob ticket scope --add` (never silently):
- `tests/test_gates_tickets_hygiene.py`: item 3's threshold change
  broke two tests hardcoding the old (20, 60) defaults (21/61 closed
  tickets); updated to the new (10, 400) defaults (11/401).
- `tests/test_ticket_land.py`: item 1's new guard broke two pre-existing
  splice-discipline regression tests (`TestArchiveSpliceDiscipline`,
  `TestArchiveResurrection`) that deliberately call `archive()` with a
  live sibling worktree present to prove splice correctness -- added
  `force=True` to the three affected calls (each keeps testing splice
  correctness, which is what these tests actually check, not the new
  precondition).

Found beyond the ticket's own text: `tests/test_ticket_runner_archive_
force.py::TestTicketArchiveForceCLI::test_force_overrides_the_live_
lease_refusal` fails on a completely clean `main` (confirmed: `git diff
main` on both that file and `src/frob/app/ticket_runner/_archive.py`
is empty) -- a pre-existing bug where T-1762's `--reason` requirement on
`--force` was never accounted for in this older (T-0810-era) test. Filed
T-1785 rather than fixing it here (out of this ticket's
scope, and unrelated to any of the three defects T-1750 names).

Not done: root cause underneath (the general "when is it safe to run a
long-blocking housekeeping op" pattern) is not generalized beyond
archive/TICK003 -- out of scope, not asked for.

### Changed
```
 tickets/T-1750/ticket.md           | 30 +++++++++++++++++++++++++++++-
 tickets/T-1785/ticket.md | 22 ++++++++++++++++++++++
 2 files changed, 51 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_tickets_organization.py::TestArchiveRefusesLiveWorktrees::test_refuses_when_another_worktree_exists` (pytest node id, verified passing when recorded)
- `tests/test_tickets_organization.py::TestArchiveRefusesLiveWorktrees::test_force_overrides_the_live_worktree_refusal` (pytest node id, verified passing when recorded)
- `tests/test_tickets_organization.py::TestArchiveRefusesLiveWorktrees::test_no_other_worktree_archives_normally` (pytest node id, verified passing when recorded)
- `tests/test_gates_tickets_hygiene.py::TestTick003StaleArchive::test_above_default_warn_threshold_warns` (pytest node id, verified passing when recorded)
- `tests/test_gates_tickets_hygiene.py::TestTick003StaleArchive::test_above_default_error_threshold_errors` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestArchiveResurrection::test_archived_id_never_resurrected` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestArchiveSpliceDiscipline::test_land_preserves_mains_newly_archived_blocks_over_a_stale_worktree_archive` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: 3 error(s), 1129 warning(s), 721 waived
- error-findings: AFFECT001@src/frob/tickets/_archive.py, ARCH001@src/frob/tickets/_archive.py, PRE001@tickets/T-1750
