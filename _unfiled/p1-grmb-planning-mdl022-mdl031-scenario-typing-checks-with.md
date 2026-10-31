+++
id = "01M68ZBTAPEHG2FJW68JEDTNX2"
title = "P1 grmb planning: MDL022-MDL031 scenario typing checks with plan corpus"
type = "task"
category = "todo"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-10-31T12:36:14Z"
updated = "2026-10-31T12:36:14Z"
scope = ["crates/grimble-model/src/{check,rules/**}", "crates/grimble-model/tests/corpus/plan/**", "docs/design/rules.md"]

[[acceptance]]
text = "each of MDL022-MDL031 has a firing and a clean corpus case under tests/corpus/plan/"
bound = false
+++

Split from ~VKN98M6. Implement MDL022-MDL031 per grmb-planning 5 and 7.1 (MDL028 Warn, rest Error), rule .rs/.md pairs, rules.md range note. Needs the planning parser.
