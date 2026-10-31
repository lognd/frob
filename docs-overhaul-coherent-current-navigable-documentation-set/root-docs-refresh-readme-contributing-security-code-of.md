+++
id = "01M67VEJ1AJM9ACF32HRJFEASS"
title = "Root docs refresh: README, CONTRIBUTING, SECURITY, CODE_OF_CONDUCT, CHANGELOG*"
type = "docs"
category = "todo"
priority = "medium"
points = 3
parent = "01M67VDQ8WGS0SYG4J4NFXNQJE"
reporter = "lognd"
created = "2026-10-31T02:08:35Z"
updated = "2026-10-31T02:08:35Z"
idempotency_key = "docs-ovh-root"
scope = ["README.md", "CONTRIBUTING.md", "SECURITY.md", "CODE_OF_CONDUCT.md", "CHANGELOG.md", "CHANGELOG-v1.md"]

[[acceptance]]
text = "Root README describes the Rust frob, crunk and grimble accurately with links that resolve; CONTRIBUTING uses frob verbs only; CHANGELOG-v1 marked archived; no Python-era text"
bound = false
+++

Audit and rewrite root markdown. Follow docs/design/documentation.md; keep frob:doc bindings and run frob ack for drift; never hand-edit docs/reference or docs/schemas; ASCII only. Each page gets a status header and stays current or is marked superseded via docs/MOVED.toml.
