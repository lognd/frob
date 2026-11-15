+++
id = "01M7EXV0FA756MNWT91C4GW0DV"
title = "crunk triage: per-request total deadline"
type = "task"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-15T06:20:43Z"
updated = "2026-11-15T06:20:43Z"
idempotency_key = "crunkplan-93812eb31043"
labels = ["no-story"]

[[acceptance]]
text = "a client trickling bytes is dropped after the deadline (test)"
bound = false
+++

Source: ~/projects/frob-audit-grimble-crunk.md, finding L7.
Evidence: slow client holds the single-threaded accept loop
Remedy: check an Instant deadline between reads
Crates/files: crates/crunk-gallery/src/triage/server.rs:230-270,330-341
Verify against HEAD first; the audit ran on a stale binary.
