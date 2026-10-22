+++
id = "01M5H3RXZHDEDM508R6K4DBBVJ"
title = "crunk extract-token: non-color literals (lengths, durations)"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-22T06:11:32Z"
updated = "2026-10-22T20:55:29Z"
scope = ["crates/crunk/src/extract.rs", "crates/crunk/tests/extract.rs", "docs/crunk/README.md", "docs/reference/cli/crunk.md"]

[[acceptance]]
text = "Given a length literal, when crunk extract-token runs, then it is promoted to a token and references rewritten"
bound = true

[[acceptance]]
text = "Given a duration literal, when crunk extract-token runs, then it is promoted likewise"
bound = false
+++

Found while working ~PAN1YXT: extract-token only promotes hex colors; other literals are refused with E-EXTRACT-LITERAL.
