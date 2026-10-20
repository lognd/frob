+++
id = "01M5CY4615SPGHB682NX2S3S24"
title = "frob work, CI and goway with_refs must handle the ticket branch"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-20T15:15:51Z"
updated = "2026-10-20T16:10:44Z"
scope = ["crates/frob-ledger/src/branch.rs", "crates/frob-worktree/src/verbs.rs", "crates/frob-worktree/tests/work.rs", ".github/workflows/ci.yml", ".github/scripts/ensure-ledger-refs.sh", "crates/frob/tests/it/ticket_branch_refs.rs", "docs/design/distributed-tickets.md", "docs/guides/ticket-branch.md", "crates/frob/tests/it/main.rs"]

[[acceptance]]
text = "Given orphan mode, when frob work runs, then the worktree branches from the code ref and the transition lands on the ticket branch"
bound = true

[[acceptance]]
text = "Given a fresh clone with no local ticket branch, when frob work runs, then it adopts origin's ticket branch and succeeds"
bound = true

[[acceptance]]
text = "Given orphan mode, when goway.toml lacks the ticket-branch with_refs, then a guard test fails"
bound = true
+++

found while working ~P418XYE
