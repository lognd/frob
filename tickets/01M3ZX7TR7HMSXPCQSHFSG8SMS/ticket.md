+++
id = "01M3ZX7TR7HMSXPCQSHFSG8SMS"
title = "E-STATE-TRACKED guard: refuse when git tracks a state or cache directory"
type = "task"
category = "in-progress"
priority = "high"
points = 2
parent = "01M3ZX76WPYZQ4Q5WDQ72AWMZQ"
reporter = "lognd"
created = "2026-10-03T03:34:33Z"
updated = "2026-10-10T15:59:24Z"
idempotency_key = "m2-sec-state-tracked"
labels = ["milestone:2", "area:security"]
scope = ["crates/gob-trust/src/guard.rs", "crates/gob-diagnostics/src/refusal.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7J6SES21T3KC4WESVR7H"

[[acceptance]]
text = "Given a repository that tracks .frob/cache.sqlite, when any check runs, then it exits 3 with E-STATE-TRACKED naming the file"
bound = false

[[acceptance]]
text = "Given untracked or ignored state directories, when a check runs, then it proceeds normally"
bound = false
+++

Implements security.md sections 2.2 and 4.

If git tracks anything under .frob/, .grimble/ or .crunk/, the run refuses with exit 3 and names the files.
