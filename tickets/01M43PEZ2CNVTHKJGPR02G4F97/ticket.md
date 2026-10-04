+++
id = "01M43PEZ2CNVTHKJGPR02G4F97"
title = "One comment discovery: frob-obligations duplicates gob-directives comment scanning"
type = "chore"
category = "in-progress"
priority = "medium"
reporter = "lognd"
created = "2026-10-04T14:53:04Z"
updated = "2026-10-04T22:43:49Z"
scope = ["crates/gob-languages/src/comments.rs", "crates/gob-languages/src/lib.rs", "crates/gob-languages/src/grmb.rs", "crates/gob-languages/tests/corpus/*", "crates/gob-directives/src/comments.rs", "crates/gob-directives/Cargo.toml", "crates/frob-obligations/src/comments.rs", "Cargo.lock"]

[[acceptance]]
text = "Given the workspace, when searched, then comment discovery per language exists in exactly one crate"
bound = true

[[acceptance]]
text = "Given a shared corpus with strings, front matter and fenced code, when both consumers scan it, then they see identical comment spans"
bound = false
+++

crates/frob-obligations/src/comments.rs duplicates the per-language comment discovery in crates/gob-directives/src/comments.rs (the string-blind hash scanner existed in both until ~41MBK6Q, and front-matter handling from ~JTV288R exists only in gob-directives). Two scanners for one question means every comment-lexing fix has to be made twice and drifts. Make gob-directives (or gob-languages) the single owner of comment discovery per language, have frob-obligations consume it, delete the copy, and add a test that both consumers see identical comment spans on a shared corpus.
