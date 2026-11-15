+++
id = "01M7E7HY77XT967FTS81EC8WTX"
title = "grimble-check: move TYPING004 pass to the cached report path"
type = "task"
category = "todo"
priority = "low"
points = 2
reporter = "lognd"
created = "2026-11-14T23:51:17Z"
updated = "2026-11-15T01:12:33Z"
scope = ["crates/grimble-check/**"]

[[acceptance]]
text = "Given grimble-check runs twice on an unchanged tree, then TYPING004 findings come from the report cache and match the uncached run; an integration test like res_rules.rs covers it"
bound = false
+++

TYPING004 (BMAZEDQ) is wired into grimble-check minimally: typing_report runs uncached each run (product.rs). Move it into the cached reports() tuple with a report_cache key (typing-v1) like res/err, and add a grimble-check integration test like tests/it/res_rules.rs.
