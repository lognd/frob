+++
id = "01M65SN5N5EZ50ZG7JKQE2X637"
title = "CAP: Rust cross-file, macro_use and macro_export macros are not followed"
type = "bug"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-30T06:58:46Z"
updated = "2026-10-30T06:58:46Z"
scope = ["crates/grimble-bind/**", "crates/gob-symbols/**"]
+++

found while working ~D37NDVN: macro_rules is expanded only within its own file.
