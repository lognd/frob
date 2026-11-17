+++
id = "01M7KME88Y8N7JD506Y0WRG2MX"
title = "BASE001/BASE002: product BaselineHost, baseline inputs, and shared prune helpers"
type = "task"
category = "in-progress"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-11-17T02:12:40Z"
updated = "2026-11-17T02:51:40Z"
idempotency_key = "split-8az7dkd-host"

[[acceptance]]
text = "Given a repo with frob-baseline.toml, when frob check runs, then BASE001 (vs [check] base file, silent when absent) and BASE002 (ticket liveness; missing ledger ticket is Unknown) fire; prune_input/pruned_text live in a shared crate used by frob-land and frob-check"
bound = false
+++
