## Done report

<!-- frob:waive BUG002 reason="ledger/doc-correction ticket (kind=bug per T-2268 triage default): resolved entirely by two child tickets (T-2355, T-2356) that landed BEFORE this ticket was even filed off main, so no ref in this ticket's own reachable history ever contains the defect unfixed -- there is no base_ref this ticket's own worktree could check repro against. The underlying defect (21 divergent tickets.md rows, 108 miscounted as migration-missing) is real and its evidence (T-2355/T-2356's own MUST-FAIL-THEN-PASS verified fixes, recorded in their own Done reports) already exists; this ticket's evidence cites those tests to prove the resolution holds, not to re-derive a repro this ticket cannot reach." -->

Resolved by its two children landing (T-2355, T-2356), not by direct work
on this ticket -- closing it here records the corrected facts for anyone
who reads this ticket later, since the original filing's own numbers were
wrong in a load-bearing way.

### The corrected facts (read this before the filing text above)

The original filing's "108 tickets exist only in tickets.md with no
per-ticket file" was WRONG. It was measured by checking only
`tickets/T-####/` (the active v2 directory) and never
`tickets/archive/<id>/`. T-2355 (child, done) found this while
implementing the golden round-trip migration: running the corrected
migrator against the real repo wrote 0 files, because all 108 of those
"missing" ids already had a real v2 file -- archived, not active. Direct
verification (all 158 `tickets.md` ids checked against BOTH v2
locations): zero missing anywhere. There was never a 108-ticket
migration gap. `acceptance[1]` above was amended in place to say this
rather than leaving the wrong number to mislead the next reader.

The 21 state divergences (T-1226, T-1664, T-1665, etc., `tickets.md`
saying "still open" while the real per-ticket file said "done"/
"dropped") were never a live desync BUG in the sense of two writers
racing or a merge losing data. Every state-changing write since this
repo's earlier partial v2 adoption went to the per-ticket file only;
`tickets.md` was simply never updated again for those 21 ids, because
`frob ticket migrate --to v2` (the design's own step 2) never ran its
final cutover commit for this repo. It was an ABANDONED compatibility
window, not a corruption -- the per-ticket file was always the correct,
current state; `tickets.md` was a frozen, increasingly stale snapshot
sitting alongside it, exactly matching docs/design/ledger-v2.md section
7's documented (and, until T-2356, undischarged) risk.

### Resolution

- T-2355 (done): built docs/design/ledger-v2.md section 7.3's golden
  round-trip test (checked-in fixture + a required must-fail positive
  control) and `migrate_missing_v2`, confirming -- not assuming -- that
  every id in the monofile already had a real v2 file.
- T-2356 (done): ran the final golden coverage check against the live
  tree one more time (1748 monofile ids, 0 missing a v2 file anywhere:
  50 active + 1698 archived), then deleted `tickets.md`/
  `tickets-archive.md` and the `.gitattributes` merge-driver lines that
  routed them. The 21 divergent rows and the whole "two copies of the
  same fact" hazard this ticket describes are now physically
  impossible -- there is exactly ONE representation left
  (`tickets/<ID>/ticket.md`).
- `LEDGERV1001` (`src/frob/gates/_tickets_gate.py`) was extended by
  T-2356 so this can never silently recur: a v2-mode repo with a
  lingering monofile now fires an unconditional ERROR (not a
  sunset-gated warning) -- acceptance[2]'s "divergence is reported
  rather than passing silently" is satisfied by construction: there is
  no file left to diverge FROM, and if one reappears, the gate catches
  it immediately.

### Acceptance verification

- [0] "given a ticket whose state changed via the CLI, ... they agree
  (or tickets.md no longer exists)": TRUE by the second disjunct --
  tickets.md does not exist (confirmed: `test -f tickets.md` -> absent
  on main as of T-2356's land).
- [1] (amended text): TRUE, confirmed by T-2355's direct measurement
  (0 missing in either v2 location) and re-confirmed by T-2356's final
  golden check before deleting (same result: 0 missing).
- [2]: TRUE -- `test_v2_mode_repo_with_a_lingering_monofile_errors`
  (T-2356) proves a reappeared monofile is reported, not silently
  accepted.

### Changed

No code changed by this ticket directly -- all changes are in T-2355/
T-2356, already landed and cited above.

### Evidence

- `tests/test_tickets_migration.py::TestGoldenFixtureRoundTrip::test_checked_in_fixture_round_trips_to_v2_and_back` (T-2355)
- `tests/test_tickets_migration.py::TestMigrateMissingV2::test_a_stale_active_row_whose_v2_state_already_moved_to_archive_is_not_duplicated` (T-2355)
- `tests/test_tickets_migration.py::TestLedgerV1DeprecationGate::test_v2_mode_repo_with_a_lingering_monofile_errors` (T-2356)

### Changed
```
 tickets/T-2346/done-report.md | 105 ++++++++++++++++++++++++++++++++++++++++++
 tickets/T-2346/ticket.md      |  20 ++++++--
 2 files changed, 120 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/test_tickets_migration.py::TestGoldenFixtureRoundTrip::test_checked_in_fixture_round_trips_to_v2_and_back` (pytest node id, verified passing when recorded)
- `tests/test_tickets_migration.py::TestMigrateMissingV2::test_a_stale_active_row_whose_v2_state_already_moved_to_archive_is_not_duplicated` (pytest node id, verified passing when recorded)
- `tests/test_tickets_migration.py::TestLedgerV1DeprecationGate::test_v2_mode_repo_with_a_lingering_monofile_errors` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@scripts/fleet_status.py, ARCH103@src/frob/release/_cli.py, COV001@scripts/fleet_status.py, COV001@src/frob/tickets/_land_git_ops.py, COV001@src/frob/verify/_drain.py, COV001@src/frob/verify/_quarantine.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, DOC001@docs/commands/release.md, DOC002@scripts/fleet_status.py, DOC002@src/frob/app/verify_runner.py, DOC002@src/frob/verify/_drain.py, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2346/src/frob/verify/_worker.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_new.py, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md

### Acceptance amendments
- [1] replace: 'given the 108 tickets that exist only in tickets.md with no per-ticket file, when the fix is applied, then none of them is lost' -> 'given the 108 tickets whose stale tickets.md row implied no per-ticket file, when checked against BOTH tickets/<id>/ticket.md and tickets/archive/<id>/ticket.md, then all 158 tickets.md ids already have a real v2 file somewhere (T-2355 measured 2026-08-17: zero missing in either location) -- no migration write was needed or made' (reason: T-2355 (child, done) found and fixed the coordinator's own filing error:
"108 tickets exist only in tickets.md with no per-ticket file" was
measured by checking only tickets/T-####/ (active v2 dir) and never
tickets/archive/<id>/. Direct verification against the real repo tree
(all 158 tickets.md ids checked against BOTH v2 locations) found zero
missing a v2 file -- all 108 already had an ARCHIVED v2 file, just not
where the stale monofile row implied. There is no 108-ticket migration
gap; this criterion is corrected to reflect that, rather than left to
silently mislead a future reader.
; logan, 2026-08-17)
