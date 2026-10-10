+++
id = "01M3ZX87BT61JENRM8NVQTPNVW"
title = "Generated docs/README.md map by reader task and per-crate README headers"
type = "task"
category = "done"
outcome = "duplicate"
priority = "low"
points = 3
parent = "01M3ZX776JJSRQXW8Q0327K9QN"
reporter = "lognd"
created = "2026-10-03T03:34:46Z"
updated = "2026-10-09T20:45:25Z"
idempotency_key = "m2-nav-docs-map"
labels = ["milestone:2", "area:navigation"]
scope = ["crates/gob-dev/src/render/docs_map.rs", "docs/README.md"]

[[links]]
kind = "blocked-by"
target = "01M3ZX85N2KZ39PG65MX0YT2P0"

[[acceptance]]
text = "Given the docs tree, when generated, then docs/README.md lists pages by reader task"
bound = false

[[acceptance]]
text = "Given a crate without a README header, when checked, then GEN001 reports it"
bound = false
+++

Implements navigation.md section 3.2 (last bullet).

Generated as in the survey; per-crate README headers carry the one-line description.
