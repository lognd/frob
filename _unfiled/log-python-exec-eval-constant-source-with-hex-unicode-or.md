+++
id = "01M65FKMFTM3TH0MVPXSRWVHSN"
title = "LOG: Python exec/eval constant source with hex, unicode or octal escapes is unresolved"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-30T04:03:10Z"
updated = "2026-11-17T07:00:41Z"
labels = ["no-story"]
scope = ["crates/grimble-check/src/log/**", "docs/design/grimble/output-atoms.md", "crates/grimble-check/tests/**"]

[[acceptance]]
text = "Given Python exec/eval with a constant source using hex, unicode or octal escapes, when scanned, then the source is decoded and scanned; malformed escapes stay unresolved"
bound = true
+++

found while working 01M64230T88F77RTBYS9M3CY3C: unescape handles only simple escapes.
