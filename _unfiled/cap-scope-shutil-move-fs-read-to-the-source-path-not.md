+++
id = "01M7K4BGAK2EWZVBFF18SDN3JW"
title = "CAP: scope shutil.move fs.read to the source path, not unscoped"
type = "bug"
category = "in-progress"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-16T21:31:33Z"
updated = "2026-11-17T02:41:19Z"
idempotency_key = "shutil-move-read-scope"
scope = ["crates/grimble-bind/src/caps.rs"]

[[acceptance]]
text = "shutil.move scopes fs.read to the source path, positional or keyword"
bound = true
+++
