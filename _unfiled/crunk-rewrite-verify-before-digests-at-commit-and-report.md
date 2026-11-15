+++
id = "01M7EXV23A07ESDK8BRNH679QT"
title = "crunk rewrite: verify before-digests at commit and report unreadable dirs"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-15T06:20:45Z"
updated = "2026-11-15T06:20:45Z"
idempotency_key = "crunkplan-06153c5085a6"
labels = ["no-story"]

[[acceptance]]
text = "a file changed mid-rename aborts without overwrite (test)"
bound = false

[[acceptance]]
text = "unreadable dir is reported"
bound = false
+++

Source: ~/projects/frob-audit-grimble-crunk.md, finding L9.
Evidence: rollback overwrites concurrent edits; unreadable dirs hide references
Remedy: digest check before write/rollback; report unreadable dirs
Crates/files: crates/crunk/src/rewrite.rs:405-438,481-500
Verify against HEAD first; the audit ran on a stale binary.
