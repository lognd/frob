+++
id = "01M4GKD8WNG2NW2VAR1MBP382J"
title = "DOC001 partial markdown parse is reported at 1:1 without the line that failed (unescaped | in a code span in a table row)"
type = "bug"
category = "in-progress"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-10-09T15:09:51Z"
updated = "2026-10-10T20:54:37Z"
labels = ["adoption:logand-app"]
scope = ["crates/gob-text/**", "crates/frob-obligations/**", "changelog.d/**", "crates/gob-check/**", "crates/frob-check/**"]

[[acceptance]]
text = "Given a markdown table row with an unescaped | inside a code span, when DOC001 reports a partial parse, then the finding points at that line and names the likely cause"
bound = false
+++

logand.app-v2 F-557.
