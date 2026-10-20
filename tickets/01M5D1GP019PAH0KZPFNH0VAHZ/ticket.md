+++
id = "01M5D1GP019PAH0KZPFNH0VAHZ"
title = "Audit working-tree tickets/ path assumptions before the orphan flip"
type = "task"
category = "in-progress"
priority = "high"
points = 3
parent = "01M5CVZND2H3YDDB67WZ7ANRQY"
reporter = "lognd"
created = "2026-10-20T16:15:07Z"
updated = "2026-10-20T16:21:22Z"
idempotency_key = "dt-audit-tickets-paths"
scope = ["crates/frob/tests/it/orphan_readiness.rs", "crates/frob/tests/it/main.rs", "docs/design/orphan-readiness.md", "docs/guides/ticket-branch.md"]

[[acceptance]]
text = "Given an orphan-mode repo, when frob check and gen run, then no rule reports missing tickets/ paths"
bound = true
+++

Found while working ~X2S3S24: frob-check/src/product.rs:693, frob-pm/src/legacy/story.rs, gob-walk and any other reader assume tickets/ lives in the working tree. Under ref_mode = orphan these must read via the ledger. Audit with grep, fix or file per-site tickets, and add a test that runs check on an orphan-mode repo. Blocks the DT04 flip (~Q468BZE, ~HP76EES).
