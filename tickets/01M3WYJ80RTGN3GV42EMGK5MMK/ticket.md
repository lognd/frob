+++
id = "01M3WYJ80RTGN3GV42EMGK5MMK"
title = "frob-land: synchronous land with preconditions, dry-run, close on land"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 8
parent = "01M3WYJ802ZVWE6E3050EVRCSV"
reporter = "agent"
created = "2026-10-02T00:00:00Z"
updated = "2026-10-02T00:00:03Z"
aliases = ["T-0024"]
labels = ["milestone:2.0.0", "component:frob-land"]
scope = ["crates/frob-land/**", "crates/frob/**", "docs/reference/**"]

[[links]]
kind = "blocked-by"
target = "01M3WYJ80KZFWBMZRGS901RTA2"

[[links]]
kind = "blocked-by"
target = "01M3WYJ80QWTM5QKG7HNGE3P2T"

[[acceptance]]
text = "Given a worked ticket with green check and evidence, when frob land runs, then the base branch contains the work, the ticket is done with an outcome, the lease is gone, and the ledger commit is on the ledger ref"
bound = false

[[acceptance]]
text = "Given a red check, when frob land runs, then exit is 3, the remedy names frob check --ticket, and nothing moved"
bound = false
+++

Implement crates/frob-land per tickets.md section 10 as updated by D23 and D25. frob land [<ticket>] [--dry-run] [--push] [--wait <secs>]: preconditions (ticket in-progress and leased by this worktree, worktree clean, base merged, frob check --ticket green at the configured fail_on, evidence present), take the land lock in the git common dir (--wait bounds acquisition only), fast-forward or merge the ticket branch onto the base branch in the primary (gob-git; spawn fallback on conflicts), write the land event and close the ticket with outcome through the ledger ref, release the lease, optionally remove the worktree, optionally push. --dry-run prints the plan as a list of steps with a plan digest. Exit codes per the cli.md table (refused preconditions exit 3 with remedy, non-retryable where retrying cannot help). Everything synchronous; no job ids. Integration test lands a ticket end to end in a temp repo.
