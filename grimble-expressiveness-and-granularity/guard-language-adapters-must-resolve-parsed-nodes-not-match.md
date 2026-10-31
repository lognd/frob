+++
id = "01M67VHPB1J3X7KNF3WYJYDBPP"
title = "Guard: language adapters must resolve parsed nodes, not match raw text"
type = "task"
category = "in-progress"
priority = "high"
points = 5
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-10-31T02:10:18Z"
updated = "2026-10-31T02:51:29Z"
idempotency_key = "lexguard-1"
scope = ["crates/gob-symbols/**", "crates/grimble-check/tests/**", "docs/design/universal-model.md"]

[[acceptance]]
text = "A test fails if any per-language capability scanner in gob-symbols decides a capability from raw source text (string or regex search over file contents) instead of tree-sitter nodes plus import and scope resolution."
bound = true

[[acceptance]]
text = "The guard runs over every supported language adapter and is documented; a deliberately lexical adapter fixture makes it fail."
bound = true
+++

Owner: parse each language symbolically; no easily defeatable lexical checks.
