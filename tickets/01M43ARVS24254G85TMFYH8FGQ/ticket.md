+++
id = "01M43ARVS24254G85TMFYH8FGQ"
title = "crunk binary and crunk-check: Product scaffold, --version, doctor, exit codes"
type = "story"
category = "done"
outcome = "done"
priority = "medium"
points = 5
parent = "01M43ANVJYA7GHN0Y8GX0SN72M"
reporter = "lognd"
created = "2026-10-04T11:28:46Z"
updated = "2026-10-04T12:51:36Z"
idempotency_key = "crunk-plan-bin"
labels = ["area:crunk"]
scope = ["crates/crunk/**", "crates/crunk-check/**", "docs/crunk/**", "Cargo.lock", "crates/frob-release/tests/products.rs"]

[[acceptance]]
text = "Given a directory with no crunk.toml, when `crunk check --json` runs, then it exits with the shared no-config code and the envelope names the remedy"
bound = true

[[acceptance]]
text = "Given an empty valid config, when `crunk check --json` runs, then stdout is a gob.sibling/1 document with product crunk that validates against docs/schemas/sibling.json"
bound = true

[[acceptance]]
text = "Given `crunk --version`, then it prints the workspace lockstep version"
bound = true
+++

Create the `crunk` package (binary crunk, no `crk` alias unless the owner asks) and crunk-check, which implements gob-check's Product trait the way grimble-check does, over gob-cli, gob-config, gob-walk, gob-cache. Verbs for this ticket: check (empty rule set, emits the sibling document gob.sibling/1 with product=crunk, docs/design/sibling-contract.md), doctor, --version, exit codes 0/1/2 per cli.md section 2, --json/--color/-v globals. Mirror crates/grimble layout. [package.metadata.dist] dist = true is added by the registration ticket, not here. Sources: crunk __main__.py (337 LOC) and app shell, docs/commands/*.md for flags. docs/design/products.md section 1, boundaries.md 2.4 and 6.
