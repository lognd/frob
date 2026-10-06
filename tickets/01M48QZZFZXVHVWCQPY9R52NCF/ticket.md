+++
id = "01M48QZZFZXVHVWCQPY9R52NCF"
title = "Spike: the #[rule] attribute, RuleDef and FileRule on one rule in a scratch crate"
type = "task"
category = "in-progress"
priority = "high"
parent = "01M48QZYWAMKC7MXHQ6AYNV7BN"
reporter = "lognd"
created = "2026-10-06T13:56:03Z"
updated = "2026-10-06T16:15:19Z"
scope = ["crates/gob-macros/**", "crates/gob-rules/**", ".config/nextest.toml"]

[[acceptance]]
text = "deleting the .md, a required section, the fire example or the trait impl, or mistyping a language or capability, each fails to compile with a spanned message"
bound = true

[[acceptance]]
text = "touching the .md rebuilds the rule (include_str tracking verified)"
bound = true

[[acceptance]]
text = "the host-trait versus Supplies<Cx> decision is recorded as a comment on this epic"
bound = true
+++

M0: prove the loop on one TODO001-shaped rule before migrating anything: FileRule generic over a host trait (or the Supplies<Cx> fallback), the colocated .md read by the macro with include_str!, spanned errors. Record the host-trait decision. Design: docs/design/rule-authoring.md (D107); detail and the failure table: notes/research/rule-authoring.md section 4.
