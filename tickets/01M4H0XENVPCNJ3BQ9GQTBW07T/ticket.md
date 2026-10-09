+++
id = "01M4H0XENVPCNJ3BQ9GQTBW07T"
title = "Notes archive: indexed and frozen; audit and resolution pairs merged; crunk research merged; v1-gap under v1/; root strays sorted; coordinator.md deleted with its agent rules moved to docs/guides/agents.md"
type = "docs"
category = "todo"
priority = "medium"
points = 3
parent = "01M4H0WWHV461NXWVCCNKAH3YP"
reporter = "lognd"
created = "2026-10-09T19:05:52Z"
updated = "2026-10-09T19:05:52Z"
idempotency_key = "docs-consolidation-2026-10-09-p7"
labels = ["creates:docs/guides/agents.md"]
scope = ["notes/**", "docs/README.md", "docs/MOVED.toml", "changelog.d/**", "docs/guides/agents.md"]

[[links]]
kind = "blocked-by"
target = "01M4FCWY3H8CRHYYHVQ19SEHXJ"

[[links]]
kind = "blocked-by"
target = "01M4GMKVN0XRRH5FFXV5QA6P6W"

[[links]]
kind = "blocked-by"
target = "01M4H0WZ6Z1MDH6G815EE8MASY"

[[acceptance]]
text = "Given notes/audit-design.md with audit-resolution.md, and design-consistency.md with its resolution and pass 2, when phase 7 lands, then each set is one file under notes/review/ with finding then resolution"
bound = false

[[acceptance]]
text = "Given notes/coordinator.md, when phase 7 lands, then it is deleted and its still-valid agent ground rules are a short docs/guides/agents.md listed in docs/README.md"
bound = false

[[acceptance]]
text = "Given notes/, when phase 7 lands, then no note sits at the notes/ root except README.md, every note has an index row, and frob check reports zero DOC002 and zero DRIFT002 findings, and `cargo dev gen --check` is clean"
bound = false
+++

Phase 7 of notes/review/docs-consolidation-2026-10-09.md (sections 2.6, 3.1, 3.2, owner decision 4).
