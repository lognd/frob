+++
id = "01M55NRVBCXZGRBWP0RG3SK7JG"
title = "crunk: LAYER001 underscore integers and golden provenance note"
type = "chore"
category = "in-progress"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-10-17T19:35:10Z"
updated = "2026-11-02T11:48:44Z"
idempotency_key = "crunk-cmp-layer-golden"
labels = ["area:crunk"]
scope = ["crates/crunk-rules/**", "crates/crunk-ingest/**", "crates/crunk-ingest/tests/fixtures/tailwind/**"]

[[acceptance]]
text = "Given layer 1_0, when LAYER001 runs, then it parses as 10"
bound = true

[[acceptance]]
text = "Given the tailwind fixtures, when read, then a note states the golden is Rust-authored"
bound = true
+++

Python int() accepts underscores (1_0) in LAYER001. Also record in tests/fixtures/tailwind that the tailwind_v4.theme.json golden was hand-authored on the Rust side, not a Python output.
