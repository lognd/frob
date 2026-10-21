+++
id = "01M54GWME19N64RRMBTCZSG7YJ"
title = "GRL constructs to express LAYER and ORG, rest: crunk host input, bucket attribute, glob membership, crunk.json side relations, gen rules non-std target"
type = "story"
category = "done"
outcome = "done"
priority = "medium"
points = 3
parent = "01M4Z1KTKEVF53GWM6ZN7PFN4Q"
reporter = "lognd"
created = "2026-10-17T08:50:37Z"
updated = "2026-10-21T09:05:35Z"
scope = ["crates/gob-plan/src/catalog/config.rs", "crates/gob-plan/tests/catalog.rs", "packs/crunk-core/exceptions.toml", "changelog.d/01M54GWME19N64RRMBTCZSG7YJ.added.md", "docs/design/grl-spec.md"]

[[acceptance]]
text = "ConfigSchema types crunk.json org and layers as side relations (value rows, int layer values, enum class_case as string)"
bound = true
+++

Follow-up of ~Y8CNED9, which landed the css class_selector node kind (gob-symbols css, gob-ir style, gob-plan kind). Remaining blockers in packs/crunk-core/exceptions.toml: per-file bucket attribute, glob membership over config.org columns, config.layers/org side relations typed from docs/schemas/crunk.json, gen rules target for a non-std pack with a CrunkHost, BEM segment predicates.
