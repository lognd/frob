+++
id = "01M4HW9J243ZJRMVYW51K18GCM"
title = "ticket update --add-scope (and lease widen) take --wait SECS to wait for an overlapping lease instead of failing"
type = "story"
category = "todo"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-10-10T03:04:21Z"
updated = "2026-10-10T03:04:21Z"
labels = ["adoption:logand-app"]
scope = ["crates/frob/src/ticket/**", "crates/frob-lease/src/**", "changelog.d/**"]

[[acceptance]]
text = "Given --add-scope naming a file another lease holds, when run with --wait 600, then it waits (bounded, reporting the holder) and succeeds when the holder releases"
bound = false
+++

logand.app-v2 F-578: a docs-file lease blocked a 2-character fix for ~20 minutes.
