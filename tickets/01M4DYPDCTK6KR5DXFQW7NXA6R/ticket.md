+++
id = "01M4DYPDCTK6KR5DXFQW7NXA6R"
title = "land advance fails E-LAND-ADVANCE on a transient index.lock held by a concurrent ledger write; take the ledger lock around advance or retry with backoff"
type = "bug"
category = "in-progress"
priority = "high"
points = 2
parent = "01M4CTDVKQVPSY0SF4XTNT2Q1E"
reporter = "lognd"
created = "2026-10-08T14:29:21Z"
updated = "2026-10-10T01:05:25Z"
scope = ["changelog.d/**", "crates/frob-land/src/git.rs"]

[[acceptance]]
text = "Given a concurrent ledger write holding index.lock during advance, when land runs, then it waits or retries and succeeds (deterministic test with an injected lock)"
bound = true
+++

2026-10-08 13:38: frob land ~M635E0X failed to fast-forward experimental because an agent's evidence write held .git/index.lock; nothing was damaged and a re-run is needed.
