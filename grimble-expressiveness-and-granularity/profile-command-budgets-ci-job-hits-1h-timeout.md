+++
id = "01M69P2ZY0CQ2Q00FQFC7E9GDH"
title = "profile (command budgets) CI job hits 1h timeout"
type = "bug"
category = "in-progress"
priority = "high"
points = 2
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-10-31T19:13:22Z"
updated = "2026-10-31T19:35:18Z"
idempotency_key = "ci-profile-timeout"
scope = ["crates/gob-dev/**", "docs/design/build-test-ci.md"]

[[acceptance]]
text = "profile job completes within its budget on CI"
bound = true
+++

CI run 41221220516: profile job timed out at 1h after the grimble graph scenario was added; find the slow scenario.
