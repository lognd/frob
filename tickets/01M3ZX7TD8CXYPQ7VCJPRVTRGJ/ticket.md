+++
id = "01M3ZX7TD8CXYPQ7VCJPRVTRGJ"
title = "Benchmark B4: WASM tree-sitter grammar versus native, published per adapter"
type = "task"
category = "todo"
priority = "low"
points = 2
parent = "01M3ZX76SB6GRNSW6AVFRFVJVQ"
reporter = "lognd"
created = "2026-10-03T03:34:33Z"
updated = "2026-10-03T03:34:33Z"
idempotency_key = "m2-bench-b4"
labels = ["milestone:2", "area:packs", "kind:test"]
scope = ["crates/gob-wasm/benches/**"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7T99WHFM0DHJXAHY68NM"

[[acceptance]]
text = "Given one grammar in both forms, when the bench runs, then the ratio is written to the bench report"
bound = false

[[acceptance]]
text = "Given the report, when read, then it names the adapter and the grammar version"
bound = false
+++

Implements plugins.md section 6.6 (B4).

Measured and published, not gated.
