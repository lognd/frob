+++
id = "01M53B2RR2W6PZN5RFFY8CNED9"
title = "GRL constructs to express LAYER and ORG, remainder: crunk host input, class-selector kind, bucket attribute, crunk.json side relations"
type = "story"
category = "todo"
priority = "medium"
points = 3
parent = "01M4Z1KTKEVF53GWM6ZN7PFN4Q"
reporter = "lognd"
created = "2026-10-16T21:49:52Z"
updated = "2026-10-17T01:18:08Z"
scope = ["crates/gob-ir/src/style.rs", "crates/gob-ir/tests/it/web.rs", "crates/gob-symbols/src/css/mod.rs", "crates/gob-symbols/tests/it/css.rs", "crates/gob-plan/src/exec/core/kind.rs", "crates/gob-plan/src/catalog/mod.rs", "crates/gob-plan/tests/web_rule.rs", "docs/generated/**", "docs/README.md", "docs/assets", "docs/crunk", "docs/decisions", "docs/design", "docs/guides", "docs/migration", "docs/reference", "docs/schemas"]

[[acceptance]]
text = "Given the GRL rules, when the std pack builds, then findings equal the removed Rust rules on the corpus"
bound = false

[[acceptance]]
text = "Given the conformance test, when it runs, then compiled and plan findings are byte identical"
bound = false
+++

Follow-up of ~KR11AZT, which landed the integer value predicate (is integer). Remaining blockers are listed in packs/crunk-core/exceptions.toml: css class-selector node (needs gob-symbols css + gob-ir style), per-file bucket attribute, glob membership over config.org columns, config.layers/org side relations typed from docs/schemas/crunk.json, gen rules target for a non-std pack with a CrunkHost.
