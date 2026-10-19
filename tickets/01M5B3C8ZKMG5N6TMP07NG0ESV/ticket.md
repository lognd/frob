+++
id = "01M5B3C8ZKMG5N6TMP07NG0ESV"
title = "frob-obligations collect() skips no-grammar files; register PARSE002 in explain and grimble-check"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-19T22:09:11Z"
updated = "2026-10-19T23:18:53Z"
scope = ["crates/frob-obligations/src/collect.rs", "crates/frob/src/explain_cmd.rs", "crates/grimble-check/src/product.rs"]
+++

found while working ~GCNECVB: collect.rs:98 skips Language::detect==None files; use Scanner::scan_unparsed_in. Add PARSE002 to rule_pages! in explain_cmd.rs and DIRECTIVE_RULES in grimble-check product.rs. Separately TICK010 lacks an unresolved coverage case (rule_coverage fails pre-existing).
