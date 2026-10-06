+++
id = "01M48R016FCW4AR269QN88H9SY"
title = "The #[rule] attribute and RuleDef: every field required, applies declared, colocated .md"
type = "story"
category = "in-progress"
priority = "high"
parent = "01M48QZYWAMKC7MXHQ6AYNV7BN"
reporter = "lognd"
created = "2026-10-06T13:56:04Z"
updated = "2026-10-06T23:41:58Z"
labels = ["creates:changelog.d/01M48R016FCW4AR269QN88H9SY.*.md"]
scope = ["crates/gob-macros/**", "crates/gob-rules/**", "Cargo.toml", "changelog.d/01M48R016FCW4AR269QN88H9SY.*.md"]

[[links]]
kind = "blocked-by"
target = "01M48QZZFZXVHVWCQPY9R52NCF"

[[links]]
kind = "blocked-by"
target = "01M48R002DA5FKCXDP8HQ6B02X"

[[acceptance]]
text = "one trybuild case per compile-time row of the failure table (metadata, evaluation, applies, unknown language or capability, unsatisfiable need, missing .md or section or example, stem, since)"
bound = true

[[acceptance]]
text = "RuleDef records file and line"
bound = true

[[acceptance]]
text = "the old derive still compiles unchanged and its docs point to #[rule]"
bound = true
+++

M3: the attribute of D107 section 2 with every field required except min_fidelity, family derived, applies checked against gob-caps at compile time, file stem equal to the id, the colocated .md validated at expansion, since and version checked, RuleDef carrying file and line. The old derive keeps compiling, deprecated. Supersedes ~D3ZK8NM. Design: docs/design/rule-authoring.md (D107); detail and the failure table: notes/research/rule-authoring.md section 4.
