+++
id = "01M5B07S0STANADP897P4A6YB2"
title = "Mirror: replace the curl-subprocess HTTP transport with a native HttpTransport"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-19T21:14:17Z"
updated = "2026-10-19T23:49:43Z"
scope = ["crates/frob-mirror/**", "docs/design/mirror.md", "design/model.grmb"]

[[acceptance]]
text = "frob-mirror provides a native in-process HttpTransport that sends method, query, JSON body and auth headers, reports redirects unfollowed, and maps connection failures to TransportError"
bound = true
+++

found while working ~1KH6CCV
