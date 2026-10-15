+++
id = "01M4Z1MYPEJ6HDVBJVPDVHR8MA"
title = "Land train: candidate builder merging ticket branches into a temp branch, skipping conflicts"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 5
parent = "01M4Z1KTKEVF53GWM6ZN7PFN4Q"
reporter = "lognd"
created = "2026-10-15T05:48:05Z"
updated = "2026-10-15T12:32:21Z"
idempotency_key = "train-candidate"
labels = ["area:land", "creates:crates/frob-land/src/candidate.rs"]
scope = ["crates/frob-land/src/git.rs", "crates/frob-land/src/candidate.rs", "crates/frob-land/src/lib.rs"]

[[acceptance]]
text = "Given a textual conflict between two branches, when the candidate is built, then the later one is skipped and the rest are merged"
bound = true

[[acceptance]]
text = "Given tickets with overlapping lease scopes, then they are placed in separate trains"
bound = true

[[acceptance]]
text = "Given any failure, then no temp ref is left behind"
bound = true
+++

Given base oid and ordered ticket branches, build a candidate on a temp ref (refs/frob/train/<id>) off base by sequential merge (octopus when all scopes are disjoint, else sequential). A textual conflict skips that ticket, it stays queued, and the merge is aborted cleanly. Same-file shared-scope tickets are split into separate trains. Returns candidate oid, merged list, skipped list with reasons. Temp refs removed on drop/failure. Log each merge and skip.
