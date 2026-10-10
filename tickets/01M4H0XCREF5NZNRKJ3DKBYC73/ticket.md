+++
id = "01M4H0XCREF5NZNRKJ3DKBYC73"
title = "grmb-planning.md becomes Part II of docs/design/grimble/grmb-spec.md"
type = "docs"
category = "todo"
priority = "medium"
points = 2
parent = "01M4H0WWHV461NXWVCCNKAH3YP"
reporter = "lognd"
created = "2026-10-09T19:05:51Z"
updated = "2026-10-09T19:05:51Z"
idempotency_key = "docs-consolidation-2026-10-09-p3b"
scope = ["docs/design/grmb-planning.md", "docs/design/grimble/**", "docs/README.md", "docs/MOVED.toml", "changelog.d/**"]

[[links]]
kind = "blocked-by"
target = "01M4GK6D3AXE7H91YDCT5VVDBY"

[[links]]
kind = "blocked-by"
target = "01M4H0X3NM9GZGBEFFPCTVPW94"

[[acceptance]]
text = "Given docs/design/grmb-planning.md, when phase 3b lands, then its content is Part II of docs/design/grimble/grmb-spec.md, the file is gone and every anchor is in docs/MOVED.toml, and frob check reports zero DOC002 and zero DRIFT002 findings, and `cargo dev gen --check` is clean"
bound = false
+++

Phase 3b of notes/review/docs-consolidation-2026-10-09.md. Waits for planning rev 2 (~T5VVDBY) and the P1-P3 planning tickets that cite its sections. Prose citations ('x.md section N') in crates/ that this phase moves are rewritten by `frob doc remap`; before running it, add the exact files from `frob doc remap --dry-run` to this ticket's scope with `frob ticket update`. Ledger text and notes are never rewritten. No new frob:doc or frob:describes into docs/design until phase 4b lands (owner decision 5).
