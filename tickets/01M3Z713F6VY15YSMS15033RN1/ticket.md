+++
id = "01M3Z713F6VY15YSMS15033RN1"
title = "gob-symbols over U: Rust and markdown adapters produce U terms with status edges"
type = "task"
category = "todo"
priority = "high"
points = 13
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-02T21:06:24Z"
updated = "2026-10-02T21:06:24Z"
idempotency_key = "m2-symbols"
labels = ["milestone:2"]
scope = ["crates/gob-symbols/**", "crates/gob-languages/**", "crates/frob/**"]

[[links]]
kind = "blocked-by"
target = "01M3Z712DPZN71ZQDS6PXY6QQV"

[[acceptance]]
text = "Given a Rust fn passed as a value to another fn, when the graph is built, then an edge with status May exists and affects() follows it"
bound = false

[[acceptance]]
text = "Given a file in a language without a grammar, when walked, then it appears as one opaque unit at fidelity F0 and every rule reports it Unresolved or NotApplicable"
bound = false
+++

universal-model.md 8 and 7 (G1-G4, G10-G19): SymbolRecord becomes the unit view of U terms; edges carry Must/May/Unknown; references are a superset of calls; functions passed as values are edges; re-exports in public_api; parse_status and holes are visible; unknown files are F0 opaque; attributes in the Sig stream, comments out of the Body stream, markdown section digests section-local; fidelity corpus per language; frob doctor --languages prints fidelity and capability precision.
