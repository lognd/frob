+++
id = "01M4DYPH29YAN8DBKAKKCDWQGX"
title = "crunk: must_measure design note (spec-only project gets a required Unresolved from COLOR001), multi-file mdtest projects, stale crunk:waive directive docs"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 2
parent = "01M43ANVJYA7GHN0Y8GX0SN72M"
reporter = "lognd"
created = "2026-10-08T14:29:25Z"
updated = "2026-10-12T02:37:32Z"
scope = ["changelog.d/**", "crates/crunk-rules/**", "crates/crunk-check/**", "docs/design/crunk.md", "docs/reference/directives.md", "docs/schemas/directives.json", "crates/crunk-ingest/src/waive.rs"]

[[acceptance]]
text = "Given a spec-only project (crunk.toml, no sources), when crunk check runs, then COLOR001 reports a required Unresolved (examined zero subjects)"
bound = true

[[acceptance]]
text = "Given the generated directives reference, when it is read, then crunk:waive documents that a missing or blank reason grants nothing"
bound = true
+++

Follow-ups from ~8MQFYVM. Decision recorded: ingest stays to css_root plus [jsx] globs; ungoverned files belong to the org rules.
