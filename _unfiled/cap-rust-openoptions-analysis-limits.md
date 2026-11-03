+++
id = "01M6607PTFF13C9TGEJA83XCBZ"
title = "CAP: Rust OpenOptions analysis limits"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-30T08:53:45Z"
updated = "2026-11-03T05:56:40Z"
labels = ["no-story"]
scope = ["crates/grimble-bind/src/caps.rs", "crates/grimble-bind/src/caps/**"]
+++

found while working ~MM08TTF: flags after .open(), bool consts not folded, per-use reparse
