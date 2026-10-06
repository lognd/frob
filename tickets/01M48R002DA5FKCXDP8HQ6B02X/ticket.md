+++
id = "01M48R002DA5FKCXDP8HQ6B02X"
title = "gob-caps leaf crate: Lang, Fidelity, Capability, Precision and the const capability matrix"
type = "story"
category = "in-progress"
priority = "high"
parent = "01M48QZYWAMKC7MXHQ6AYNV7BN"
reporter = "lognd"
created = "2026-10-06T13:56:03Z"
updated = "2026-10-06T16:43:32Z"
labels = ["creates:crates/gob-caps/**"]
scope = ["crates/gob-caps/**", "crates/gob-symbols/**", "crates/gob-languages/**", "crates/grimble-model/**", "Cargo.lock", "crates/gob-rules/**"]

[[links]]
kind = "blocked-by"
target = "01M48QZZFZXVHVWCQPY9R52NCF"

[[acceptance]]
text = "docs/reference/languages.md is byte-identical (GEN001 clean)"
bound = false

[[acceptance]]
text = "a test asserts each adapter's capabilities equal its const row"
bound = false

[[acceptance]]
text = "one Lang mapping function is tested over all three vocabularies"
bound = false
+++

M1: one source for languages and capabilities: a closed Lang enum (with opaque-text and binary rows), Capability (plus Comments, Style, Markup), Precision and a const MATRIX; every adapter's capabilities() reads its row; one mapping from gob-languages Language, LanguageHint and adapter tags to Lang. Design: docs/design/rule-authoring.md (D107); detail and the failure table: notes/research/rule-authoring.md section 4.
