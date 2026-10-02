+++
id = "01M3WYJ80WDCC3PR0XGNHWHNHY"
title = "TicketField derive: generate ticket frontmatter serde, schema and docs table from one declaration"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 3
parent = "01M3WYJ802PGVRR55XCM9C3KV9"
reporter = "agent"
created = "2026-10-02T00:00:00Z"
updated = "2026-10-02T00:00:03Z"
aliases = ["T-0028"]
labels = ["milestone:2.0.0", "component:gob-macros"]
scope = ["crates/gob-macros/**", "crates/frob-ledger/src/schema.rs", "crates/frob-ledger/Cargo.toml"]

[[links]]
kind = "blocked-by"
target = "01M3WYJ80E4PPKMTXS4CG0HCH6"

[[links]]
kind = "blocked-by"
target = "01M3WYJ80J56GDD3VY4N8J4DJR"

[[acceptance]]
text = "Given the frontmatter struct with the derive, when cargo dev gen runs, then the ticket field reference page lists every field with its doc and default"
bound = false
+++

Split from T-0018. Add #[derive(TicketField)] (or a struct-level TicketSchema derive) to gob-macros that generates serde impls, a JSON schema and a FieldDescription inventory entry for the ticket frontmatter struct in frob-ledger, replacing the hand-written schema table T-0018 ships with. Keep the frontmatter format byte-identical.
