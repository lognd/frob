+++
id = "01M4H0XB30TVD3TW813XPA3A54"
title = "User guides and per-product reference: guides/grimble.md and crunk.md, upgrade guide absorbs the v1 migration docs, reference/{cli,config}/<product>, one rules index for all products"
type = "docs"
category = "todo"
priority = "medium"
points = 5
parent = "01M4H0WWHV461NXWVCCNKAH3YP"
reporter = "lognd"
created = "2026-10-09T19:05:49Z"
updated = "2026-10-09T19:05:49Z"
idempotency_key = "docs-consolidation-2026-10-09-p6"
labels = ["creates:docs/guides/grimble.md", "creates:docs/guides/crunk.md", "creates:docs/history/migration-v1.md"]
scope = ["docs/guides/**", "docs/reference/**", "docs/crunk/**", "docs/migration/**", "docs/design/migration.md", "docs/schemas/**", "crates/gob-dev/src/render/**", "crates/gob-dev/src/main.rs", "crates/crunk-spec/src/schema.rs", "crates/crunk-rules/src/registry.rs", "crates/crunk-check/tests/waive001.rs", "crates/crunk-tokens/README.md", "crates/crunk-tailwind/README.md", "README.md", "docs/README.md", "docs/MOVED.toml", "changelog.d/**", "docs/guides/grimble.md", "docs/guides/crunk.md", "docs/history/migration-v1.md"]

[[links]]
kind = "blocked-by"
target = "01M4H0WZ6Z1MDH6G815EE8MASY"

[[acceptance]]
text = "Given the generators, when `cargo dev gen` runs, then docs/reference/cli/{frob,grimble,crunk,any}.md and docs/reference/config/{frob,crunk}.md exist and docs/reference/rules/README.md indexes frob, grimble and crunk rules, and docs/crunk/ no longer exists"
bound = false

[[acceptance]]
text = "Given docs/migration/v1-import.md, migration.md 2-3 and docs/reference/changelog.md, when phase 6 lands, then the upgrade and release guides state the field mapping and fragment rules once and docs/history/migration-v1.md holds the rest"
bound = false

[[acceptance]]
text = "Given docs/guides/release.md#one-time-setup, when phase 6 lands, then that anchor still exists, and frob check reports zero DOC002 and zero DRIFT002 findings, and `cargo dev gen --check` is clean"
bound = false
+++

Phase 6 of notes/review/docs-consolidation-2026-10-09.md (sections 3.1, 3.2, 4.1). Generator paths change in gob-dev and crunk-spec; the crunk rules index joins `cargo dev gen rules`; docs/migration/v1-selection.toml moves with the gob-dev default. Covers ~QQSAJAT (grimble guide). Split 3 + 2 if the generator change is large.
