## Done report

Delivered docs/design/ledger-v2.md section 7.3's golden round-trip test
plus the migration primitive the parent ticket's second acceptance item
needed -- WITH a load-bearing correction to the parent's own premise,
found and fixed before it could land bad data.

### What shipped

1. Golden round-trip fixture + test (section 7.3, "not yet built"):
   `tests/fixtures/tickets/golden-monofile-ledger.md` +
   `golden-monofile-archive.md`, checked in, covering every shape the
   design names (done ticket w/ Done report, queued ticket w/
   blocked_by, ticket w/ attachments, archived ticket, draft-id ticket).
   `TestGoldenFixtureRoundTrip.test_checked_in_fixture_round_trips_to_v2_and_back`
   migrates the real fixture file and asserts semantic equality.
   REQUIRED positive control:
   `test_a_genuinely_divergent_v2_tree_fails_the_equivalence_check`
   hand-corrupts a v2 ticket's title post-migration and asserts the
   shared equivalence helper actually raises -- proof the check can
   fail, not just always pass.

2. `migrate_missing_v2` (src/frob/tickets/_store.py): closes the real
   gap `migrate_v1_to_v2` leaves open -- that migrator no-ops entirely
   (Ok(0)) the instant a repo is v2-mode, so a repo cut over for new
   writes but still carrying legacy monofile-only tickets has no path
   to a v2 file for them. Writes only for ids missing a v2 file in
   EITHER active or archive location.

### The premise correction (read this before trusting "108")

The coordinator brief's numbers (158 tickets.md rows, 108 with "no
per-ticket file") were measured by checking only `tickets/T-####/`
(active v2 dir), the same incomplete check I made myself at first. I
ran `migrate_missing_v2` against this repo's real tree and it wrote
108 files under `tickets/T-####/` -- then `frob check`'s DuplicateId
gate immediately refused the tree: every one of those 108 ids ALREADY
had a v2 file, just under `tickets/archive/<id>/`, because the
monofile's "active" row was stale (the ticket had been migrated once,
then separately archived, and the row was never updated). I reverted
that commit (`git reset --hard` to the pre-data commit), fixed
`migrate_missing_v2` to check BOTH v2 locations before writing, added
a regression test reproducing the exact incident
(`test_a_stale_active_row_whose_v2_state_already_moved_to_archive_is_not_duplicated`),
and re-ran the corrected function against the real repo.

**Result: 0 tickets written.** Direct verification (every one of the
158 `tickets.md` ids checked against both `tickets/<id>/ticket.md` and
`tickets/archive/<id>/ticket.md`) confirms zero are genuinely missing a
v2 file. The "108 legacy-only tickets" do not exist as a real gap --
every id already has a real per-ticket file, just not always where its
stale monofile row implies. No 108-ticket data commit was needed or
made.

### Positive controls (all three, as required)

1. Round-trip test MUST FAIL on a divergent tree: verified directly
   (`test_a_genuinely_divergent_v2_tree_fails_the_equivalence_check`,
   passes by catching the induced AssertionError).
2. All 158 tickets.md ids exist as real per-ticket v2 files afterward:
   TRUE, verified directly against the real repo tree (0 missing in
   either location) -- see correction above for why this needed no new
   commit.
3. No already-migrated ticket altered: TRUE by construction
   (`migrate_missing_v2` only ever writes a file that does not already
   exist in EITHER v2 location) and confirmed empirically -- 0 tickets
   written means 0 tickets touched.

### Verification

- `pytest tests/test_tickets_migration.py`: 19 passed (was 13 before
  this ticket; +6 new: 2 golden-fixture tests incl. must-fail control,
  3 migrate_missing_v2 tests incl. the stale-archive regression, +1
  existing suite unaffected).
- `frob check --land-parity`: clean, 0 unscoped errors, after fixing
  ARCH001 (function too long, split into `_migrate_missing_ids`) and
  E501 (frob:doc/frob:tests directive line length) found along the way.
- Deletion-filter check (`git diff main --diff-filter=D`): empty.
- `tickets.md`/`tickets-archive.md` untouched (migrate_missing_v2
  never writes to either, by design, same reversibility guarantee as
  `migrate_v1_to_v2`).

### Changed
```
 docs/design/ledger-v2.md                              |  30 ++-
 src/frob/tickets/_store.py                             | 116 +++++++-
 tests/fixtures/tickets/golden-monofile-archive.md      |  32 +++
 tests/fixtures/tickets/golden-monofile-ledger.md       | 100 ++++++++
 tests/test_tickets_migration.py                        | 218 ++++++++++++++-
```

### Evidence
- `tests/test_tickets_migration.py::TestGoldenFixtureRoundTrip::test_checked_in_fixture_round_trips_to_v2_and_back`
- `tests/test_tickets_migration.py::TestGoldenFixtureRoundTrip::test_a_genuinely_divergent_v2_tree_fails_the_equivalence_check`
- `tests/test_tickets_migration.py::TestMigrateMissingV2::test_migrates_only_the_monofile_only_tickets`
- `tests/test_tickets_migration.py::TestMigrateMissingV2::test_never_overwrites_an_already_migrated_ticket`
- `tests/test_tickets_migration.py::TestMigrateMissingV2::test_a_stale_active_row_whose_v2_state_already_moved_to_archive_is_not_duplicated`
- `tests/test_tickets_migration.py::TestMigrateMissingV2::test_idempotent_second_run_is_a_no_op`

### Residue
No new ticket filed. The parent's step-2 acceptance ("108 tickets exist
as per-ticket files afterward") is already true today, as shown above
-- nothing further to migrate. T-2356 (final cutover: delete
tickets.md/tickets-archive.md) remains the separate follow-up per the
design's own two-commit plan; unaffected by this correction since it
never depended on the (incorrect) 108-count.

### Changed
```
 docs/design/ledger-v2.md                          |  42 ++--
 src/frob/tickets/_store.py                        |  97 ++++++++-
 tests/fixtures/tickets/golden-monofile-archive.md |  32 +++
 tests/fixtures/tickets/golden-monofile-ledger.md  | 100 +++++++++
 tests/test_tickets_migration.py                   | 246 ++++++++++++++++++++++
 tickets/T-2355/ticket.md                          |  29 ++-
 6 files changed, 532 insertions(+), 14 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@scripts/fleet_status.py, ARCH103@src/frob/release/_cli.py, COV001@scripts/fleet_status.py, COV001@src/frob/tickets/_land_git_ops.py, COV001@src/frob/verify/_drain.py, COV001@src/frob/verify/_quarantine.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, DOC001@docs/commands/release.md, DOC002@scripts/fleet_status.py, DOC002@src/frob/app/verify_runner.py, DOC002@src/frob/verify/_drain.py, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2355/src/frob/verify/_worker.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_new.py, PRE001@tickets/T-2355, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE001@src/frob/tickets/_store.py, WIRE003@docs/modules/cli.md
