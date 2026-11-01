+++
id = "01M6A82237VHE76NKB9B9CJAC6"
title = "caps test key_path breaks on Windows (backslash in Python literal)"
type = "bug"
category = "in-progress"
priority = "high"
points = 1
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-11-01T00:27:26Z"
updated = "2026-11-01T01:58:30Z"
idempotency_key = "caps-keypath-windows-2026-10-31"
scope = ["crates/grimble-bind/tests/caps.rs"]

[[acceptance]]
text = "arg_scope_a_read_outside_every_granted_path_is_cap001_naming_both passes on Windows: key_path uses a forward slash root, not MAIN_SEPARATOR"
bound = true
+++

CI run 41251789959 windows: key_path() yields backslash-home which is an invalid escape inside the generated Python literal, so the use is Unresolved not Error. Use '/' as the root char.
