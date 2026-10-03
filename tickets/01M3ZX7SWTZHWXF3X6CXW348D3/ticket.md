+++
id = "01M3ZX7SWTZHWXF3X6CXW348D3"
title = "Benchmark B3: tier-3 per-file call versus the same rule in tier 0"
type = "task"
category = "todo"
priority = "low"
points = 3
parent = "01M3ZX76SB6GRNSW6AVFRFVJVQ"
reporter = "lognd"
created = "2026-10-03T03:34:32Z"
updated = "2026-10-03T03:34:32Z"
idempotency_key = "m2-bench-b3"
labels = ["milestone:2", "area:packs", "kind:test"]
scope = ["crates/gob-wasm/benches/**"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7SCND92D383E8X9CEWJ7"

[[acceptance]]
text = "Given a rule in tier 0 and as a component, when the bench runs, then the ratio is reported and the gate fails above 1.5x"
bound = false

[[acceptance]]
text = "Given both runs, when compared, then findings are equal"
bound = false
+++

Implements plugins.md section 6.6 (B3).

Target within 1.5x.
