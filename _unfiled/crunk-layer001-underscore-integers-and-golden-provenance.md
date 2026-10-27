+++
id = "01M55NRVBCXZGRBWP0RG3SK7JG"
title = "crunk: LAYER001 underscore integers and golden provenance note"
type = "chore"
category = "todo"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-10-17T19:35:10Z"
updated = "2026-10-27T02:58:21Z"
idempotency_key = "crunk-cmp-layer-golden"
labels = ["area:crunk"]
scope = ["crates/crunk-rules/**", "crates/crunk-ingest/**"]

[[acceptance]]
text = "Given layer 1_0, when LAYER001 runs, then it parses as 10"
bound = false

[[acceptance]]
text = "Given the tailwind fixtures, when read, then a note states the golden is Rust-authored"
bound = false
+++

Python int() accepts underscores (1_0) in LAYER001. Also record in tests/fixtures/tailwind that the tailwind_v4.theme.json golden was hand-authored on the Rust side, not a Python output.
