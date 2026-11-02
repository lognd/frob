+++
id = "01M6DS5R8DYVH4DSZBKMYQBS8S"
title = "Move 7 leftover top-level docs/design pages into subdirectories"
type = "docs"
category = "in-progress"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-02T09:24:16Z"
updated = "2026-11-02T10:03:15Z"
scope = ["docs/design/*.md", "docs/MOVED.toml", "crates/crunk-*/src/**", "docs/guides/crunk-hullbreach.md", "docs/guides/freshness-hooks.md", "docs/design/**", "docs/decisions/**", "docs/history/**", "docs/README.md", "crates/frob-evidence/src/**", "crates/frob-present/src/**"]
+++

found while working ~SD9WXF0: crunk, migration, output, output-atoms, distributed-tickets, grimble-capabilities-v3, vet remain at docs/design top level; moving them needs MOVED.toml rows plus doc-comment path rewrites in crates/crunk-* and gob-symbols tests, and guide links owned by ~J0BEQR7.
