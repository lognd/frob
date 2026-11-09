+++
id = "01M5BSTQWD096Z3AKQNNB0YFYT"
title = "Wire TICK011 into frob check, explain catalog and product rule list"
type = "task"
category = "in-progress"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-20T04:41:33Z"
updated = "2026-11-09T07:09:00Z"
labels = ["no-story"]
scope = ["crates/frob-check/src/product.rs", "crates/frob/src/explain_cmd.rs", "crates/frob-check/src/ledger_protection.rs", "crates/frob-check/Cargo.toml", "crates/frob-check/src/lib.rs", "crates/frob/src/doctor.rs", "Cargo.lock", "docs/design/frob/tickets.md", "changelog.d/01M5BSTQWD096Z3AKQNNB0YFYT.added.md"]

[[acceptance]]
text = "frob check evaluates TICK011 for the orphan ticket branch through a shared GitHub probe that doctor also uses"
bound = true
+++

found while working ~ZK2SR2P: only doctor emits TICK011 today

no-story: internal engineering task in frob-check; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
