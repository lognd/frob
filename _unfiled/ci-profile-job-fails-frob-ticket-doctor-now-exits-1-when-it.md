+++
id = "01M4HSNJF5CKX2XHFQT6REH8WT"
title = "CI profile job fails: frob ticket doctor now exits 1 when it reports issues (~76AS8XH), but its profile scenario expects exit 0"
type = "bug"
category = "done"
outcome = "done"
priority = "high"
points = 1
reporter = "lognd"
created = "2026-10-10T02:18:29Z"
updated = "2026-10-10T02:56:14Z"
scope = ["crates/gob-dev/profile.toml", "changelog.d/**"]

[[acceptance]]
text = "Given the profile job on this repository, when frob ticket doctor reports ledger issues, then its scenario accepts exit 1 (issues reported) as well as 0, and fails only on other exit codes or a budget overrun"
bound = true
+++

CI run 38015688152 profile job: frob ticket doctor warm 497 ms, exit 1. Cause: ~76AS8XH made doctor exit 1 with issues; this ledger has 131 E-DOCTOR-ORDER issues (repair is ~Y8NVYNZ).
