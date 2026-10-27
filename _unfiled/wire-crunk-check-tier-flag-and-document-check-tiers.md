+++
id = "01M5XDC5WFWYYNXBCXRNGXAEYS"
title = "Wire crunk check --tier flag and document check tiers"
type = "task"
category = "in-progress"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-27T00:50:13Z"
updated = "2026-10-27T02:43:29Z"
scope = ["crates/crunk/src/lib.rs", "docs/design/crunk.md"]

[[acceptance]]
text = "crunk check accepts --tier T0..T4 (default T1), rejects other values with exit 2 listing them, and passes it to CheckOptions.tier"
bound = true

[[acceptance]]
text = "docs/design/crunk.md documents the not_run section of the check document"
bound = true
+++

Follow-up to ~08R5Y3H: crunk_check::CheckOptions.tier and the not_run document section exist; add the --tier value_parser T0..T4 (clap exits 2 listing them, default T1) in GateArgs, pass it to CheckOptions, and document section 4 not_run. Those paths were leased by another ticket.
