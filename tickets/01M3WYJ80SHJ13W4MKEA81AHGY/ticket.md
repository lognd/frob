+++
id = "01M3WYJ80SHJ13W4MKEA81AHGY"
title = "Self-host switch: v2 frob.toml, import this repo's v1 tickets, CI runs frob v2 check"
type = "task"
category = "todo"
priority = "high"
points = 5
parent = "01M3WYJ802PGVRR55XCM9C3KV9"
reporter = "agent"
created = "2026-10-02T00:00:00Z"
updated = "2026-10-02T00:00:00Z"
aliases = ["T-0025"]
labels = ["milestone:2.0.0", "component:selfhost"]
scope = ["frob.toml", "tickets/**", "crates/gob-dev/**", ".github/**", "CONTRIBUTING.md", "notes/coordinator.md", ".gitignore", "notes/**", "docs/design/**", "docs/reference/**", "rustfmt.toml", "rust-toolchain.toml", "clippy.toml", "deny.toml", ".cargo/**", ".config/**", "crates/frob-ack/tests/**", "crates/frob-obligations/tests/**", "Cargo.toml", "README.md", "docs/migration/**"]

[[links]]
kind = "blocked-by"
target = "01M3WYJ80RBBNFYD89NF0X48R0"

[[acceptance]]
text = "Given the repository after the switch, when CI runs, then frob check and frob test from the v2 binary pass"
bound = false

[[acceptance]]
text = "Given the v1 tickets, when imported, then every v1 id resolves through an alias and the count matches"
bound = false
+++

Switch this repository from v1 frob to frob v2 per migration.md section 2 step 1 and D36. Write the materialized frob.toml for v2 (frob init), add a one-off script under crates/gob-dev (cargo dev import-v1-tickets) that converts tickets/T-*/ticket.md from the v1 ledger into v2 ULID tickets minted from the v1 created timestamps with aliases = ["T-0001"...], add frob check and frob test to .github/workflows/ci.yml using the built binary, remove the v1 check_base key, update CONTRIBUTING.md with the v2 workflow (work, check, test, land), and record in notes/coordinator.md that v2 is live. Record every v1-only field that could not be carried as a dropped item with reason.
