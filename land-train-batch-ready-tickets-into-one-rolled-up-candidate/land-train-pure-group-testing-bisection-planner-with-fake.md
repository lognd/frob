+++
id = "01M4Z1MYF3JKB73KCCX5BPJ7WJ"
title = "Land train: pure group-testing bisection planner with fake-runner tests"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 3
parent = "01M4Z1KTKEVF53GWM6ZN7PFN4Q"
reporter = "lognd"
created = "2026-10-15T05:48:04Z"
updated = "2026-10-15T11:19:44Z"
idempotency_key = "train-bisect"
labels = ["area:land", "creates:crates/frob-land/src/bisect.rs"]
scope = ["crates/frob-land/src/bisect.rs", "crates/frob-land/src/lib.rs"]

[[acceptance]]
text = "Given a batch of 12 with 1 failing and a fake runner, then the 11 good tickets are landable and the culprit is isolated in at most 8 checks"
bound = true

[[acceptance]]
text = "Given a batch of 12 with 2 failing, then both culprits are isolated within 12 checks"
bound = true

[[acceptance]]
text = "Given an all-green batch, then exactly one check runs"
bound = true

[[acceptance]]
text = "Given a red parent whose parts are all green, then the planner reports an interaction, blames nobody and does not loop"
bound = true

[[acceptance]]
text = "Given an A+C interaction plus an independent culprit D, then the landable set is a set that was checked whole"
bound = true

[[acceptance]]
text = "Given a runner fault, then it is retried once and a second fault blames no ticket and reports the rest as unchecked"
bound = true
+++

Pure module, no git or IO. Input: ordered batch of ticket handles and a Runner trait (check(subset)->Green|Red(evidence)). Output: landable set, culprit set, round count. Split red batch in halves, test halves (parallelizable: expose the two sibling checks as one round), recurse; a green half lands, a singleton red is a culprit; if both halves green after a red parent (flaky or interaction) mark the pair interacting and test sequential prefixes. Supersedes the prefix-only bisection in train.rs (~DSD1QBK, done). Log every round at info.
