## Done report

Root cause: commit_paths synced index and files only in the checkout it ran from, so a ledger commit from a linked worktree left the primary (which has the ref checked out) stale and its next commit_paths refused with E-GIT-LOCAL-EDITS. Fix: after the CAS, every worktree whose branch is the updated ref is synced for exactly the changed paths under its own index.lock with the filter-aware local-edit check; checkouts with genuine local edits are skipped, logged and returned in CommitOutcome.unsynced; the commit is never rolled back. frob-land's git restore workaround (Publish::resync_ledger_dir) removed.

### Changed
```
 crates/frob-land/src/land.rs   |  34 -------------
 crates/gob-git/src/ledger.rs   | 110 +++++++++++++++++++++++++++++++++++++----
 crates/gob-git/src/lib.rs      |   2 +-
 crates/gob-git/tests/ledger.rs |  78 +++++++++++++++++++++++++++++
 tickets/T-0035/ticket.md       |  13 +++--
 5 files changed, 189 insertions(+), 48 deletions(-)
```

### Evidence
(no evidence recorded)
