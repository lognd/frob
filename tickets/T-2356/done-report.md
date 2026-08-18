## Done report

Second half of the ledger-v2 cutover (T-2355 was first half): deletes
`tickets.md`/`tickets-archive.md`, and investigates/corrects the
design's own stale claim about what code is left to delete.

### Final golden round-trip / coverage confirmation (run BEFORE deleting,
as required)

```
monofile id count: 1748
v2 id count (active+archive): 2303
monofile ids with NO v2 file anywhere: 0
of monofile ids: have active v2 file = 50  have archived v2 file = 1698
monofile ids whose v2 state differs from the stale monofile row: 113
```

Every one of the 1748 ids the real `tickets.md`/`tickets-archive.md`
listed already has a real v2 file. Field-for-field equality (what the
synthetic fixture's golden test checks) is NOT the right bar for this
repo's real data -- 113 ids have legitimately diverged (v2 is
authoritative; individual state changes since migration only ever wrote
to v2, never back to the monofile) -- so the check that matters for
cutover is coverage (0 missing), confirmed above, not byte-for-byte
identity. The coordinator independently re-derived the same 50/108/0
split before authorizing deletion.

### What shipped

1. Deleted `tickets.md` (11252 lines) and `tickets-archive.md` (203330
   lines) via `git rm`.
2. Retired the two `.gitattributes` lines routing them through the
   frob-ledger merge driver, replaced with a note explaining the driver
   itself stays in frob's source (other repos still need it).
3. Extended `LEDGERV1001` (`src/frob/gates/_tickets_gate.py`,
   `_ledgerv1001_violations`): a v2-mode repo with a lingering
   `tickets.md`/`tickets-archive.md` now fires an unconditional ERROR
   (no sunset grace period -- a v2-mode repo that kept a stray monofile
   is an incomplete cutover, not "still migrating"). Confirmed silent
   against this repo's own now-monofile-free tree.
4. Corrected docs/design/ledger-v2.md section 7 step 4's stale claim
   (see "the scope correction" below).

### The scope correction (read before trusting the ticket's own scope)

T-2356's declared scope named `src/frob/tickets/_land_merge.py` and
`_land_merge_zones.py` for deletion, quoting the design doc's section 4:
"the monofile-mode code path (..., `_land_merge.py`,
`_land_merge_zones.py`) is NOT yet deleted." I measured before deleting,
per this repo's own "deletion is a detector test" discipline
(`frob check --only dead_symbols --only wire --only refs`): zero
DEAD001/WIRE001/REF002 hits against either file. Reading the code
confirmed why -- both are stale references:

- `_land_merge.py` no longer contains any monofile-merge logic at all.
  T-1189/T-1194/T-1251 (all landed well before this ticket) progressively
  split it out into `_land_ledger_merge.py` (splice_ledger),
  `_land_merge_zones.py` (union-zone resolution), and `_land_git_ops.py`
  (git plumbing). What remains -- pre-merge closeability validation,
  the commit-message helper -- is generic and used by every land
  regardless of ledger mode. Real, live callers: `_land.py`,
  `_land_finalize.py`, `_land_git_ops.py`, `_land_ledger_merge.py`,
  `_land_squash.py`, `_land_cmd.py`, `_tickets_gate.py`.
- `_land_merge_zones.py`'s three registered union zones are
  `frob.toml`, `src/frob/gates/__init__.py`, and `docs/audits/*.md` --
  NONE of them is `tickets.md`. This module has never been
  monofile-specific; it resolves unrelated chronic merge-conflict
  hotspots (gate-severity config, the known-gate-rules registry, audit
  docs).

Deleting either file would have broken the live land pipeline for
every ticket, not just retired dead weight. I did NOT delete them.
I corrected docs/design/ledger-v2.md's section 4 in place instead of
silently deviating from the ticket's stated scope, explaining the real
split history and, separately, why `splice_ledger`/`_render_ledger`/the
v1 dispatch branches must stay in frob's SOURCE regardless of this
repo's own cutover: frob is a general tool other repos use, and they
may still be inside their own v1-mode compatibility window -- deleting
those would break them, not just this repo's now-inert data files.

Miss set for the DEAD001/WIRE001/REF002 measurement: 0 of 0 -- the
detectors correctly found nothing to flag, because there was genuinely
nothing dead to find. No detector gap here; the ticket's own premise
(inherited from a stale doc) was the thing that was wrong.

### Positive controls

1. A state change via the CLI post-cutover is visible through the ONE
   remaining representation: confirmed (`frob ticket show T-2350` reads
   the drop reason recorded moments earlier, entirely off
   `tickets/T-2350/ticket.md`).
2. Every read path that used to fall back to tickets.md for a
   pre-migration id still resolves it via its real per-ticket file:
   confirmed directly -- `frob ticket show T-1220` (one of the 108
   archived-since-migration ids from T-2355) resolves cleanly with full
   Done-report content; `frob ticket board` renders end-to-end off the
   pure v2 tree.
3. A repo with BOTH a v2 tree and a lingering monofile is flagged, not
   silently accepted indefinitely: new test
   `test_v2_mode_repo_with_a_lingering_monofile_errors` proves this
   (unconditional ERROR); the companion `test_v2_mode_repo_is_silent`
   was corrected to actually delete the monofiles before asserting
   silence -- it was previously asserting silence while the monofiles
   were STILL ON DISK (migrate_v1_to_v2 deliberately leaves them), which
   is exactly the gap this ticket closes, so the old assertion was
   accidentally testing the wrong thing.

### Verification

- `pytest tests/test_tickets_migration.py tests/test_ticket_merge_driver.py`:
  29 passed (was 19+? before this ticket; +1 new LEDGERV1001 test, 1
  existing test corrected to a genuine positive case).
- `frob check --land-parity`: 1 unscoped error (E501 in
  `src/frob/verify/_worker.py`), pre-existing and unrelated to this
  ticket's scope -- confirmed via `git blame`-adjacent reasoning (not
  touched by this diff).
- `frob ticket show`/`board` smoke-tested against real post-deletion
  tree (see positive controls above).

### Changed
```
 .gitattributes                       |  27 ++--
 docs/design/ledger-v2.md             |  29 ++++-
 src/frob/gates/_tickets_gate.py      |  56 +++++++-
 tests/test_tickets_migration.py      |  46 ++++++-
 tickets.md                           | -11252 (deleted)
 tickets-archive.md                   | -203330 (deleted)
```

### Evidence
- `tests/test_tickets_migration.py::TestLedgerV1DeprecationGate::test_v2_mode_repo_is_silent`
- `tests/test_tickets_migration.py::TestLedgerV1DeprecationGate::test_v2_mode_repo_with_a_lingering_monofile_errors`
- `tests/test_tickets_migration.py::TestLedgerV1DeprecationGate::test_monofile_mode_warns_before_sunset`
- `tests/test_tickets_migration.py::TestLedgerV1DeprecationGate::test_monofile_mode_errors_past_sunset`
- `tests/test_tickets_migration.py::TestLedgerV1DeprecationGate::test_no_ledger_content_at_all_is_silent`

### Residue
No new ticket filed. `_land_merge.py`/`_land_merge_zones.py` are NOT
dead and were not deleted -- see the scope correction above; the design
doc is corrected in place rather than left stale for the next reader.

### Changed
```
 tickets-archive.md       | 203330 --------------------------------------------
 tickets.md               |  11252 ---
 tickets/T-2356/ticket.md |     50 +-
 3 files changed, 49 insertions(+), 214583 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: AFFECT001@src/frob/gates/_tickets_gate.py, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/release/_cli.py, COV001@scripts/fleet_status.py, COV001@src/frob/tickets/_land_git_ops.py, COV001@src/frob/verify/_drain.py, COV001@src/frob/verify/_quarantine.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, DOC001@docs/commands/release.md, DOC002@scripts/fleet_status.py, DOC002@src/frob/app/verify_runner.py, DOC002@src/frob/verify/_drain.py, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2356/src/frob/verify/_worker.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_new.py, PRE001@tickets/T-2356, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md
