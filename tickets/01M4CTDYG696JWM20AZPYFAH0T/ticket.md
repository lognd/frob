+++
id = "01M4CTDYG696JWM20AZPYFAH0T"
title = "gob-exec: kill the whole process tree on timeout (Windows job object, unix process group) and bound the post-kill join (audit M2)"
type = "task"
category = "in-progress"
priority = "high"
points = 3
parent = "01M4CTDVKQVPSY0SF4XTNT2Q1E"
reporter = "lognd"
created = "2026-10-08T03:55:35Z"
updated = "2026-10-10T15:17:05Z"
scope = ["changelog.d/**", "crates/gob-exec/**"]

[[acceptance]]
text = "Given a command that spawns a grandchild sleeping past the timeout, when the timeout fires, then both are killed and run returns within timeout plus 2 s on Linux and Windows"
bound = false
+++

notes/review/audit-2026-10-07.md M2, gob-exec/src/runner.rs 270. Only the direct child is killed and output read blocks on grandchildren holding the pipe, so timeouts do not hold on Windows or for setsid children.
