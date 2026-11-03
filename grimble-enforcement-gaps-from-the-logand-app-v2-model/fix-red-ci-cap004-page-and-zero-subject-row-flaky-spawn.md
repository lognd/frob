+++
id = "01M6G8WZY2SBVS9M1CMJCN684Y"
title = "Fix red CI: CAP004 page and zero-subject row, flaky spawn_detached test"
type = "bug"
category = "todo"
priority = "high"
parent = "01M4FGWBHH3K9F2PPFYRGQ353T"
reporter = "lognd"
created = "2026-11-03T08:37:35Z"
updated = "2026-11-03T08:37:35Z"
scope = ["crates/grimble/src/explain_cmd.rs", "crates/grimble-bind/src/**", "crates/gob-exec/tests/runner.rs", "changelog.d/**"]
+++

Two deterministic test failures plus one timing flake on experimental CI.
