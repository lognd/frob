+++
id = "01M6SJHAYG2757SX0J21YGJ7WB"
title = "Grimble LOG: resolve through the universal model (gob-symbols terms, gob-ir queries), not per-language tree-sitter walkers"
type = "story"
category = "in-progress"
priority = "high"
points = 8
reporter = "lognd"
created = "2026-11-06T23:19:09Z"
updated = "2026-11-09T10:29:59Z"
scope = ["crates/grimble-check/src/log/**", "changelog.d/01M6SJHAYG2757SX0J21YGJ7WB.*", "docs/design/grimble/output-atoms.md", "crates/grimble-check/**"]

[[acceptance]]
text = "No LOG atom decision depends on raw callee text; every language resolves via U queries or reports Unresolved"
bound = false
+++

Audit: crates/grimble-check/src/log/lang_{python,js,rust,java,c,csharp,bash}.rs walk raw tree_sitter nodes with per-language string matching (engine.rs State::resolve_segs, catalogue.rs when-clause text). Per docs/design/shared/universal-model.md sections 3, 5, 8 rules are written once against U via gob-symbols adapters and gob-ir queries, unknowns are Unresolved. Plan: inventory remaining lexical checks (callee path text, mode strings, std-stream names, aliasing); express call-target, alias and literal-argument resolution as U queries; one language-neutral LOG pass over U, deleting lang_*.rs walkers as covered; lexical fallbacks yield Unresolved never clean. Sequence after HQW3WE8, 233F9ZV, KGBAD9H land (log/** scope overlap).
