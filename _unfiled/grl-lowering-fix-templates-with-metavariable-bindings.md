+++
id = "01M4XJ9HCS3WP614D698VN2V5Y"
title = "GRL lowering: fix templates with metavariable bindings"
type = "task"
category = "todo"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-10-14T16:00:28Z"
updated = "2026-10-28T12:55:46Z"
labels = ["no-story"]
scope = ["crates/gob-plan/**"]

[[acceptance]]
text = "a fix template using metavariables lowers with its bindings"
bound = false

[[acceptance]]
text = "the executor renders the fix replacement from the bindings"
bound = false
+++

Follow-up of ~H2V8QVT. Fixes (fix x -> SNIPPET, before/after, delete, host, manual) are dropped by lowering and the plan IR has no fix representation; add one, rendering with gob_pattern::grammar render over Match.bindings.

no-story: internal engineering task in gob-plan; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
