+++
id = "01M5ASPRW2FYMNRHWQHEVN9W9J"
title = "Mirror: real GitHub TrackerAdapter over an HTTP transport (read/create/update/close/inventory)"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-19T19:20:09Z"
updated = "2026-10-19T20:20:48Z"
scope = ["crates/frob-mirror/src/github/adapter.rs"]
+++

Only WriteTransport/HistorySource/ListingSource traits exist; no concrete TrackerAdapter. Needed by the mirror recreate verb (~1KH6CCV).
