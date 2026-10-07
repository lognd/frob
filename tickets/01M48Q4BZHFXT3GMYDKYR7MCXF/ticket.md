+++
id = "01M48Q4BZHFXT3GMYDKYR7MCXF"
title = "gob-rules: typed Unresolved reason on Finding and a RuleReport with subject accounting"
type = "story"
category = "in-progress"
priority = "high"
parent = "01M48Q4BE7FBVXDVYH59ZVPK66"
reporter = "lognd"
created = "2026-10-06T13:40:58Z"
updated = "2026-10-07T16:20:13Z"
scope = ["crates/gob-rules/**", "crates/gob-ir/**", "crates/gob-check/**", "crates/grimble-bind/**", "crates/gob-diagnostics/**", "crates/grimble-check/**", "crates/frob-check/tests/check.rs", "crates/gob-mdtest/**", "docs/schemas/**"]

[[acceptance]]
text = "no production code parses a reason out of a message"
bound = false

[[acceptance]]
text = "the JSON schema shows reason (snapshot)"
bound = false

[[acceptance]]
text = "the mdtest Runner can return RuleReport"
bound = false
+++

Finding has no reason and no subjects_examined although universal-model.md 8 says it does; reason codes live in message text and five separate reason enums. Add Finding.reason (typed: the UM 4.6 table plus opaque, hole, edge-may, edge-unknown, vacuous, fidelity, parse-failed, partial) and RuleReport {rule, subjects_total, subjects_examined, not_applicable, findings}; gob-ir RuleOutcome and gob-check subject counters convert into it; migrate gob-ir eval, gob-check status/required and grimble-bind; delete message-prefix parsing. Design: docs/design/testing.md (D106); audit: notes/research/u-testing-audit.md.
