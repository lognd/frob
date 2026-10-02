+++
id = "01M3WYJ80DWFZK0DPR4CBP0KHT"
title = "gob-symbols: symrefs, three-facet digests, imports and call graph for Rust and markdown"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 13
parent = "01M3WYJ802ZVWE6E3050EVRCSV"
reporter = "agent"
created = "2026-10-02T00:00:00Z"
updated = "2026-10-02T00:00:03Z"
aliases = ["T-0013"]
labels = ["milestone:2.0.0", "component:gob-symbols"]
scope = ["crates/gob-symbols/**"]

[[links]]
kind = "blocked-by"
target = "01M3WYJ80BJ3NMGNWTAJ7SYPA5"

[[links]]
kind = "blocked-by"
target = "01M3WYJ80C2XQD40EYQWHEWDKK"

[[acceptance]]
text = "Given a Rust file, when extracted, then every public item has a symref, a kind and three digests, and renaming a parameter changes sig but not body"
bound = false

[[acceptance]]
text = "Given fn a calls fn b in the same crate, when affects(b) is queried, then a is returned"
bound = false

[[acceptance]]
text = "Given a markdown file with headings, when extracted, then each heading is path#slug with GitHub-style slugging"
bound = false
+++

Implement crates/gob-symbols per code-model.md sections 2 and 3 and D31. Symbol extraction for Rust (modules, fns, structs, enums, traits, impls, consts, macros, with visibility) and markdown (headings as anchors path#slug), yielding SymbolRecord { symref path::Qual.Name or path#slug, kind, span, visibility, digests { sig, body, doc } as blake3 of normalized text facets }. Imports (use trees resolved to crate-relative paths where possible) and a conservative call graph for Rust (callee names resolved within the crate, unresolved kept as names). Repository-level SymbolGraph with petgraph: nodes are symbols, edges Imports/Calls/Contains; a public-API view; affects(symref) and reach(symref, kind) queries; graph digest for repo-rule cache keys. Incremental: per-file extraction keyed by file digest through gob-cache. Parallel over files with rayon. Symref parsing and ambiguity errors per code-model.md section 2. Markdown corpus tests (plain files under tests/corpus until gob-mdtest lands) and criterion bench on this repository.
