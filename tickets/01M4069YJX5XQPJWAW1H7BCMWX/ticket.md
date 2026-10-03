+++
id = "01M4069YJX5XQPJWAW1H7BCMWX"
title = "docs/guides/release.md: the release runbook (owner steps, environments, resume)"
type = "docs"
category = "in-progress"
priority = "medium"
points = 2
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-03T06:13:00Z"
updated = "2026-10-03T17:53:06Z"
idempotency_key = "m2-rel-release-guide"
labels = ["milestone:2", "area:release"]
scope = ["docs/guides/release.md"]

[[links]]
kind = "blocked-by"
target = "01M4069Y65FA7GGXG2F6N2KET1"

[[links]]
kind = "blocked-by"
target = "01M4069YA9PXDNNCV86DR38G0G"

[[acceptance]]
text = "Given the guide, when followed on a dry run, then every command exists"
bound = true

[[acceptance]]
text = "Given a partial publish, when the guide's resume steps are followed, then publish continues at the first unpublished crate"
bound = true
+++

Runbook: prerequisites and owner steps (environments, reviewer, tokens or trusted publishers, crate name reservations), the cut-to-publish sequence, how to resume a partial publish, how to pin or yank, and v1's lessons (manylinux, retired images, timeouts). Linked from frob release status output.
