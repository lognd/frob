+++
id = "01M4BDMJQY38FFYK0J7FB6FTR5"
title = "gob-check ui_product trybuild stderr depends on whether rust-src is installed"
type = "bug"
category = "in-progress"
priority = "medium"
reporter = "lognd"
created = "2026-10-07T14:52:47Z"
updated = "2026-10-07T15:10:24Z"
idempotency_key = "gob-check-ui-product-rust-src"
labels = ["milestone:2"]
scope = ["rust-toolchain.toml", "crates/gob-check/tests/ui_product/**"]

[[acceptance]]
text = "Given a host with rust-src installed and one without, when gob-check::ui_product runs, then both pass with the same committed .stderr files"
bound = false
+++

The ui_product .stderr files (from ~PBJ6GPZ, 94a7a76b9) were blessed on a host without the rust-src component, so they read '= note: the failure occurred here'. Where rust-src is installed (the primary checkout on 2026-10-07), rustc prints the core/src/panic.rs snippet instead and all 3 cases fail on experimental. Fix: add rust-src to rust-toolchain.toml components so every host matches, then re-bless with TRYBUILD=overwrite; check gob-macros::ui for the same skew.
