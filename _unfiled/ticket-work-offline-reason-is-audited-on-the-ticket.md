+++
id = "01M7EX86H3KBF8A1VVG44D4XAZ"
title = "ticket work --offline --reason is audited on the ticket"
type = "task"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-15T06:10:27Z"
updated = "2026-11-15T06:10:27Z"
labels = ["no-story"]

[[acceptance]]
text = "Offline work adds a ticket note with the reason (test)"
bound = false
+++

Source: frob-audit-core.md L10. Evidence: verb.rs:160,264-292 accept --offline --reason without recording it. Remedy: add a ledger note with the reason. Files: crates/frob/src/verb.rs and callee.
