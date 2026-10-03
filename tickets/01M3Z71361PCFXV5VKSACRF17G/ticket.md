+++
id = "01M3Z71361PCFXV5VKSACRF17G"
title = "frob-lease: take configuration from the caller so registry_files reaches every verb"
type = "task"
category = "in-progress"
priority = "medium"
points = 2
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-02T21:06:24Z"
updated = "2026-10-03T08:58:14Z"
idempotency_key = "m2-leasecfg"
labels = ["milestone:2", "release:0.532.0"]
scope = ["crates/frob-lease/**", "crates/frob-worktree/**", "crates/frob/**", "frob.toml", "crates/frob-land/src/land.rs", "docs/design/README.md", "docs/design/architecture.md", "docs/design/tickets.md", "docs/reference/config.md", "docs/schemas/config.json"]

[[acceptance]]
text = "Given shared_files = [Cargo.lock], when two tickets both touch Cargo.lock, then frob work grants both leases"
bound = true
+++

T-0031 left the [tickets] registry_files alias honoured by doable only; open_store takes a LeaseConfig (or shared files) so work, lease list and contention see the same shared set; drop the alias once this repository's frob.toml uses [lease] shared_files.
