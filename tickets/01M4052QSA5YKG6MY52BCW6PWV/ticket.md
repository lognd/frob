+++
id = "01M4052QSA5YKG6MY52BCW6PWV"
title = "frob-gh: status classification (301, 404, 410) and the token blindness check"
type = "task"
category = "todo"
priority = "high"
points = 3
parent = "01M3ZX77302X3HQF4Z4P7WC0WS"
reporter = "lognd"
created = "2026-10-03T05:51:35Z"
updated = "2026-10-03T05:51:35Z"
idempotency_key = "m2-mirror2-gh-status-blind"
labels = ["milestone:2", "area:mirror"]
scope = ["crates/frob-gh/src/status.rs", "crates/frob-mirror/src/blind.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX8182AHQF2XB4WYNC30Q8"

[[links]]
kind = "blocked-by"
target = "01M3ZX83AB2JADBKWFA9SY4J60"

[[acceptance]]
text = "Given a 404 for an issue, when classified, then the result is not-visible and never deleted"
bound = false

[[acceptance]]
text = "Given a 410, when classified, then the ticket is marked unmirrored and reported and no create is made"
bound = false

[[acceptance]]
text = "Given a 301, when handled, then the cached location changes only after the marker verifies at the new location"
bound = false

[[acceptance]]
text = "Given a token that cannot see the repository or its own recent issues, when the blindness check runs first, then the run stops with MIR001 token-blind and makes no write"
bound = false
+++

Implements mirror.md section 3.3 (Status codes).

301 updates the cached location after the marker is verified at the new location; 404 is never read as deleted (a token that cannot see the issue also gets 404); 410 marks the ticket unmirrored and reports it. A blindness check (the token sees the repository and its own recent issues) runs first; on failure the run stops with MIR001 token-blind.
