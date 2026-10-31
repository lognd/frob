+++
id = "01M69QBAKJPZ1V1M9AARQ4HHR5"
title = "frob check: allow skipping tool stages so the profile scenario does not cold-build the workspace"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 3
reporter = "lognd"
created = "2026-10-31T19:35:24Z"
updated = "2026-10-31T20:05:48Z"
scope = ["crates/frob-check/**", "crates/gob-dev/profile.toml", "docs/reference/tool-stages.md"]

[[acceptance]]
text = "1. [ ] frob check can skip [[check.tool]] stages from the CLI. 2. [ ] profile.toml frob check scenario uses it and completes in CI within its budget"
bound = true
+++

found while working C7E9GDH: the profile frob check scenario runs cargo clippy --workspace in a fresh clone (cold, 2 cores), exceeding the 600 s run limit on every CI run since at least 41192078408. C7E9GDH only makes it fail fast.
