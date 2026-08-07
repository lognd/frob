## Done report

Investigated the field-described mechanism ("ticket start's background
pre-work sweep loads the ledger, a concurrent frob ticket new writes a new
block, the sweep's completion writes back a stale whole-ledger copy") in
CURRENT source. `frob.gates.sweep_ticket`/`record_prework` (invoked by the
background sweep) never touches `tickets.md` at all -- it persists only to
`.frob/prework/<id>.json`. Every single-ticket ledger writer
(`write_ticket`, used by `transition`/`add_evidence`/`set_done_report`/
`new_ticket`/...) already splices only its own ticket's section under a
freshly re-read, lock-held copy of the ledger text (T-0505), so a
different ticket id's bytes can never travel through it.

The one place this exact bug class (an unlocked `load_all`/`load_archive`
snapshot later replayed into a locked wholesale `write_all`/`write_archive`
call, silently reverting anything written in the gap) IS still live today
is the three wholesale ledger operations: `archive()`, `renumber()`, and
`renumber_one()` (the rename primitive `finalize_draft` uses at land time).
Each of these read the whole ledger BEFORE acquiring `ledger_lock`, and
only locked their own final write -- so a concurrent single-ticket write
landing in that window got silently clobbered the moment the wholesale
write replaced the entire file with the stale pre-lock snapshot. This is
the generalized, currently-reproducible form of the described defect
(scope is `src/frob/tickets/**`, not narrowly "the sweep"), and
`renumber_one` in particular runs during `frob ticket land`'s draft
finalize -- exactly the moment a sibling worktree's own ledger write is
most likely to be in flight, matching the field incidents' timing.

Fix: hold ONE `ledger_lock` span across the entire load-modify-write
sequence in `archive()`, `renumber()`, and `renumber_one()` (the lock is
thread-reentrant, so nesting the existing internal `write_all`/
`write_archive`/`write_ticket` locks inside the new outer span is a safe
no-op re-entry, not a deadlock). This closes the TOCTOU: the load and the
write are now one atomic unit, so no concurrent writer's splice can ever
land in a gap and then be overwritten by a stale wholesale rewrite.

Added `tests/test_tickets_ledger_concurrency.py`:
- `TestArchiveRaceWithConcurrentNew`: `archive()` racing a concurrent
  `new_ticket()` -- both survive, T-0001 moves to archive, the new
  ticket's block stays in the active ledger.
- `TestRenumberOneRaceWithConcurrentNew`: same race through
  `renumber_one()` (the finalize_draft primitive).
- `TestLedgerLockSpansWholesaleOperations`: a direct proof that
  `ledger_lock` genuinely blocks a second acquirer for the full held span,
  not just around one atomic write.

Honest disclosure: I could not reproduce the LITERALLY-described mechanism
(a live write-back from the background sweep subprocess itself) against
current source, because that subprocess's only ledger-adjacent write today
is the per-ticket JSON prework file, which is keyed by ticket id and never
collides across tickets. The fix above targets the actual remaining
lost-update surface in the same module and closes the acceptance
criterion's underlying guarantee (a concurrent `new_ticket` survives a
racing wholesale ledger operation) rather than the literal subprocess path,
which I verified carries no live bug today.

### Changed
```
 src/frob/tickets/__init__.py             | 142 ++++++++++++-------
 tests/test_tickets_ledger_concurrency.py | 232 +++++++++++++++++++++++++++++++
 2 files changed, 322 insertions(+), 52 deletions(-)
```

### Evidence
(no evidence recorded)
