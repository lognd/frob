+++
id = "01M61Y35DTKGERGNVE1SPT1F4A"
title = "CAP: resolve symlinks when judging path grant arguments"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-28T18:59:21Z"
updated = "2026-10-29T23:58:44Z"
scope = ["crates/grimble-model/src/args.rs", "crates/grimble-model/Cargo.toml", "Cargo.lock"]

[[acceptance]]
text = "path comparison accounts for symlinks"
bound = true
+++

found while working ~5X9CAQE: path comparison accounts for symlinks
