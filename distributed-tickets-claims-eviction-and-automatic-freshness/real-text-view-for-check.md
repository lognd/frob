+++
id = "01M5EFE42EH8JYYRC0JXSZR52F"
title = "Real --text view for check"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 3
parent = "01M5CVZND2H3YDDB67WZ7ANRQY"
reporter = "lognd"
created = "2026-10-21T05:37:37Z"
updated = "2026-10-21T07:41:05Z"
scope = ["crates/frob/src/product.rs", "crates/frob/src/lib.rs", "crates/frob/src/check_view.rs", "changelog.d/01M5EFE42EH8JYYRC0JXSZR52F.changed.md"]

[[acceptance]]
text = "frob check --text prints a verdict line, the findings, and Fix/Timing/Notes sections instead of the generic key dump; JSON output is unchanged"
bound = true
+++

Split from ~5JDQ45M: the remaining everyday verbs still fall back to the generic key dump under --text. Reuse crates/frob/src/text_view.rs table helper.
