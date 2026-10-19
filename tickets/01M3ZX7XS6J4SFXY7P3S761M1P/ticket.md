+++
id = "01M3ZX7XS6J4SFXY7P3S761M1P"
title = "Summary separates plugin-unfinished from undecidable and counts security decisions"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M3ZX76WPYZQ4Q5WDQ72AWMZQ"
reporter = "lognd"
created = "2026-10-03T03:34:36Z"
updated = "2026-10-19T18:01:48Z"
idempotency_key = "m2-sec-summary"
labels = ["milestone:2", "area:security"]
scope = ["crates/gob-diagnostics/src/text.rs", "crates/gob-diagnostics/src/record.rs", "crates/gob-diagnostics/src/lib.rs", "crates/gob-diagnostics/tests/snapshots/*.snap", "docs/design/security.md"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7X3RQTTR7V8JFRN8TQEK"

[[acceptance]]
text = "Given Unresolved from a trapped plugin and from an undecidable call, when summarized, then they are separate lines"
bound = true

[[acceptance]]
text = "Given a grant and a replaces, when summarized, then each appears as a counted security decision"
bound = true
+++

Implements security.md sections 1 (I13) and 2.7 (last bullet).

Trust, grants, replacements, excuses, NotApplicable claims, declarations and overrides are counted in the summary and diffable.
