+++
id = "01M7ATYETF63DD8V49QW6C7VZ0"
title = "land: hunk-presence refusal leaves bad merge on the ticket branch; retry lands it unchecked"
type = "bug"
category = "in-progress"
priority = "high"
points = 3
reporter = "lognd"
created = "2026-11-13T16:13:13Z"
updated = "2026-11-13T16:46:50Z"
labels = ["no-story"]
scope = ["crates/frob-land/**"]

[[acceptance]]
text = "A regression test shows a refused land, retried, is refused again or the branch is reset."
bound = true
+++

On refusal the merge commit stays on the branch and a second frob land skips the check (crates/frob-land/src/land.rs:214-226). Source: frob-audit-core.md (Opus audit); read from code, not reproduced.
