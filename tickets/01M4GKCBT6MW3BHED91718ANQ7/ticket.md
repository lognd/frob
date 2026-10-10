+++
id = "01M4GKCBT6MW3BHED91718ANQ7"
title = "TOOL001 quotes a noisy INFO stderr line instead of the error; pick the excerpt from error-looking lines and the tail"
type = "bug"
category = "in-progress"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-09T15:09:21Z"
updated = "2026-10-10T20:18:16Z"
labels = ["adoption:logand-app"]
scope = ["crates/gob-check/**", "crates/gob-exec/**", "changelog.d/**"]

[[acceptance]]
text = "Given a tool that logs INFO lines then fails with an error line, when TOOL001 fires, then its excerpt shows the error line(s) and the last lines of stderr, not the first INFO line"
bound = false
+++

logand.app-v2 F-554 (the missing findings array on a failed gate is ~Y6GKQPS).
