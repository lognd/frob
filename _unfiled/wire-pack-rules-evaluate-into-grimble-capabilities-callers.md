+++
id = "01M5A56QBF8SQBSZ5QSSZ6F835"
title = "Wire pack_rules::evaluate into grimble-capabilities callers and index PACK rules in the generated rules index"
type = "task"
category = "in-progress"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-19T13:21:51Z"
updated = "2026-11-02T13:48:08Z"
scope = ["crates/grimble-check/**", "changelog.d/01M5A56QBF8SQBSZ5QSSZ6F835.fixed.md", "docs/reference/config/frob.md", "docs/schemas/config.json"]

[[acceptance]]
text = "grimble check reports PACK006 for an unreadable enabled pack file and PACK005 for a malformed one, and neither for a good pack"
bound = true
+++
