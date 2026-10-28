+++
id = "01M3ZX7SREAYJMKRMTGDC2P7WJ"
title = "Conformance test applies to WASM-built packs"
type = "task"
category = "todo"
priority = "low"
points = 3
parent = "01M3ZX76SB6GRNSW6AVFRFVJVQ"
reporter = "lognd"
created = "2026-10-03T03:34:32Z"
updated = "2026-10-28T12:55:51Z"
idempotency_key = "m2-wasm-conformance"
labels = ["milestone:2", "area:packs", "kind:test", "no-story"]
scope = ["crates/gob-plan/tests/conformance/**"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7HRM8SVB3607V973VQTH"

[[links]]
kind = "blocked-by"
target = "01M3ZX7SMJ1W3K92Z6J59CYGQT"

[[acceptance]]
text = "Given a std rule built to a component, when the conformance test runs, then plan and component JSON are byte-identical"
bound = false

[[acceptance]]
text = "Given a divergent component, when run, then the test fails naming the rule"
bound = false
+++

Implements plugins.md section 6.1.

The conformance harness gains a third form: the pack built to WASM.

no-story: internal engineering task in gob-plan; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
