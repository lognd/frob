+++
id = "01M6Q1JHPPFRX5QSKW0991J98R"
title = "Add claim_idle_days ticket field and pass it to claim_status"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M5DCZ3PVHP2ZNP9SVYFFQSVP"
reporter = "lognd"
created = "2026-11-05T23:44:14Z"
updated = "2026-11-06T00:31:34Z"
scope = ["crates/frob-ledger/src/**"]
+++

Follow-up of ~JFEYB9S: Frontmatter (frob-ledger) has no claim_idle_days field (deny_unknown_fields); add it plus a field-set verb, then feed it as ticket_days in frob-worktree next.rs claim_status.
