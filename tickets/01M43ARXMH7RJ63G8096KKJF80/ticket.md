+++
id = "01M43ARXMH7RJ63G8096KKJF80"
title = "gob-symbols: TS/TSX adapter with symbols, bindings and module graph"
type = "story"
category = "in-progress"
priority = "medium"
points = 8
parent = "01M47QJ3CHWZBZ6R3QHN4R2XN5"
reporter = "lognd"
created = "2026-10-04T11:28:48Z"
updated = "2026-10-06T07:44:21Z"
idempotency_key = "crunk-plan-tssym"
labels = ["area:crunk"]
scope = ["crates/gob-symbols/src/typescript/**", "crates/gob-symbols/tests/typescript*.rs", "docs/reference/fidelity.md", "crates/gob-symbols/src/lib.rs", "crates/gob-symbols/src/registry.rs", "crates/gob-symbols/src/pipeline.rs", "crates/gob-symbols/src/view.rs", "crates/gob-symbols/src/graph.rs", "crates/gob-symbols/src/graph/typescript.rs", "frob.toml"]

[[links]]
kind = "blocked-by"
target = "01M43ARXDXMJ99H23MV17ZVW3R"

[[acceptance]]
text = "Given the web_pages fixture, when indexed, then every import resolves as Must, May or Unknown identically to the Python module graph"
bound = false

[[acceptance]]
text = "Given a dynamic import or computed require, when indexed, then the edge is Unknown, never dropped"
bound = false

[[acceptance]]
text = "Given the adapter, when `frob explore` style views run on a TSX file, then declarations and JSX elements are listed"
bound = false
+++

Port crunk.semantic.ts parser-independent parts (symbols, bindings, module_graph; 2.5k LOC with consteval) to a gob-symbols adapter that emits U terms: declarations, imports with Must/May/Unknown edges, re-exports, path alias resolution (tsconfig paths), JSX elements and attributes as terms. monorepo.md section 3, boundaries.md 2.1 (crunk TS module graph). Fidelity row recorded honestly (what is Unknown by nature). Port tests/unit/test_semantic_ts_module_graph.py and parser tests. Scope uses a new module directory to avoid the ~F0KSGKF files.
