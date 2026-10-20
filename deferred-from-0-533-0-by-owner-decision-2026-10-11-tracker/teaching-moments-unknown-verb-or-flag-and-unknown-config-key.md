+++
id = "01M3ZX827QGZVR7KCV61M0ZSQR"
title = "Teaching moments: unknown verb or flag and unknown config key"
type = "task"
category = "todo"
priority = "low"
points = 3
parent = "01M3ZX76ZV963F3AXRKJ8F744N"
reporter = "lognd"
created = "2026-10-03T03:34:41Z"
updated = "2026-10-03T03:34:41Z"
idempotency_key = "m2-diag-moments-cli"
labels = ["milestone:2", "area:diagnostics"]
scope = ["crates/gob-cli/src/error.rs", "crates/gob-config/src/**"]

[[acceptance]]
text = "Given `frob tikcet list`, when run, then the error suggests `ticket` and lists three likely verbs and exits 2"
bound = false

[[acceptance]]
text = "Given an unknown key `[check] fail_no`, when loaded, then the error suggests `fail_on` and links the config reference table"
bound = false
+++

Implements diagnostics.md section 5 (table rows 3 and 4).

Did-you-mean through strsim plus the three most likely verbs; unknown config key gets did-you-mean against the materialized table and the doc link for the table.
