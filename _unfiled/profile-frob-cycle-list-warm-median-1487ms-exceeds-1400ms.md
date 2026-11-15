+++
id = "01M7GHZ9QXWMQ4EF945Q7KZZT6"
title = "profile: frob cycle list warm median 1487ms exceeds 1400ms budget in CI"
type = "bug"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-15T21:31:50Z"
updated = "2026-11-15T21:31:50Z"
scope = ["crates/gob-dev/profile.toml"]

[[acceptance]]
text = "frob cycle list stays within its profile budget on the CI runner, by speeding it up or justifying a raised budget"
bound = false
+++

CI run on 64e2aa59f2 profile job: warm median 1487 ms vs budget 1400 ms (700 x 2). Likely runner noise but cycle list reads the whole ledger; investigate before raising the budget.
