+++
id = "01M5BA6340AM6WZBKZXVCCJKNB"
title = "docs/design/mirror.md: recreate section still says 'curl transport'; now NativeTransport (ureq)"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-20T00:08:08Z"
updated = "2026-10-20T00:38:30Z"
scope = ["docs/design/mirror.md"]

[[acceptance]]
text = "docs/design/mirror.md describes the recreate verb's live transport as NativeTransport (ureq/rustls), not curl"
bound = true
+++

found while working ~3CPVHZS: line ~296 says GithubAdapter over a curl transport; replace with the native ureq transport. Blocked from that ticket by a lease held by ~Q7FE2A0.
