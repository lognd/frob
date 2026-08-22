## Done report

: T-1136 EPIC ledger v2

Nine children rolled up, all done:

- T-1253: per-ticket lock + allocator lock primitives (`ticket_lock`,
  `allocator_lock`, `src/frob/tickets/_store.py`).
- T-1254: file-per-ticket store backend (ticket.md + done-report.md split,
  T-1587's on-disk-split/in-memory-canonical fix folded in).
- T-1255: renumber via git mv + multi-file reference rewrite, reusing
  T-1125's prose-rewrite engine.
- T-1256: archive via git mv, no content rewrite (T-0959 made structurally
  impossible, not just guarded).
- T-1257: doable/list/show glob + derived index cache + flow mining.
- T-1258: land merge story on native git per-file merge; frob-ledger
  driver retirement designed (actual .gitattributes line removed by
  T-2356, see below).
- T-1259: migration (frob ticket migrate --to v2, golden round-trip
  design, deprecation gate design, T-1553's default-v2 cutover for fresh
  repos).
- T-1669: ledger ownership model (lease-scoped writes + atomic draft
  promotion at land).
- T-2355: built the golden round-trip test
  (tests/fixtures/tickets/golden-monofile-ledger.md +
  golden-monofile-archive.md,
  TestGoldenFixtureRoundTrip::test_checked_in_fixture_round_trips_to_v2_and_back,
  plus its positive control
  test_a_genuinely_divergent_v2_tree_fails_the_equivalence_check) and
  migrate_missing_v2, closing the gap where a partially-migrated repo
  (some tickets v2, some monofile-only) had no repair path. Migrated
  this repo's own 158 monofile ids to v2 (50 active + 108 archived, 0
  missing -- verified by the coordinator).

T-2356 (not a T-1136 child in the ledger's parent field, but the epic's
final dependent step) landed as commit e2ed60480f76189b19157b99c6357a8d
563068e7: deleted tickets.md (-11252 lines) and tickets-archive.md
(-203330 lines), added LEDGERV1001 (gates/_tickets_gate.py) which errors
on a lingering monofile in a v2-mode repo, and removed the
merge=frob-ledger line from .gitattributes. Confirmed directly via
`git show --stat e2ed60480f`.

**Correction absorbed into criterion 1 (amended, reason recorded via
`frob ticket accept --amend`):** the original criterion assumed
_land_merge.py/_land_merge_zones.py would be deleted as monofile-splice
residue. The T-2356 landing agent measured zero DEAD001/WIRE001/REF002
hits against both files and found T-1189/T-1194/T-1251 had already split
the real monofile-merge logic out into _land_ledger_merge.py/
_land_git_ops.py long before this land; what remains in _land_merge.py is
generic land-closeability validation every land depends on, and
_land_merge_zones.py's union zones (frob.toml, gates/__init__.py,
docs/audits/*.md) were never about tickets.md. Deleting either would have
broken the live land pipeline. Neither was deleted; design doc section
4/5 and the ticket's own acceptance criterion were corrected instead to
describe reality.

## Acceptance

- [0] design doc coverage: bound to
  tests/test_tickets_migration.py::TestGoldenFixtureRoundTrip::test_checked_in_fixture_round_trips_to_v2_and_back
- [1] (amended) migration landed, monofiles deleted, LEDGERV1001 gate
  live, _land_merge*.py correctly retained as live generic code: bound
  to tests/test_tickets_migration.py::TestLedgerV1DeprecationGate::test_v2_mode_repo_with_a_lingering_monofile_errors

## Filed

None -- no new residue found; the one correction needed (criterion 1) was
handled via `frob ticket accept --amend`, not a new ticket.

## Cuts

None disclosed as outstanding. Design doc section 8's four open questions
(lock primitive final choice, index rebuild strategy, LEDGERV1001 naming,
attachment path) were each resolved by the implementing children as they
landed -- no longer open.

### Changed
(no changed files detected)

### Evidence
- `tests/test_tickets_migration.py::TestGoldenFixtureRoundTrip::test_checked_in_fixture_round_trips_to_v2_and_back` (pytest node id, verified passing when recorded)
- `tests/test_tickets_migration.py::TestLedgerV1DeprecationGate::test_v2_mode_repo_with_a_lingering_monofile_errors` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@scripts/fleet_status.py, ARCH103@src/frob/release/_cli.py, COV001@scripts/fleet_status.py, COV001@src/frob/tickets/_land_git_ops.py, COV001@src/frob/verify/_drain.py, COV001@src/frob/verify/_quarantine.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, DOC001@docs/commands/release.md, DOC002@scripts/fleet_status.py, DOC002@src/frob/app/verify_runner.py, DOC002@src/frob/verify/_drain.py, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, E501@/home/logan/projects/frob/src/frob/verify/_worker.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_new.py, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md

### Acceptance amendments
- [1] replace: 'GIVEN the migration lands THEN the land path performs no monofile splice, two agents landing disjoint tickets produce no ledger merge conflict, and the TICK002/TICK006 draft-death classes are structurally impossible or auto-repaired' -> 'GIVEN the migration lands THEN tickets.md/tickets-archive.md are deleted, a v2-mode repo with a lingering monofile errors (LEDGERV1001), two agents landing disjoint tickets produce no ledger merge conflict, and the TICK002/TICK006 draft-death classes are structurally impossible or auto-repaired -- while _land_merge.py/_land_merge_zones.py correctly remain as live generic land-closeability/union-zone code, not monofile-splice residue (design section 5 corrected accordingly)' (reason: Verified against commit e2ed60480f76189b19157b99c6357a8d563068e7 (T-2356 land):
tickets.md (-11252 lines) and tickets-archive.md (-203330 lines) are both
deleted. gates/_tickets_gate.py gained LEDGERV1001 (errors on a lingering
monofile in a v2-mode repo). The migration is landed and the compatibility
window is closed.

The original criterion assumed _land_merge.py/_land_merge_zones.py would be
deleted as monofile-splice residue -- design section 5's stale text. The
landing agent (T-2356) measured zero DEAD001/WIRE001/REF002 hits against
both files and confirmed by reading the code that T-1189/T-1194/T-1251 had
already split the real monofile-merge logic out into
_land_ledger_merge.py/_land_git_ops.py long ago; what remains in
_land_merge.py is generic closeability validation every land depends on,
and _land_merge_zones.py's union zones (frob.toml, gates/__init__.py,
docs/audits/*.md) were never about tickets.md at all. Deleting either would
have broken the live land pipeline. Neither was deleted; design section 4/5
was corrected instead (see the same commit's docs/design/ledger-v2.md diff).
Amending the criterion to match the corrected design rather than the
now-known-stale original text.
; logan, 2026-08-17)
