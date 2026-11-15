+++
id = "01M7EXSGN2MYM30HZM33YNR89E"
title = "crunk: unreadable or unsolvable scene files are Unresolved, not dropped"
type = "task"
category = "todo"
priority = "medium"
points = 2
parent = "01M7ETKAPM2000N80NA0W5NAM5"
reporter = "lognd"
created = "2026-11-15T06:19:54Z"
updated = "2026-11-15T06:19:58Z"
idempotency_key = "crunkplan-5e146141b39d"
labels = ["no-story"]

[[links]]
kind = "blocked-by"
target = "01M7EXSFWBE6NF7KTA3R2C2421"

[[acceptance]]
text = "a scene with a trailing comma yields an Unresolved finding for LAYOUT003-005"
bound = false

[[acceptance]]
text = "the check does not pass green"
bound = false
+++

Source: ~/projects/frob-audit-grimble-crunk.md, finding M2.
Evidence: parse_scene/solve_scene errors become warn! and skip; all-failed reports inapplicable
Remedy: count bad files as subjects and emit a file-level Unresolved per geometry rule
Crates/files: crates/crunk-rules/src/scene_files.rs:80-110, host.rs:136-152
Verify against HEAD first; the audit ran on a stale binary.
