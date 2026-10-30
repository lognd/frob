+++
id = "01M65SN5QPZ3G7NGQHRDWAZN8N"
title = "CAP: Rust local glob imports do not resolve bare names"
type = "bug"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-30T06:58:46Z"
updated = "2026-10-30T06:58:46Z"
scope = ["crates/grimble-bind/**", "crates/gob-symbols/**"]
+++

found while working ~D37NDVN: use w::*; Cmd::new() is only unproven, not resolved.
