+++
id = "01M4GWS3GBJTFXFEGSNFB7J4FQ"
title = "frob-land: wire culprit finding into the base-red refusal and file the blocking fix ticket"
type = "story"
category = "todo"
priority = "medium"
points = 3
parent = "01M4GRTA9XBJCM2RY98HWZXYC7"
reporter = "lognd"
created = "2026-10-09T17:53:24Z"
updated = "2026-10-09T17:53:24Z"
scope = ["crates/frob-land/**", "changelog.d/**"]

[[links]]
kind = "blocked-by"
target = "01M4D6NFCDSW5E4FD9X8J3BE8W"

[[links]]
kind = "blocked-by"
target = "01M4GRXFQYZRDJ2TP68WFY48QC"

[[acceptance]]
text = "Given a red base, when land refuses, then E-LAND-BASE-RED names the tickets(land) commits between the last green and first red run"
bound = false

[[acceptance]]
text = "Given the same red base, when land is retried, then no second fix ticket is filed (idempotency key from frob_gh::find_culprit) and lands stay blocked until the fix ticket closes"
bound = false
+++

found while working ~WFY48QC; consumes frob_gh::find_culprit / Client::workflow_runs; cycle ~XAFQ008
