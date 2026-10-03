+++
id = "01M3ZX80K6BAB9B2SJKX80Q4DH"
title = "Adapter guards: claimed ids, NotApplicable claims, by-declaration marks"
type = "task"
category = "todo"
priority = "low"
points = 5
parent = "01M3ZX76WPYZQ4Q5WDQ72AWMZQ"
reporter = "lognd"
created = "2026-10-03T03:34:39Z"
updated = "2026-10-03T03:34:39Z"
idempotency_key = "m2-sec-adapter-guards"
labels = ["milestone:2", "area:security"]
scope = ["crates/gob-packs/src/adapters/guards.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7S5JYVCTRD0ZYC57GJ93"

[[links]]
kind = "blocked-by"
target = "01M3ZX7T0WTQ93A8DWG8HJZ9MP"

[[acceptance]]
text = "Given an adapter claiming .rs, when loaded, then PACK004 is emitted"
bound = false

[[acceptance]]
text = "Given an in-source declaration that would remove a target found by the adapter, when applied, then the target remains"
bound = false
+++

Implements security.md section 2.9.

An adapter may not claim an extension or language id already claimed (PACK004); repository NotApplicable claims are listed in the fidelity report and counted by GATE001; a claim for an atom owned by another pack is PACK005; in-source declarations are marked by-declaration and may add targets but never remove one the adapter found.
