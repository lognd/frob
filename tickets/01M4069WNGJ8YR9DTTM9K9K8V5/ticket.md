+++
id = "01M4069WNGJ8YR9DTTM9K9K8V5"
title = "REL002 lockstep-version-mismatch (Error)"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 2
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-03T06:12:58Z"
updated = "2026-10-03T08:15:09Z"
idempotency_key = "m2-rel-rel002"
labels = ["milestone:2", "area:release", "release:0.532.0"]
scope = ["crates/frob-release/src/rel002.rs", "docs/reference/rules/rel/**", "crates/frob-release/Cargo.toml", "crates/frob-release/src/lib.rs", "crates/frob-release/tests/**", "crates/frob-check/src/product.rs", "crates/frob-check/Cargo.toml", "docs/reference/rules/**", "Cargo.lock"]

[[links]]
kind = "blocked-by"
target = "01M4069W8ECWEPBH6YPAR7X0X0"

[[acceptance]]
text = "Given one crate with a different version, when frob check runs, then REL002 fires naming it"
bound = true

[[acceptance]]
text = "Given all equal, when frob check runs, then REL002 is silent"
bound = true
+++

Reads the workspace Cargo.toml and every member's effective version (and the PyPI wheel metadata file) and fires when they differ; the fix remedy names `frob release cut`.
