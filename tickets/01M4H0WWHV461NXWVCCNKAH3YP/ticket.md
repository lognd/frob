+++
id = "01M4H0WWHV461NXWVCCNKAH3YP"
title = "Docs consolidation: one index, per-audience guides and generated references, 18 consolidated specs, decision log as TOML, frozen notes archive"
type = "epic"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-09T19:05:34Z"
updated = "2026-10-09T19:06:03Z"
idempotency_key = "docs-consolidation-2026-10-09-epic"
scope = ["changelog.d/**"]

[[links]]
kind = "relates"
target = "01M4H0RE1Q9A1M47ZT7Q1ZG43K"

[[links]]
kind = "relates"
target = "01M4H0RKJHHWWT0XC17W5JD1VG"

[[links]]
kind = "relates"
target = "01M4H0RSP2HVXYS4BNCY9W8WYP"

[[acceptance]]
text = "Given the phase tickets of notes/review/docs-consolidation-2026-10-09.md section 5, when all are done, then the tree of section 3.1 exists, every old design anchor resolves through docs/MOVED.toml, and frob check reports zero DOC002 and zero DRIFT002 findings, and `cargo dev gen --check` is clean"
bound = false
+++

Owner-approved plan of notes/review/docs-consolidation-2026-10-09.md (sections 3-6, ~35CQFYN). Consolidate, not move: merged text is rewritten into one argument per subject, superseded text is deleted (git keeps history; docs/MOVED.toml resolves old anchors).
