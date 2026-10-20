+++
id = "01M4H0WXVXJ18DX9SVX6EHT0AD"
title = "frob doc remap: rewrite doc links, frob:doc/frob:describes targets, .grmb refs and 'x.md section N' citations from docs/MOVED.toml; DRIFT002 and DOC002 say 'moved to X'"
type = "story"
category = "todo"
priority = "medium"
points = 5
parent = "01M4H0WWHV461NXWVCCNKAH3YP"
reporter = "lognd"
created = "2026-10-09T19:05:35Z"
updated = "2026-10-09T19:05:35Z"
idempotency_key = "docs-consolidation-2026-10-09-p0"
labels = ["creates:crates/frob-doc/**", "creates:crates/frob/src/doc_cmd.rs", "creates:docs/MOVED.toml"]
scope = ["crates/frob/src/lib.rs", "crates/frob/src/main.rs", "crates/frob-ack/src/rules.rs", "crates/frob-obligations/src/doc.rs", "docs/reference/cli/frob.md", "docs/reference/rules/DRIFT002.md", "docs/reference/rules/DOC002.md", "Cargo.toml", "Cargo.lock", "changelog.d/**", "crates/frob-doc/**", "crates/frob/src/doc_cmd.rs", "docs/MOVED.toml"]

[[links]]
kind = "blocked-by"
target = "01M4FD0TNGWDEYHP9FHH0RPXYR"

[[acceptance]]
text = "Given a docs/MOVED.toml with moved, merged, removed and archive rows, when `frob doc remap` runs, then markdown links, frob:doc and frob:describes targets, .grmb ref strings and 'x.md section N' citations in crates/ and docs/ point at the new anchors and nothing under tickets/ or notes/ changes"
bound = false

[[acceptance]]
text = "Given a map row whose target is not a heading of the new file at HEAD, when `frob doc remap` runs, then it refuses with exit 3 and names the row"
bound = false

[[acceptance]]
text = "Given an old anchor listed in docs/MOVED.toml, when DRIFT002 or DOC002 fires on it, then the message names the new location"
bound = false
+++

Phase 0 of notes/review/docs-consolidation-2026-10-09.md (section 4.2). Value forms: path#anchor, merged:, removed:superseded-by, archive:. Never rewrites tickets/ or notes/. Relates to ~Q1ZG43K (prose citation resolution): share the citation parser.
