+++
id = "01M7EXV2AFPR23THT4CA1THKNB"
title = "crunk edit: canonical path confinement"
type = "task"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-15T06:20:45Z"
updated = "2026-11-15T06:20:45Z"
idempotency_key = "crunkplan-ee96a3dff71c"
labels = ["no-story"]

[[acceptance]]
text = "a write through a symlinked dir outside root is refused (test)"
bound = false
+++

Source: ~/projects/frob-audit-grimble-crunk.md, finding L10.
Evidence: lexical confinement lets a symlinked dir escape root
Remedy: canonicalize parent and re-check under canonical root
Crates/files: crates/crunk/src/edit.rs:283-289, serve_patch.rs:84
Verify against HEAD first; the audit ran on a stale binary.
