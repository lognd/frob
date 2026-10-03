+++
id = "01M4069YW2EF551WF2J7R0EMJ4"
title = "frob init on a fresh repository: end-to-end loop test"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 5
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-03T06:13:00Z"
updated = "2026-10-03T09:06:12Z"
idempotency_key = "m2-rel-init-e2e"
labels = ["milestone:2", "area:release", "release:0.532.0"]
scope = ["crates/frob/tests/e2e_init_loop.rs"]

[[links]]
kind = "blocked-by"
target = "01M3WYJ81430D3D5QSNCFM8QB0"

[[links]]
kind = "blocked-by"
target = "01M3Z71361PCFXV5VKSACRF17G"

[[acceptance]]
text = "Given an empty git repository, when the whole loop runs, then land closes the ticket and the base branch holds the change"
bound = true

[[acceptance]]
text = "Given the ledger after land, when ticket show runs, then it shows evidence bound to the acceptance"
bound = true
+++

A test that creates an empty git repository in a temp dir (no remote), runs frob init, ticket new with acceptance and scope, work, edits a file, check, test, evidence, close guards, and land onto the base branch, asserting every step's exit code and the final ledger. Any gap found becomes a filed ticket labelled release:0.532.0, not a skipped assertion.
