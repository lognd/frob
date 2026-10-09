+++
id = "01M4FG5RCDA668CK81QT54E67N"
title = "The opaque-files notice is repeated as an unresolved finding once per rule; emit it once per run"
type = "bug"
category = "todo"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-10-09T04:54:04Z"
updated = "2026-10-09T04:54:04Z"
labels = ["adoption:logand-app"]
scope = ["crates/gob-check/**", "crates/frob-check/**", "changelog.d/**"]

[[acceptance]]
text = "Given 59 opaque text files, when frob check runs, then one unresolved notice names the count and the rules that could not read them, instead of one finding per rule"
bound = false
+++

logand.app-v2 F-506.
