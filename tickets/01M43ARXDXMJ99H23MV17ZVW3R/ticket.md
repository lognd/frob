+++
id = "01M43ARXDXMJ99H23MV17ZVW3R"
title = "gob-languages: TS, TSX and CSS grammars with comment scanners"
type = "story"
category = "in-progress"
priority = "medium"
points = 5
parent = "01M47QJ3CHWZBZ6R3QHN4R2XN5"
reporter = "lognd"
created = "2026-10-04T11:28:48Z"
updated = "2026-10-06T05:36:47Z"
idempotency_key = "crunk-plan-lang"
labels = ["area:crunk"]
scope = ["crates/gob-languages/**", "crates/gob-directives/src/comments.rs", "crates/gob-directives/src/scan.rs", "Cargo.toml", "Cargo.lock"]

[[links]]
kind = "blocked-by"
target = "01M43A5DJT8XBQYEK36F0KSGKF"

[[acceptance]]
text = "Given a .tsx file, when parsed, then the typed tree is returned and a syntax error yields diagnostics with spans while the rest of the file stays queryable"
bound = false

[[acceptance]]
text = 'Given a CSS file with /* crunk:waive COLOR001 reason="brand" */, when scanned, then the directive is found in the crunk namespace with its span'
bound = false

[[acceptance]]
text = "Given the grammar pins, when the pin test runs, then it matches Cargo.toml"
bound = false
+++

notes/crunk.md section 3 and boundaries.md 2.4: crunk's tree-sitter wrapper (semantic/ts parser.py, ABI pin <0.26) is replaced by feature-gated grammars in gob-languages, pinned exactly against tree-sitter =0.27 (the ABI problem ends with one lock): features typescript, tsx, css; ERROR and MISSING nodes become PARSE diagnostics, not Err; /* */ and // comment scanners so `crunk:waive RULE reason="..."` is found by gob-directives with namespace crunk. Blocked by ~F0KSGKF because it holds the gob-languages scope lease; coordinate order with ~83EFRF2 and ~WHCDCMG (same crates).
