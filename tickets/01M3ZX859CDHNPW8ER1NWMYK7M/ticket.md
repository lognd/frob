+++
id = "01M3ZX859CDHNPW8ER1NWMYK7M"
title = "Privacy: [mirror] exclude, redacted evidence, no worktree paths"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M3ZX77302X3HQF4Z4P7WC0WS"
reporter = "lognd"
created = "2026-10-03T03:34:44Z"
updated = "2026-10-03T03:34:44Z"
idempotency_key = "m2-mirror-privacy"
labels = ["milestone:2", "area:mirror"]
scope = ["crates/frob-mirror/src/privacy.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX832JK52FXBPPCCGTDRTG"

[[acceptance]]
text = "Given an evidence transcript containing a registered secret, when projected, then the secret is redacted"
bound = false

[[acceptance]]
text = "Given a ticket with a held lease, when projected, then no worktree path appears"
bound = false
+++

Implements mirror.md section 3 (privacy and security).

Evidence transcripts are redacted with gob-log before publishing; excluded tickets or fields are never sent; lease worktree paths are never published.
