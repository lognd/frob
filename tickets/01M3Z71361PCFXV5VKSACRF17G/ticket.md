+++
id = "01M3Z71361PCFXV5VKSACRF17G"
title = "frob-lease: take configuration from the caller so registry_files reaches every verb"
type = "task"
category = "todo"
priority = "medium"
points = 2
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-02T21:06:24Z"
updated = "2026-10-02T21:06:24Z"
idempotency_key = "m2-leasecfg"
labels = ["milestone:2"]
scope = ["crates/frob-lease/**", "crates/frob-worktree/**", "crates/frob/**", "frob.toml"]

[[acceptance]]
text = "Given shared_files = [Cargo.lock], when two tickets both touch Cargo.lock, then frob work grants both leases"
bound = false
+++

T-0031 left the [tickets] registry_files alias honoured by doable only; open_store takes a LeaseConfig (or shared files) so work, lease list and contention see the same shared set; drop the alias once this repository's frob.toml uses [lease] shared_files.
