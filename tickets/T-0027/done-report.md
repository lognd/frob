## Done report

Root cause: gix shares one index snapshot across Repository clones and refreshes it by the index file's mtime alone, so two index writes inside one mtime tick left status() and the LocalEdits check reading a stale index. Fix: status(), index_map() and check_local_edits open a fresh gix handle (Repo::fresh_gix) with its own index cache. Test assertions unchanged; 30 consecutive passes in the worktree.

### Changed
```
 crates/gob-git/src/ledger.rs |  2 +-
 crates/gob-git/src/read.rs   | 10 ++++++++++
 crates/gob-git/src/status.rs |  6 +++---
 tickets/T-0027/ticket.md     |  6 +++---
 4 files changed, 17 insertions(+), 7 deletions(-)
```

### Evidence
(no evidence recorded)
