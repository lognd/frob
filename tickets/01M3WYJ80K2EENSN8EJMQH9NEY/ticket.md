+++
id = "01M3WYJ80K2EENSN8EJMQH9NEY"
title = "frob-lease + frob-worktree: locked scope leases and frob work"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 8
parent = "01M3WYJ802PGVRR55XCM9C3KV9"
reporter = "agent"
created = "2026-10-02T00:00:00Z"
updated = "2026-10-02T00:00:03Z"
aliases = ["T-0019"]
labels = ["milestone:2.0.0", "component:frob-lease"]
scope = ["crates/frob-lease/**", "crates/frob-worktree/**"]

[[links]]
kind = "blocked-by"
target = "01M3WYJ80J56GDD3VY4N8J4DJR"

[[acceptance]]
text = "Given two tickets with overlapping globs and no files yet, when both run work concurrently, then exactly one succeeds and the other gets exit 3 E-LEASE-HELD"
bound = false

[[acceptance]]
text = "Given a held lease, when the same holder runs work again, then it returns already: true with the same worktree path"
bound = false
+++

Implement crates/frob-lease and crates/frob-worktree per tickets.md section 6 as updated by D26 and audit L21. Leases live in .git/frob/leases/<ticket>.toml under one lock file .git/frob/leases.lock (fs2 or rustix flock); holder = actor plus worktree path; overlap = glob intersection (globset text analysis) OR resolved-set intersection, with [tickets] registry_files exempt; TTL knob with renewal on any frob verb from the worktree; steal with --steal --reason recorded as an event. frob work <ticket>: idempotent for the same holder (returns existing worktree and lease), refuses with E-LEASE-HELD exit 3 naming the holder otherwise; creates the worktree at the [worktree] dir knob (default ../<repo>-wt/<ticket-handle>) via gob-git (spawn fallback allowed), branch ticket/<handle>, merges the base branch, transitions the ticket to in-progress, writes the lease. Verbs: work, start, requeue (release), ticket contention. SCOPE001 rule: diff of the worktree against base touches files outside the lease (reuse gob-git diff). Tests: concurrent work calls on two overlapping tickets from two threads produce exactly one lease.
