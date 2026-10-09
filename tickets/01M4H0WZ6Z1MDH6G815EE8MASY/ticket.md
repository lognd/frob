+++
id = "01M4H0WZ6Z1MDH6G815EE8MASY"
title = "Docs index and status headers: docs/README.md and notes/README.md, one header block on every docs file, stale facts fixed"
type = "docs"
category = "todo"
priority = "medium"
points = 3
parent = "01M4H0WWHV461NXWVCCNKAH3YP"
reporter = "lognd"
created = "2026-10-09T19:05:37Z"
updated = "2026-10-09T19:05:37Z"
idempotency_key = "docs-consolidation-2026-10-09-p1"
labels = ["creates:docs/README.md", "creates:notes/README.md"]
scope = ["docs/**/*.md", "notes/**/*.md", "README.md", ".github/PULL_REQUEST_TEMPLATE.md", "crates/frob-lease/src/config.rs", "crates/frob-lease/src/lib.rs", "crates/frob-worktree/src/lib.rs", "crates/gob-plan/README.md", "docs/schemas/config.json", "changelog.d/**", "docs/README.md", "notes/README.md"]

[[acceptance]]
text = "Given every markdown file under docs/, when phase 1 lands, then each starts with the Status/Owner/Decisions/Audience block of the report's section 3 principle 5 and docs/README.md lists every document by audience"
bound = false

[[acceptance]]
text = "Given notes/, when phase 1 lands, then notes/README.md has one row per note (date, question, decision fed, status)"
bound = false

[[acceptance]]
text = "Given the stale facts of report section 2.3, when phase 1 lands, then the 'tickets.md section 6' citations, the crunk and gob-plan READMEs, the PR template, the README typo, the fake 0.532.0 heading and the 17 absolute local paths are fixed, and frob check reports zero DOC002 and zero DRIFT002 findings, and `cargo dev gen --check` is clean"
bound = false
+++

Phase 1 of notes/review/docs-consolidation-2026-10-09.md (sections 2.3, 3 principle 5). The header check itself is ~W5JD1VG. Folds in ~VQTPNVW (generated docs/README.md map) and ~XCH7F2D (docs/SUMMARY.md): close those as duplicates of this ticket.
