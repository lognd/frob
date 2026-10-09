+++
id = "01M4GK4M8KKRE7X7JCP6YJ5K96"
title = "A leftover v1 frob.lock aborts frob check with E-CHECK-LOCK without naming the file or saying it is a v1 artifact"
type = "bug"
category = "todo"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-10-09T15:05:08Z"
updated = "2026-10-09T15:05:08Z"
labels = ["adoption:logand-app"]
scope = ["crates/gob-lock/**", "crates/frob-check/**", "changelog.d/**"]

[[acceptance]]
text = "Given a v1-format frob.lock, when frob check runs, then the error names the file, says it is a v1 lock and gives the remedy (delete it and run frob ack)"
bound = false
+++

logand.app-v2 F-548.
