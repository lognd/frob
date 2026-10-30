+++
id = "01M65SN5VWSCMDH9W4V6KM8R9S"
title = "CAP: Rust include! in macro bodies and unowned re-export files are not scanned"
type = "bug"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-30T06:58:46Z"
updated = "2026-10-30T06:58:46Z"
scope = ["crates/grimble-bind/**", "crates/gob-symbols/**"]
+++

found while working ~D37NDVN: reaching sources are scan files only; include! within macro bodies is skipped.
