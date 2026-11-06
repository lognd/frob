+++
id = "01M680RDGMV8XCRQP27ABW7H0Q"
title = "Docs: move doc clusters per the approved tree (consolidation phase 3)"
type = "docs"
category = "in-progress"
priority = "medium"
points = 5
parent = "01M67VDQ8WGS0SYG4J4NFXNQJE"
reporter = "lognd"
created = "2026-10-31T03:41:21Z"
updated = "2026-11-06T01:00:13Z"
scope = ["docs/**", "crates/*/src/**", "packs/grimble-websec/pack.toml", "crates/frob/tests/it/doc_commands.rs", "crates/gob-dev/tests/layering.rs", "crates/frob-mirror/tests/support/fake_github.rs", "README.md"]

[[links]]
kind = "blocked-by"
target = "01M4GRAVWQ8W227X5E335CQFYN"

[[acceptance]]
text = "Given the approved target tree, when done, then every phase 3 move is in MOVED.toml, applied with frob doc remap, and frob check and gob-dev gen --check are clean"
bound = false
+++

Do only after the owner approves the audit; one commit per cluster.
