+++
id = "01M703GDFMCNA4M7VW8F4JHJHX"
title = "Grimble LOG: Bash adapter must record call sites so U can witness LOG001"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 3
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-11-09T12:11:11Z"
updated = "2026-11-14T21:06:22Z"
labels = ["no-story"]
scope = ["crates/gob-symbols/src/shell*.rs"]

[[acceptance]]
text = "The shell adapter records one call site per uncaptured plain-word command, so the U witness reports Bash calls"
bound = true
+++

found while working ~MV8PWVD: extract_file yields no calls or uses for shell
