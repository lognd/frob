+++
id = "01M6Q1JHPPFRX5QSKW0991J98R"
title = "Add claim_idle_days ticket field and pass it to claim_status"
type = "task"
category = "in-progress"
priority = "medium"
points = 2
parent = "01M5DCZ3PVHP2ZNP9SVYFFQSVP"
reporter = "lognd"
created = "2026-11-05T23:44:14Z"
updated = "2026-11-11T14:23:02Z"
labels = ["no-story"]
scope = ["crates/frob-ledger/src/**", "crates/frob-worktree/**", "crates/frob-ledger/benches/**"]

[[acceptance]]
text = "Frontmatter accepts claim_idle_days, a ledger verb sets it, and frob-worktree next.rs feeds it as ticket_days into claim_status"
bound = true
+++

Follow-up of ~JFEYB9S: Frontmatter (frob-ledger) has no claim_idle_days field (deny_unknown_fields); add it plus a field-set verb, then feed it as ticket_days in frob-worktree next.rs claim_status. no-story: internal ledger plumbing with no standalone user-visible story.
