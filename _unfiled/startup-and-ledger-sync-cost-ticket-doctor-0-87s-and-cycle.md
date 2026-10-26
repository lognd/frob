+++
id = "01M5WC2FESEC3XRRE1PM8QMZ57"
title = "Startup and ledger-sync cost: ticket doctor 0.87s and cycle velocity 2.1s still exceed the 0.5s target"
type = "task"
category = "todo"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-10-26T15:08:12Z"
updated = "2026-10-26T15:08:12Z"
scope = ["crates/frob-ledger/**", "crates/frob-pm/**", "crates/frob-cli/**"]

[[acceptance]]
text = "frob ticket doctor and frob cycle velocity each complete in under 0.5s on this repository, measured by a recorded benchmark"
bound = false
+++

Follow-up of JD1T9DP: bulk event reads are now parallel (doctor 1.8s to 0.87s, velocity 3.8s to 2.1s). Remaining: 0.51s fixed startup/ledger sync in frob ticket doable, non-event work in cycle velocity, and the option of caching parsed done-transition facts in the index.
