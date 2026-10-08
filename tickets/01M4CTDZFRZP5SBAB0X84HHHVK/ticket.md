+++
id = "01M4CTDZFRZP5SBAB0X84HHHVK"
title = "gob-git ledger: sync_checkout skips paths whose tip blob has moved past the one being written (audit M3)"
type = "task"
category = "in-progress"
priority = "high"
points = 3
parent = "01M4CTDVKQVPSY0SF4XTNT2Q1E"
reporter = "lognd"
created = "2026-10-08T03:55:36Z"
updated = "2026-10-08T08:03:00Z"
scope = ["changelog.d/**", "crates/gob-git/**"]

[[acceptance]]
text = "Given two concurrent ledger writers on one path, when both sync the checkout in the losing order, then the working tree and index equal HEAD (deterministic test with an injected interleaving)"
bound = true
+++

notes/review/audit-2026-10-07.md M3, gob-git/src/ledger.rs commit_paths_with 180-185, sync_checkout 440-498, sync_other_checkouts 363-403. Two writers can leave the working tree with the older ticket.md while HEAD has the newer one.
