+++
id = "01M3ZX87403VR4YVK4QMJ7KPBV"
title = "Generated README region for the ticket pointer in the code repository"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M3ZX776JJSRQXW8Q0327K9QN"
reporter = "lognd"
created = "2026-10-03T03:34:46Z"
updated = "2026-10-03T03:34:46Z"
idempotency_key = "m2-nav-code-readme"
labels = ["milestone:2", "area:navigation"]
scope = ["crates/frob-ledger/src/gen/code_readme.rs", "README.md"]

[[links]]
kind = "blocked-by"
target = "01M3ZX85N2KZ39PG65MX0YT2P0"

[[links]]
kind = "blocked-by"
target = "01M3ZX85X37W6QSQSJD1WYVKZG"

[[acceptance]]
text = "Given `ticket reindex --code-readme`, when run, then only the marked region of README.md changes"
bound = false

[[acceptance]]
text = "Given a hand edit inside the region, when `--check` runs, then GEN001 reports it"
bound = false
+++

Implements navigation.md section 3.2.

A BEGIN/END marked region of README.md with the branch link, the three commands and the tracker link; GEN001 checks it byte for byte and refuses edits inside it.
