+++
id = "01M4Z1KTKEVF53GWM6ZN7PFN4Q"
title = "Land train: batch ready tickets into one rolled-up candidate, check once, bisect (group testing) on failure"
type = "epic"
category = "todo"
priority = "high"
points = 8
reporter = "lognd"
created = "2026-10-15T05:47:28Z"
updated = "2026-10-15T05:47:28Z"
idempotency_key = "land-train-batch"
labels = ["area:land"]

[[acceptance]]
text = "Given 12 ready tickets with one failing, when the train runs, then the 11 good tickets land and the culprit is isolated in at most 2*ceil(log2 12) candidate checks"
bound = false

[[acceptance]]
text = "Given a batch of green tickets, when the train runs, then exactly one check runs and all tickets close in one ledger commit"
bound = false

[[acceptance]]
text = "Given a textual conflict between two branches, when the candidate is built, then the later one stays queued and the rest proceed"
bound = false
+++

Concurrent lands each re-run the check serially under the land lock (4 concurrent lands: 6-52 min each). Replace with a train: (1) lands enqueue (ledger-only guards first, ~Y7E721R); (2) the train driver takes every ready ticket branch, merges them in priority order into one candidate on a temp branch off base (skip any that conflict textually; they stay queued); (3) runs ONE affected-cone check + bound evidence over the union (build-test-ci.md fast-lands cone, union of cones), shared target dir; (4) green: fast-forward base to the candidate, close all tickets in one ledger commit; (5) red: group-testing bisection - split the batch in halves, test each half as its own candidate (halves in parallel, goway shards), recurse until the culprit ticket(s) are isolated; innocent halves land immediately, culprit returns to its agent with the failing evidence (Uber SubmitQueue, Keeping Master Green EuroSys 2019). Adaptive batch size: grow after green trains, halve after red, cap by RAM. Optional speculative: pre-build candidates N+1 while N checks. Interactions: lease scope disjointness already guarantees few conflicts; same-file shared tickets split into separate trains; require_base_green and CI stay as post-merge net; keep single-ticket frob land as fallback. Write design in docs/design/build-test-ci.md (new section), schema for train state in .git/frob/train, verbs frob land --train / frob train status|run|drain, logging per stage, tests with a fake runner proving bisection finds 1 and 2 culprits in a batch of 12 in <= ceil(log2) + k rounds.
