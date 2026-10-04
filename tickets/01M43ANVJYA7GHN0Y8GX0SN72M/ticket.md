+++
id = "01M43ANVJYA7GHN0Y8GX0SN72M"
title = "crunk in the monorepo"
type = "epic"
category = "todo"
priority = "medium"
points = 13
reporter = "lognd"
created = "2026-10-04T11:27:07Z"
updated = "2026-10-04T11:28:45Z"
labels = ["area:crunk"]
+++

Move the front-end design-system goblin (the Python crunk, 24.5k LOC, the crunk repository) into this workspace as the Rust `crunk` product: one binary, crunk-* library crates, shared gob-* substrate. Design: docs/design/monorepo.md sections 1-5, products.md (crunk row, D87 section 6), boundaries.md 2.4 and 2.5, releases.md section 7; survey in notes/crunk.md. D89 splits the web lint: crunk keeps pack crunk-web (A11Y, SEO, LAUNCH, WEBPERF markup and assets); the grimble packs are a separate epic. Order: wave 1 is crunk-values, the crunk binary scaffold, crunk-tailwind tables and the parity corpus capture; then registration and sibling wiring, ingest on gob-languages and gob-symbols, spec, tokens, rules, fix, query verbs, gallery, crunk-web, parity, ticket import, retirement of the Python crunk. Rules start as Rust tier-0 (plugins.md section 4: recorded exceptions) because GRL has no value-domain operators and no CSS declaration kind yet; LAYER and ORG move to GRL in a follow-up. See the report of the planner for milestone placement and owner decisions.
