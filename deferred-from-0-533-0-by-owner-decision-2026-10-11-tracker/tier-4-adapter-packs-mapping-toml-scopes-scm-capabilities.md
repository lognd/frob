+++
id = "01M3ZX7T0WTQ93A8DWG8HJZ9MP"
title = "Tier-4 adapter packs: mapping.toml, scopes.scm, capabilities, fidelity corpus"
type = "task"
category = "todo"
priority = "low"
points = 5
parent = "01M3ZX76SB6GRNSW6AVFRFVJVQ"
reporter = "lognd"
created = "2026-10-03T03:34:32Z"
updated = "2026-10-03T03:34:32Z"
idempotency_key = "m2-adapters-pack"
labels = ["milestone:2", "area:packs"]
scope = ["crates/gob-packs/src/adapters/**"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7JN8RWAKDVYK0BNG3E2K"

[[links]]
kind = "blocked-by"
target = "01M3ZX7JRYNHG0BHJ3ZHC9450N"

[[acceptance]]
text = "Given a mapping.toml missing a node kind present in node-types.json, when loaded, then a load finding names the kind"
bound = false

[[acceptance]]
text = "Given an adapter whose fidelity corpus fails, when loaded, then the language is reported at the measured fidelity level, not the claimed one"
bound = false
+++

Implements plugins.md section 8.

Declarative mapping of node kinds to U operators checked against node-types.json (an unmapped kind is a load finding), a locals-style scopes file with Must/May/Unknown references, capability precisions and a fidelity corpus run once per version; unexpressible nodes become opaque and Unresolved.
