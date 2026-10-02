+++
id = "01M3ZEH3S0PG61C2AEBM691F69"
title = "gob-symbols: adapter registry, ConcreteTree::Source and entity kinds so non-tree-sitter adapters register"
type = "task"
category = "todo"
priority = "high"
points = 3
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-02T23:17:28Z"
updated = "2026-10-02T23:17:28Z"
idempotency_key = "m2-adapter-registry"
labels = ["milestone:2"]
scope = ["crates/gob-symbols/**", "crates/grimble-model/**", "crates/frob/**", "docs/reference/**"]

[[acceptance]]
text = "Given a binary linking grimble-model, when frob doctor --languages runs, then grmb appears at F4 with its capability precisions"
bound = false
+++

From ~63XJMC3 (D-a): adapters()/adapter_for are static over LanguageHint, so grimble-model's GrmbAdapter cannot register (grimble-model depends on gob-symbols). Add an inventory-based adapter registry, a ConcreteTree::Source(Arc<str>) variant for hand-written parsers (replacing grimble-model's thread-local hand-off), and SymbolKind variants for model entities (node, flow, contract, claim, vmodel, pack, boundary) so the FileSymbols view is populated; frob doctor --languages then lists grmb at F4 when the grimble-model crate is linked.
