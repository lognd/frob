+++
id = "01M6RHZHQHQFX4CRXN4DM0PQSE"
title = "grmb-spec: document manual tests listed in grimble status (follow-up to WZS7NG7)"
type = "docs"
category = "in-progress"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-06T13:50:12Z"
updated = "2026-11-13T08:18:23Z"
idempotency_key = "grmb-status-manual"
labels = ["good-first"]
scope = ["docs/**"]

[[acceptance]]
text = "Given grimble status lists manual tests, when a reader opens the docs page, then each test is documented with how to run it."
bound = true
+++

Document the manual tests that grimble status lists.

## Start here

Read crates/grimble-cli status output and docs/grimble, then add a short docs page listing each manual test and how to run it.
