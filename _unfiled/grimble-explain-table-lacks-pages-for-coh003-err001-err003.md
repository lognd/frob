+++
id = "01M5MDT7Z1XX8K9EWBK4ARF255"
title = "grimble explain table lacks pages for COH003, ERR001-ERR003, RES001, SYS006 (lib test explain_cmd the_table_covers_every_generated_page fails)"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-10-23T13:04:44Z"
updated = "2026-10-23T13:38:54Z"
scope = ["crates/grimble/src/explain_cmd.rs", "changelog.d/**", "docs/reference/config.md", "docs/schemas/config.json"]

[[acceptance]]
text = "Given the generated rule pages, when the explain table test runs, then it passes and covers COH003, ERR001-ERR003, RES001 and SYS006"
bound = true
+++
