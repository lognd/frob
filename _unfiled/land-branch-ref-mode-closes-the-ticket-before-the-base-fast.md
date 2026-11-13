+++
id = "01M7ATYEXWQEBT3NPC65JBQCNJ"
title = "land: branch ref mode closes the ticket before the base fast-forward; failed FF reads as already-done"
type = "bug"
category = "done"
outcome = "done"
priority = "high"
points = 3
reporter = "lognd"
created = "2026-11-13T16:13:13Z"
updated = "2026-11-13T21:47:45Z"
labels = ["no-story"]
scope = ["crates/frob-land/**"]

[[acceptance]]
text = "A regression test shows a failed fast-forward is reported as a failure, not an already-done no-op."
bound = true
+++

settled_by_a_racing_land treats a closed ticket as landed so code may never reach the base. Source: frob-audit-core.md (Opus audit); read from code, not reproduced.
