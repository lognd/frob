+++
id = "01M67VEJKYCC8P5TX6SHV6Q5YP"
title = "Guides cleanup: quickstart, agents, hooks, coverage, release, ticket-branch"
type = "docs"
category = "todo"
priority = "medium"
points = 3
parent = "01M67VDQ8WGS0SYG4J4NFXNQJE"
reporter = "lognd"
created = "2026-10-31T02:08:36Z"
updated = "2026-10-31T02:08:36Z"
idempotency_key = "docs-ovh-guides"
scope = ["docs/guides/agents.md", "docs/guides/claude-hooks.md", "docs/guides/coverage.md", "docs/guides/freshness-hooks.md", "docs/guides/moving-docs.md", "docs/guides/quickstart.md", "docs/guides/release.md", "docs/guides/ticket-branch.md"]

[[acceptance]]
text = "quickstart runs verbatim on current frob; no Python-era commands; every guide has audience and status header; guides cross-link; moving-docs matches MOVED.toml behavior"
bound = false
+++

Files other than guides/grimble.md, crunk.md and upgrade guide (owned by ~XPA3A54). Follow docs/design/documentation.md; keep frob:doc bindings and run frob ack for drift; never hand-edit docs/reference or docs/schemas; ASCII only. Each page gets a status header and stays current or is marked superseded via docs/MOVED.toml.
