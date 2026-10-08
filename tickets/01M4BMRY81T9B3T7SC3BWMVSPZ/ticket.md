+++
id = "01M4BMRY81T9B3T7SC3BWMVSPZ"
title = "land exits 4 E-GIT-REV cannot resolve experimental after a successful close"
type = "bug"
category = "in-progress"
priority = "high"
points = 2
reporter = "lognd"
created = "2026-10-07T16:57:30Z"
updated = "2026-10-08T04:15:57Z"
idempotency_key = "land-post-close-git-rev"
labels = ["milestone:2"]
scope = ["crates/frob-land/**"]

[[acceptance]]
text = "Given a land that merges, checks and closes successfully, when the post-close steps run, then the exit code is 0 and no E-INTERNAL is printed (regression test reproducing the sequence)"
bound = true
+++

2026-10-07 16:54: frob land ~YR7MCXF printed closed: true, outcome: done, then error[E-INTERNAL]: E-GIT-REV: cannot resolve experimental: couldn't parse revision "experimental", exit 4. Afterwards experimental resolved fine and the worktree was removed. A second land (~9VT321D) had finished minutes earlier in the same primary. Find which post-close step resolves the base by a bare name (possibly from inside the removed worktree or with a stale repo handle) and fix it; a land that succeeded must not exit non-zero.
