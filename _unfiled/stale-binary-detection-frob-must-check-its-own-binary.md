+++
id = "01M7AV6DHZ6KG77GJ74CAT8CDF"
title = "stale-binary detection: frob must check its own binary against the source"
type = "bug"
category = "todo"
priority = "high"
points = 3
reporter = "lognd"
created = "2026-11-13T16:17:34Z"
updated = "2026-11-13T17:11:58Z"
labels = ["no-story"]
scope = ["crates/frob/**"]

[[acceptance]]
text = "A stale binary refuses or warns loudly before reporting findings."
bound = false
+++

H4: closed as done but does not prevent false findings. Source: frob-audit-meta.md (Opus audit).
