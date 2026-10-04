+++
id = "01M43MPG53JR8TP0E15394FZ5T"
title = "gob-config: product-scoped config registries and dynamic-key tables; migrate crunk-spec"
type = "story"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-04T14:22:14Z"
updated = "2026-10-04T14:22:14Z"

[[acceptance]]
text = "Given frob and crunk config tables, when gen runs, then each product gets its own reference page and schema and neither contains the other's keys"
bound = false

[[acceptance]]
text = "Given crunk-spec, when built, then its tables are declared through gob-config, not hand-written serde and schemars types"
bound = false
+++

gob-config's ConfigTable derive registers every table in one global inventory, so a crate in another product (crunk-spec, for crunk.toml) cannot use it without its keys leaking into frob's docs/reference/config.md and docs/schemas/config.json. ~BWXXV5H therefore defined crunk.toml with plain serde and schemars types, a second way to declare config. Make registries product-scoped (each table names the config file and product it belongs to; gen emits one reference page and schema per product), support dynamic-key tables (palette, lint, breakpoints) in the derive, and migrate crunk-spec onto it so there is one config declaration mechanism. Read D87 (one binary per package) in docs/design/README.md.
