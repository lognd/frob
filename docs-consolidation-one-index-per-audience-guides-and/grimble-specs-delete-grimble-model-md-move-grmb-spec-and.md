+++
id = "01M4H0X3NM9GZGBEFFPCTVPW94"
title = "grimble specs: delete grimble-model.md, move grmb-spec and binding to docs/design/grimble/, merge code-model 6-7 into binding, write rule-families.md from neatness + cohesion + cicd"
type = "docs"
category = "todo"
priority = "medium"
points = 5
parent = "01M4H0WWHV461NXWVCCNKAH3YP"
reporter = "lognd"
created = "2026-10-09T19:05:41Z"
updated = "2026-10-09T19:05:41Z"
idempotency_key = "docs-consolidation-2026-10-09-p3a"
labels = ["creates:docs/design/grimble/**"]
scope = ["docs/design/grimble-model.md", "docs/design/grmb-spec.md", "docs/design/binding.md", "docs/design/code-model.md", "docs/design/neatness.md", "docs/design/cohesion.md", "docs/design/cicd.md", "docs/design/universal-model.md", "docs/design/README.md", "docs/README.md", "docs/MOVED.toml", "changelog.d/**", "docs/design/grimble/**"]

[[links]]
kind = "blocked-by"
target = "01M4H0WXVXJ18DX9SVX6EHT0AD"

[[links]]
kind = "blocked-by"
target = "01M4H0X29ZW591D2AX69V9PQ94"

[[acceptance]]
text = "Given docs/design/grimble-model.md, when phase 3a lands, then it is deleted, its section 7 is a section of docs/design/grimble/grmb-spec.md and docs/MOVED.toml maps each of its anchors"
bound = false

[[acceptance]]
text = "Given neatness.md, cohesion.md and cicd.md, when phase 3a lands, then docs/design/grimble/rule-families.md states each family once with one template (purpose, rules, knobs, decided, open) and the three files are gone"
bound = false

[[acceptance]]
text = "Given the capability matrix, when phase 3a lands, then it is defined once (binding.md section 7), and frob check reports zero DOC002 and zero DRIFT002 findings, and `cargo dev gen --check` is clean"
bound = false
+++

Phase 3a of notes/review/docs-consolidation-2026-10-09.md (sections 2.2, 3.2, 4.5). cohesion section 2 goes into docs/design/universal-model.md (moved in 4b). Best right after ~X4EY1DC. Prose citations ('x.md section N') in crates/ that this phase moves are rewritten by `frob doc remap`; before running it, add the exact files from `frob doc remap --dry-run` to this ticket's scope with `frob ticket update`. Ledger text and notes are never rewritten. No new frob:doc or frob:describes into docs/design until phase 4b lands (owner decision 5).
