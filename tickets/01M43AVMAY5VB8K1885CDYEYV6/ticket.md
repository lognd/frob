+++
id = "01M43AVMAY5VB8K1885CDYEYV6"
title = "crunk product docs: CLI and rule reference, migration guide from Python crunk"
type = "docs"
category = "todo"
priority = "medium"
points = 3
parent = "01M43ANVJYA7GHN0Y8GX0SN72M"
reporter = "lognd"
created = "2026-10-04T11:30:17Z"
updated = "2026-10-04T11:30:17Z"
idempotency_key = "crunk-plan-docs"
labels = ["area:crunk"]
scope = ["docs/crunk/**", "README.md"]

[[links]]
kind = "blocked-by"
target = "01M43ATBY4CHA4FYVC7BWK6MXR"

[[links]]
kind = "blocked-by"
target = "01M43ATCF5GGK59S96K1ZF0G9C"

[[links]]
kind = "blocked-by"
target = "01M43ATCQVX9A1TJ6A4AE48FDX"

[[acceptance]]
text = "Given the docs, when `cargo dev gen --check` runs, then generated pages are current"
bound = false

[[acceptance]]
text = "Given each Python crunk verb, when the migration guide is read, then its Rust equivalent or its removal is stated"
bound = false

[[acceptance]]
text = "Given the docs, when scanned, then there are no absolute home paths and only ASCII"
bound = false
+++

Per-product docs (monorepo.md 2): generated CLI and rule pages, the config guide, the token export guide, and a migration guide for users of the Python crunk (pip name unchanged, `crk` alias decision, flag differences, no more tinycss2/tree-sitter pin, cache location). Port docs/commands/*.md and docs/guides from the crunk repository.
