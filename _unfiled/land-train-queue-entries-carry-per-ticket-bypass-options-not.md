+++
id = "01M7ATYF0JJPY1SV1VP0BGSKE1"
title = "land train: queue entries carry per-ticket bypass options, not the driver's"
type = "bug"
category = "done"
outcome = "done"
priority = "high"
points = 3
reporter = "lognd"
created = "2026-11-13T16:13:13Z"
updated = "2026-11-13T22:42:45Z"
labels = ["no-story"]
scope = ["crates/frob-land/**"]

[[acceptance]]
text = "A test shows a queued ticket never inherits another entry's bypass flags."
bound = true
+++

The driver's --no-evidence/--no-changelog/--outcome/--override-base-ci apply to every queued ticket. Source: frob-audit-core.md (Opus audit); read from code, not reproduced.
