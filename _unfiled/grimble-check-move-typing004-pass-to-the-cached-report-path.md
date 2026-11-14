+++
id = "01M7E7HY77XT967FTS81EC8WTX"
title = "grimble-check: move TYPING004 pass to the cached report path"
type = "task"
category = "todo"
priority = "low"
reporter = "lognd"
created = "2026-11-14T23:51:17Z"
updated = "2026-11-14T23:51:17Z"
scope = ["crates/grimble-check/**"]
+++

TYPING004 (BMAZEDQ) is wired into grimble-check minimally: typing_report runs uncached each run (product.rs). Move it into the cached reports() tuple with a report_cache key (typing-v1) like res/err, and add a grimble-check integration test like tests/it/res_rules.rs.
