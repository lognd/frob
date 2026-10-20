+++
id = "01M48R07AYMKWPKZDXW4BKKSMH"
title = "Plugin parity: one RuleDef for Rust, GRL std and pack rules; GRL reads, since and fidelity headers"
type = "story"
category = "todo"
priority = "medium"
parent = "01M48QZYWAMKC7MXHQ6AYNV7BN"
reporter = "lognd"
created = "2026-10-06T13:56:11Z"
updated = "2026-10-06T13:56:11Z"
scope = ["crates/gob-rules/**", "crates/gob-plan/**", "docs/design/grl-spec.md"]

[[links]]
kind = "blocked-by"
target = "01M48R029HFBJ3PKQX5GBBKJ6V"

[[acceptance]]
text = "rules list --json has the same fields for a Rust std rule, a GRL std rule and a pack rule"
bound = false

[[acceptance]]
text = "GRL accepts reads, since and fidelity"
bound = false
+++

M12: Registry::of merges product lists and loaded packs; GRL renames needs to reads and gains optional since and fidelity. Design: docs/design/rule-authoring.md (D107); detail and the failure table: notes/research/rule-authoring.md section 4.
