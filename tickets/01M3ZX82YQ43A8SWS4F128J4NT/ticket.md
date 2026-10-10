+++
id = "01M3ZX82YQ43A8SWS4F128J4NT"
title = "Migrate this repository's tickets from tickets/ on the code branch to the ticket branch"
type = "task"
category = "in-progress"
priority = "high"
points = 3
parent = "01M3ZX77302X3HQF4Z4P7WC0WS"
reporter = "lognd"
created = "2026-10-03T03:34:41Z"
updated = "2026-10-10T01:24:33Z"
idempotency_key = "m2-tb-migrate"
labels = ["milestone:2", "area:mirror"]
scope = ["crates/frob/src/ticket/migrate_cmd.rs", "crates/frob-ledger/src/migrate.rs", "crates/frob-ledger/src/lib.rs", "crates/frob/src/ticket/mod.rs", "crates/frob/tests/ticket_migrate.rs", "docs/reference/cli/frob.md", "changelog.d/**"]

[[links]]
kind = "blocked-by"
target = "01M3ZX82TWWY2616S1Q5N48KNK"

[[acceptance]]
text = "Given this repository's ledger, when migrated in a scratch clone, then every ticket folds to identical frontmatter on the new branch"
bound = true

[[acceptance]]
text = "Given the migrated branch, when `frob ticket doctor` runs, then it reports no errors"
bound = true
+++

Implements mirror.md section 1; migration.md (underspecified, see report).

A verb that copies the ledger into the orphan branch, keeps ULIDs and event ids, switches [tickets] ref, and verifies the folded state is identical before and after.
