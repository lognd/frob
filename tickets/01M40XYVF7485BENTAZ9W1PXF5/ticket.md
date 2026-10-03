+++
id = "01M40XYVF7485BENTAZ9W1PXF5"
title = "Remaining raw-text readers pair raw offsets with git-normalized cache keys"
type = "task"
category = "todo"
priority = "low"
points = 2
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-03T13:06:22Z"
updated = "2026-10-03T13:06:22Z"
idempotency_key = "m2-raw-readers-normalized"
labels = ["milestone:2"]
scope = ["crates/gob-check/**", "crates/frob-obligations/**", "crates/frob-check/src/snapshot.rs", "crates/gob-walk/**"]

[[acceptance]]
text = "Given core.autocrlf toggled with unchanged content, when check runs twice, then findings and their spans are identical"
bound = false
+++

From ~M4T7MXR: gob-check filecheck.rs, frob-obligations collect.rs and lib.rs, and frob-check snapshot.rs still read raw worktree text for per-file rules and display while cache keys are now over git-normalized content; a mismatch is possible only when core.autocrlf or .gitattributes changes and content does not. Route them through gob-walk's ContentReader (or key their cache entries on raw digests) so offsets and keys always agree; also measure the walk stage in release (it went from 65 ms to about 240 ms in debug after normalization) and keep the warm path within budget.
