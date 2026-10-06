+++
id = "01M48PC2ZS196NARNAWT7EH2BG"
title = "Diagnostic message convention test over the registry and snapshots"
type = "story"
category = "todo"
priority = "low"
parent = "01M47QTS14TAZQ67NN2M9NHDJP"
reporter = "lognd"
created = "2026-10-06T13:27:42Z"
updated = "2026-10-06T13:41:10Z"
scope = ["crates/gob-rules/**", "crates/gob-diagnostics/**"]

[[acceptance]]
text = "the test scans registry messages and snapshots"
bound = false

[[acceptance]]
text = "an offending message fails naming the rule"
bound = false

[[acceptance]]
text = "Unresolved messages follow their own convention and each Unresolved snapshot has a reason and a remedy line"
bound = false
+++

Port clippy's lint-message convention test: every rule message and rendered finding starts lower-case and has no trailing period (or whatever docs/design/diagnostics.md states), with a shrink-only allowlist. Source: notes/research/rule-testing.md (D103).
