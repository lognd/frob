## Done report

frob-land per tickets.md section 10 and D25/D26/D33: land [handle] [--dry-run] [--push] [--wait] [--keep-worktree] [--no-evidence --reason] [--outcome]; preconditions as refusals (E-LAND-NOT-LEASED, E-LAND-WRONG-WORKTREE, E-LAND-DIRTY, E-LAND-CONFLICT, E-LAND-CHECK-RED via frob_check::run at the ticket scope, evidence guard, E-LAND-LOCKED retryable with --wait bounding acquisition under <common_dir>/frob/land.lock); the base is merged into the ticket branch first so publishing is always a fast-forward (E-LAND-STALE if the base moved); the base advances by git merge --ff-only in the checkout holding it or git update-ref with old-value CAS otherwise, through gob-exec; land and close events on the ledger ref; lease released; worktree and branch removed unless --keep-worktree; optional push to origin (failure is a warning); second land already=true; deterministic dry-run plan with a digest. Deviations: land event written by frob-land via commit_paths pending an EventBody::Land variant; primary checkout drift worked around with git restore of the ledger dir before advancing (gob-git should sync every checkout holding the ref: follow-up ticket); dry run skips the check when the base is unmerged.

### Changed
```
 Cargo.lock                     |  24 ++
 crates/frob-land/Cargo.toml    |  34 ++
 crates/frob-land/src/error.rs  |  96 ++++++
 crates/frob-land/src/events.rs |  90 +++++
 crates/frob-land/src/git.rs    |  59 ++++
 crates/frob-land/src/land.rs   | 767 +++++++++++++++++++++++++++++++++++++++++
 crates/frob-land/src/lib.rs    |  26 ++
 crates/frob-land/src/lock.rs   |  93 +++++
 crates/frob-land/src/plan.rs   | 151 ++++++++
 crates/frob-land/src/verb.rs   | 126 +++++++
 crates/frob-land/tests/land.rs | 436 +++++++++++++++++++++++
 crates/frob/Cargo.toml         |   3 +-
 crates/frob/src/lib.rs         |   5 +-
 docs/reference/cli/frob.md     |   1 +
 tickets/T-0024/ticket.md       |  14 +-
 15 files changed, 1919 insertions(+), 6 deletions(-)
```

### Evidence
(no evidence recorded)
