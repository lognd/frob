+++
id = "01M5XCVMQBQWARH7HT8RYHA0KY"
title = "crunk export css|tailwind|uss|csharp|dtcg verb over the token exporters"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M4CXQTERP5YASZGVEAH6KG4H"
reporter = "lognd"
created = "2026-10-27T00:41:11Z"
updated = "2026-10-27T01:11:52Z"
labels = ["area:crunk"]
scope = ["crates/crunk/src/export.rs", "crates/crunk/src/lib.rs", "crates/crunk/tests/export_verb.rs", "crates/crunk/src/tokens.rs", "docs/**", "crates/gob-cli/src/cli.rs"]

[[acceptance]]
text = "Given a token source, when crunk export uss runs, then the USS sheet is printed or written and the verb exits 0; given an unknown target, then it exits 2 naming the valid targets"
bound = true
+++

Design crunk.md section 5 interop row. Add a thin export verb over crunk_tokens::export::Target (same code path as tokens --target; no duplicated rendering). dtcg delegates to the existing ExportDtcg.
