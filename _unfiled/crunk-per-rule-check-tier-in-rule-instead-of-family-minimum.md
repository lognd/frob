+++
id = "01M7EXTZN68562K1PVS87W3EK8"
title = "crunk: per-rule check tier in #[rule] instead of family minimum and T1_RULES"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-15T06:20:42Z"
updated = "2026-11-15T06:20:42Z"
idempotency_key = "crunkplan-c062b6579a93"
labels = ["no-story"]

[[acceptance]]
text = "a rule with tier=T2 is not run at --tier T0"
bound = false

[[acceptance]]
text = "STATE005 tier reflects its measured input"
bound = false
+++

Source: /home/logan/projects/frob-audit-grimble-crunk.md, finding L2.
Evidence: tier is family min plus hard-coded T1_RULES
Remedy: optional tier field on #[rule], falling back to family min
Crates/files: crates/crunk-check/src/tier.rs:117-136, rule macro
Verify against HEAD first; the audit ran on a stale binary.
