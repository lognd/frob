## Done report

Root-caused three distinct write paths in the T-0753 incident class and
closed each with a regression-tested guard:

1. `frob.tickets.archive` (src/frob/tickets/__init__.py) rewrites main's
   whole active ledger without checking whether any OTHER ticket is
   mid-`start` in a sibling worktree; the in-flight worktree's later
   section-10b `git checkout main -- tickets.md` restore then silently
   reverted its own start/evidence/acceptance to queued. `archive` now
   refuses (`Err(ArchiveLiveLeaseExists)`) whenever `read_all_leases`
   reports any live cross-worktree lease, unless `force=True` is passed --
   a stale lease (worktree removed) is correctly ignored, never wedging
   archive forever.

2. `splice_ledger`'s `_newer` tiebreak (src/frob/tickets/_land.py) only
   ever qualified on Done-report presence; an in-flight ticket with
   `start` + recorded evidence + a bound acceptance criterion but NO Done
   report yet, tied in state-rank with a bare reset copy of the same id,
   fell to an arbitrary `b`-wins tiebreak that could discard the richer
   side -- exactly T-0753's shape. Generalized the tiebreak to a full
   richness tuple (Done-report presence, evidence count, bound-acceptance
   count), same priority order, so an existing Done-report-differs case
   decides identically to before. Added `_union_acceptance` (the
   acceptance-binding twin of the existing `_union_evidence`/D-09) so a
   winning side that itself lacks a binding the losing side already had
   inherits it rather than dropping it.

3. Structural guard for the T-0367 markerless-block/id-drop incident
   class: `check_ledger_id_integrity` (src/frob/tickets/_store.py)
   re-parses a rendered ledger and refuses (`Err(LedgerIntegrityViolation)`)
   if any input id fails to round-trip back out with its marker --
   wired into `write_all`, `write_archive`, and `splice_ledger` (which
   also separately refuses if the merge step itself drops an id present
   on either input side, outside an intentional archive-resurrection
   drop).

Deviations / disclosed cuts:
- `frob ticket archive`'s CLI entrypoint (src/frob/app/ticket_runner.py)
  does not yet expose `--force` -- that file is outside this ticket's
  declared scope. Filed T-0810 (finalizes to a sequential id at
  land) for the CLI wiring.
- The acceptance criterion's "markerless block" half is exercised via a
  direct unit-level pin on `check_ledger_id_integrity`
  (`test_render_that_would_drop_an_id_is_refused`, monkeypatching the
  render step to simulate a future regression) rather than a genuinely
  markerless FRESH input side -- a marker-less chunk with no prior
  parseable state carries no id to compare against, so an id-drop cannot
  be detected there at all; this is an information-theoretic limit, not
  a gap left unaddressed. A separate test confirms a malformed (marker
  present, fence broken) side still propagates its `Err` rather than
  being silently treated as empty.
- `scope` was extended by one glob (`tests/test_ticket_land.py`, via
  `frob ticket scope T-0764 --add ... --reason ...`) since
  `tests/test_tickets*.py` does not match that filename; recorded in
  `scope_changes`, not a silent expansion.

Gates: `frob check --ticket T-0764` clean across lint/static/gates-fast/
gates-native/gates-security except REL001 (land-owned, expected under
FROB_AGENT).

### Changed
(no changed files detected)

### Evidence
- `tests/test_tickets.py::TestArchiveRefusesDuringInFlightWork::test_archive_refuses_when_a_live_lease_exists` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestArchiveRefusesDuringInFlightWork::test_archive_force_overrides_the_live_lease_refusal` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestArchiveRefusesDuringInFlightWork::test_archive_ignores_a_stale_lease_from_a_removed_worktree` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestSpliceLedgerPrefersEvidenceRichSideOnRankTie::test_evidence_and_acceptance_rich_side_wins_a_same_rank_reportless_tie` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestSpliceLedgerPrefersEvidenceRichSideOnRankTie::test_acceptance_binding_unioned_even_when_the_reportless_higher_rank_side_wins` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestSpliceLedgerIdDropGuard::test_a_side_only_id_missing_from_theirs_survives_the_splice` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestSpliceLedgerIdDropGuard::test_malformed_side_is_refused_not_silently_treated_as_empty` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestSpliceLedgerIdDropGuard::test_render_that_would_drop_an_id_is_refused` (pytest node id, verified passing when recorded)
