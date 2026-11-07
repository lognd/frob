+++
id = "01M6SJHBH2JK72HAE60AFYDFWX"
title = "grimble-lints design linters: wire portable rules through the universal model"
type = "story"
category = "in-progress"
priority = "high"
points = 8
reporter = "lognd"
created = "2026-11-06T23:19:10Z"
updated = "2026-11-07T00:11:42Z"
scope = ["crates/grimble-lints/src/**", "crates/grimble-lints/Cargo.toml", "crates/grimble-lints/tests/**", "changelog.d/*AFYDFWX*", "Cargo.lock", "creates:docs/design/grimble/lint-classification.md", "creates:changelog.d/01M6SJHBH2JK72HAE60AFYDFWX.changed.md", "docs/design/grimble/lint-classification.md"]

[[acceptance]]
text = "Each lint is classified portable or language-specific in docs; portable families run through U on every adapter language"
bound = false
+++

Audit: about 22 files in crates/grimble-lints/src (effect.rs, path/flow.rs, time/flow.rs, testq/*, res.rs, neat/*, unity*.rs) use tree_sitter nodes directly. Per universal-model.md section 5 and notes/research/lint-requirements.md, rules reading queries U already provides (calls, bindings, flow, effects) should be written once against gob-ir via gob-symbols adapters; language-specific code stays only where U has no query (unity engine idioms). Plan: classify each lint portable vs language-specific; migrate portable ones one family per ticket (effect, path, time, testq, res, neat); add a test asserting each portable rule runs on every adapter language; record cut scope as dropped tickets.
