+++
id = "01M4069Z0HH5RV8TNPFVA936C5"
title = "frob init adoption: an existing Cargo project with history, no hard-coded base branch"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 3
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-03T06:13:00Z"
updated = "2026-10-03T15:28:25Z"
idempotency_key = "m2-rel-init-adopt"
labels = ["milestone:2", "area:release"]
scope = ["crates/frob/src/init.rs", "crates/frob/tests/init_adopt.rs", "crates/frob/src/config_cmd.rs", "crates/frob/tests/e2e_init_loop.rs", "crates/gob-check/src/config.rs", "crates/frob-check/src/product.rs", "crates/frob-check/tests/check.rs", "crates/frob/tests/snapshots/*", "crates/frob/tests/cli.rs", "docs/reference/config.md", "docs/design/cli.md", "docs/design/rules.md"]

[[links]]
kind = "blocked-by"
target = "01M3Z712ZXXKVJYREYG65P3P35"

[[links]]
kind = "blocked-by"
target = "01M3ZZXAZ39410AVYQSRSYVF9C"

[[links]]
kind = "blocked-by"
target = "01M405B09EW2M0NDNTXKHXV2X7"

[[links]]
kind = "blocked-by"
target = "01M4069YW2EF551WF2J7R0EMJ4"

[[acceptance]]
text = "Given a repository on branch main with existing code, when frob init and frob check run, then base is main and check exits 0"
bound = true

[[acceptance]]
text = "Given a repository on master, when init runs, then base is master"
bound = true
+++

On a repository whose default branch is main (or master, or trunk) with tracked files and a Cargo.toml, init detects the base branch for [check] base (this repository's own value is experimental), ignores .frob/, installs the merge driver, writes no ticket data into the working tree beyond the ledger ref, and a following frob check runs clean or with only documented findings.
