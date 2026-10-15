+++
id = "01M4Z1ND9ZM2NPAFJBF67JHDV6"
title = "Land train: driver and verbs (frob land --train, frob train status|run|drain)"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 5
parent = "01M4Z1KTKEVF53GWM6ZN7PFN4Q"
reporter = "lognd"
created = "2026-10-15T05:48:20Z"
updated = "2026-10-15T22:35:14Z"
idempotency_key = "train-driver"
labels = ["area:land"]
scope = ["crates/frob-land/src/train.rs", "crates/frob-land/src/verb.rs", "crates/frob/src/**", "crates/frob-land/src/lib.rs", "tests/**", "docs/reference/**", "docs/design/cli.md", "crates/frob-land/src/land.rs", "crates/frob-land/src/base_ci.rs", "crates/frob-land/src/plan.rs", "crates/frob-land/tests/land.rs", "docs/design/build-test-ci.md", "crates/frob-land/src/train_state.rs", "docs/schemas/**"]

[[links]]
kind = "blocked-by"
target = "01M4Z1MYF3JKB73KCCX5BPJ7WJ"

[[links]]
kind = "blocked-by"
target = "01M4Z1MYJSZJ8CMH8NEA8K30K4"

[[links]]
kind = "blocked-by"
target = "01M4Z1MYPEJ6HDVBJVPDVHR8MA"

[[links]]
kind = "blocked-by"
target = "01M4Z1MYSTFADV8FJM8SEXKGZ7"

[[links]]
kind = "blocked-by"
target = "01M4Z1MYXBWTWH9F271FEY3NSE"

[[links]]
kind = "blocked-by"
target = "01M4Z1N93S11HX3DGGKBJF5WGP"

[[links]]
kind = "blocked-by"
target = "01M4Z1N97QX3ZBQ4HNYY7WKNCH"

[[acceptance]]
text = "Given 12 ready tickets with one failing, when the train runs, then 11 land and the culprit returns to its agent with the failing evidence"
bound = true

[[acceptance]]
text = "Given frob train status, then it reports queue, current candidate and batch size as an envelope with a schema"
bound = true

[[acceptance]]
text = "Given one ticket or the train disabled, then single-ticket frob land behaves as before"
bound = true
+++

Wire planner, batch-size controller, candidate builder and state store into the driver: take ready enqueued tickets (reuse the enqueue queue of ~3V4VKC9, done; do not duplicate), build candidate, check, close via the ledger-close slice on green, bisect on red, parallel halves via goway shards when available. Verbs: frob land --train, frob train status|run|drain with envelopes and schemas; single-ticket frob land stays as fallback; require_base_green and CI unchanged. Log per stage. Replaces prefix bisection in train.rs (~DSD1QBK, done).
