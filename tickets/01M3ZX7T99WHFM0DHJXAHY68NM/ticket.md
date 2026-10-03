+++
id = "01M3ZX7T99WHFM0DHJXAHY68NM"
title = "WASM tree-sitter grammar loading inside the worker"
type = "task"
category = "todo"
priority = "low"
points = 5
parent = "01M3ZX76SB6GRNSW6AVFRFVJVQ"
reporter = "lognd"
created = "2026-10-03T03:34:33Z"
updated = "2026-10-03T03:34:33Z"
idempotency_key = "m2-wasm-grammar"
labels = ["milestone:2", "area:packs"]
scope = ["crates/gob-wasm/src/grammar/**"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7SCND92D383E8X9CEWJ7"

[[links]]
kind = "blocked-by"
target = "01M3ZX7T0WTQ93A8DWG8HJZ9MP"

[[acceptance]]
text = "Given a third-party WASM grammar, when a file is parsed, then parsing runs in the worker and a parse over budget makes the file opaque with Unresolved budget"
bound = false

[[acceptance]]
text = "Given the same file under the native grammar, when compared, then the U terms are equal for a corpus file"
bound = false
+++

Implements plugins.md sections 6.6 (B4) and 8; security.md section 2.9.

Third-party grammars as WASM, trust-gated, budgeted; native grammars stay compiled in for std languages.
