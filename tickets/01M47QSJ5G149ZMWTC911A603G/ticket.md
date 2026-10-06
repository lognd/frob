+++
id = "01M47QSJ5G149ZMWTC911A603G"
title = "cargo dev gen iterates registered product artifacts instead of calling products by name"
type = "story"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M47QSB9W3BVYZ4NPRVX11TG4"
reporter = "lognd"
created = "2026-10-06T04:33:18Z"
updated = "2026-10-06T07:45:41Z"
scope = ["crates/gob-dev/**", "crates/crunk-spec/**", "crates/frob-cli/**", "crates/grimble/**", "crates/gob-config/**"]

[[acceptance]]
text = "gob-dev source names no product function for generation"
bound = false

[[acceptance]]
text = "cargo dev gen --check is clean with byte-identical generated files"
bound = false
+++

products.md section 7. Each product registers its generated artifacts (JSON schemas, reference pages) through an inventory entry; gob-dev's render step iterates the registry instead of calling crunk_spec::schema and frob_cli functions directly. gob-dev still links the products. GEN001 output must not change.
