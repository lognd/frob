+++
id = "01M5XNNK0W03EZMP1EE2NDKP55"
title = "SYS012: template excuse overlapping a may grant (spec references it, no rule exists)"
type = "task"
category = "todo"
priority = "low"
points = 2
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-10-27T03:15:10Z"
updated = "2026-10-27T03:15:10Z"
idempotency_key = "grimble-expr-sys012-2026-10-26"
labels = ["grimble", "audit:grimble-expressiveness"]
scope = ["crates/grimble-bind/src/rules/**", "crates/grimble-capabilities/src/excuse.rs"]

[[acceptance]]
text = "SYS012 fires on a template excuse that overlaps a may grant, with a firing and a clean example"
bound = false
+++

Audit report: /tmp/claude-1000/-home-logan-projects-frob/9dfed69c-963b-4123-8ee8-0030bb0775b3/scratchpad/grimble-audit.md. binding.md 7.2 item 5 says 'A template excuse that overlaps a grant may A prime is SYS012 (6.12)'; crates/grimble-bind/src/rules has no sys012. Template excuses themselves are computed but never applied (excuse.rs has no caller outside its crate); emission is ~RAD5ARW. Add SYS012 once excuses are wired.
