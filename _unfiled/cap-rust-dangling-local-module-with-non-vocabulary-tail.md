+++
id = "01M65SN5STWJNBDGY0WQW4BYJP"
title = "CAP: Rust dangling local module with non-vocabulary tail yields no finding"
type = "bug"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-30T06:58:46Z"
updated = "2026-10-30T06:58:46Z"
scope = ["crates/grimble-bind/**", "crates/gob-symbols/**"]
+++

found while working ~D37NDVN: a missing mod w; file whose tail does not match vocabulary reports nothing.
