+++
id = "01M55NRV2ZS88XJ6MKHMWPBB4Z"
title = "crunk-rules: ORG003 literal prefix match and utility-first early return"
type = "bug"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-17T19:35:10Z"
updated = "2026-10-17T19:35:10Z"
idempotency_key = "crunk-cmp-org003"
labels = ["area:crunk"]
scope = ["crates/crunk-rules/**"]

[[acceptance]]
text = "Given file card.css with selector .cardinal, when ORG003 runs, then it fires"
bound = false

[[acceptance]]
text = "Given a utility-first project, when ORG003 runs, then it is silent"
bound = false
+++

Rust ORG003 case-folds and uses starts_with, so cardinal and Card pass for card. Python accepts only name, name__* and name--*, and returns early for utility-first projects.
