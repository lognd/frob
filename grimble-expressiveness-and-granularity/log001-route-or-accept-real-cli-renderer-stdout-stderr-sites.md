+++
id = "01M6B0TE9BTS7175N7NNEW7YYW"
title = "LOG001: route or accept real CLI renderer stdout/stderr sites (phase 3)"
type = "task"
category = "in-progress"
priority = "high"
points = 5
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-11-01T07:40:11Z"
updated = "2026-11-01T11:09:07Z"
scope = ["crates/frob/src/**,crates/gob-cli/src/**,crates/grimble/src/**,crates/gob-dev/src/**,crates/frob-evidence/src/**,crates/frob-worktree/src/**,crates/gob-log/src/**,crates/crunk/src/**,crates/crunk-tailwind/src/**", "crates/gob-cli/src/render.rs", "crates/crunk-tailwind/**", "changelog.d/01M6B0TE9BTS7175N7NNEW7YYW.changed.md", "crates/crunk-tailwind/node/helper.mjs"]

[[acceptance]]
text = "Every remaining Rust LOG001 stdout/stderr site is routed through the output layer or carries a justified frob:accept; grimble check --only LOG001 reports zero Rust errors"
bound = true
+++

Real CLI renderer output (tour_cmd, trust_cmd, board_cmd, render.rs, cli.rs, explain.rs, serve_mcp, presence, verbs, review, init).
