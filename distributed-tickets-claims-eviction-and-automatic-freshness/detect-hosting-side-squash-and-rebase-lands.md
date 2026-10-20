+++
id = "01M5CW0609NX9MJ45G2R4CQE0R"
title = "Detect hosting-side squash and rebase lands"
type = "task"
category = "in-progress"
priority = "high"
points = 2
parent = "01M5CVZND2H3YDDB67WZ7ANRQY"
reporter = "lognd"
created = "2026-10-20T14:38:43Z"
updated = "2026-10-20T23:29:58Z"
idempotency_key = "dt-DT22"
scope = ["crates/frob-land/src/hostland.rs", "crates/frob-land/src/lib.rs", "crates/frob-land/tests/land.rs", "crates/frob/src/refresh_cmd.rs", "changelog.d/01M5CW0609NX9MJ45G2R4CQE0R.added.md"]

[[links]]
kind = "blocked-by"
target = "01M5CW05WX0TMSBKDFTPEHB5R3"
+++

Recognise a ticket landed by the host and close it. See docs/design/distributed-tickets.md.
