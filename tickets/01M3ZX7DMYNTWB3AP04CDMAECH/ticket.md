+++
id = "01M3ZX7DMYNTWB3AP04CDMAECH"
title = "Relation catalog: kinds, fields, verbs, side relations and language ids"
type = "task"
category = "todo"
priority = "high"
points = 5
parent = "01M3ZWPE0CNFWB4PTW3D05GDWP"
reporter = "lognd"
created = "2026-10-03T03:34:20Z"
updated = "2026-10-03T03:35:00Z"
idempotency_key = "m2-grl-catalog"
labels = ["milestone:2", "area:grl"]
scope = ["crates/gob-plan/src/catalog/**"]

[[links]]
kind = "blocked-by"
target = "01M3ZX779NSRZ97ZQM5DP3BZJZ"

[[links]]
kind = "relates"
target = "01M3ZEH464EFCFAZ4XDKE89D5Z"

[[acceptance]]
text = "Given the gob-ir registry, when the catalog is built, then every word of grl-spec section 6 has a kind, a type, its Q-id, the languages that answer it and an Unknown-capable flag"
bound = false

[[acceptance]]
text = "Given the side relation config.invariants.forbid_imports, when typed, then its columns come from docs/schemas/config.json and a misspelt column is not a member"
bound = false
+++

Implements grl-spec.md section 6; universal-model.md section 5.

Single list of everything a rule can name, built from the gob-ir registry: each word with type, universal query id, languages that answer it, Unknown-capable flag, comment markers per language, and typed side-relation schemas (config, diff, lease, model).
