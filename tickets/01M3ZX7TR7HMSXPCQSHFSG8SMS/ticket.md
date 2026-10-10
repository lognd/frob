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
updated = "2026-10-10T15:59:33Z"
idempotency_key = "m2-sec-state-tracked"
labels = ["milestone:2", "area:security", "creates:crates/gob-trust/tests/guard.rs", "creates:crates/gob-trust/src/guard.rs"]
scope = ["crates/gob-diagnostics/src/refusal.rs", "crates/gob-trust/src/lib.rs", "crates/gob-trust/src/error.rs", "docs/design/security.md", "crates/gob-trust/tests/guard.rs", "crates/gob-trust/src/guard.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7J6SES21T3KC4WESVR7H"

[[acceptance]]
text = "Given a git repository that tracks .frob/cache.sqlite, when gob_trust::check_state_untracked runs, then it returns StateTracked naming .frob/cache.sqlite, and files under .grimble/ and .crunk/ are named too"
bound = false

[[acceptance]]
text = "Given that error, when converted by Refusal::state_tracked, then the code is E-STATE-TRACKED, the class is guard-needs-action, the exit code is 3 and the message names every tracked file"
bound = false

[[acceptance]]
text = "Given state directories that are untracked or git-ignored, or a directory that is not a git repository, when check_state_untracked runs, then it returns Ok"
bound = false
+++

Implements security.md sections 2.2 and 4.

If git tracks anything under .frob/, .grimble/ or .crunk/, the run refuses with exit 3 and names the files.
