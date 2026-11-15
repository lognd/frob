+++
id = "01M7EXTGGJDCGR4N487X70TMP5"
title = "crunk docs: refresh guide scene section"
type = "task"
category = "todo"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-11-15T06:20:27Z"
updated = "2026-11-15T06:20:27Z"
idempotency_key = "crunkplan-9e374608c29e"
labels = ["no-story"]

[[acceptance]]
text = "the section matches the current scene dialect and verbs"
bound = false
+++

Source: ~/projects/frob-audit2-crunk.md, finding L2.
Evidence: guide scene section is stale
Remedy: rewrite to the html dialect
Crates/files: docs/guides/crunk.md:188-225
Verify against HEAD first; the audit ran on a stale binary.
