+++
id = "01M4H0X29ZW591D2AX69V9PQ94"
title = "Decision log as TOML: docs/decisions/decisions.toml with a generated, anchored docs/decisions/README.md; row bodies moved to their home sections; supersession as status"
type = "docs"
category = "todo"
priority = "medium"
points = 5
parent = "01M4H0WWHV461NXWVCCNKAH3YP"
reporter = "lognd"
created = "2026-10-09T19:05:40Z"
updated = "2026-10-09T19:05:40Z"
idempotency_key = "docs-consolidation-2026-10-09-p2"
labels = ["creates:docs/decisions/decisions.toml", "creates:crates/gob-dev/src/render/decisions.rs", "creates:docs/MOVED.toml"]
scope = ["docs/design/*.md", "docs/decisions/**", "crates/gob-dev/src/render/**", "crates/gob-dev/src/main.rs", "changelog.d/**", "docs/decisions/decisions.toml", "crates/gob-dev/src/render/decisions.rs", "docs/MOVED.toml"]

[[links]]
kind = "blocked-by"
target = "01M4H0WZ6Z1MDH6G815EE8MASY"

[[acceptance]]
text = "Given docs/decisions/decisions.toml, when `cargo dev gen` runs, then docs/decisions/README.md holds one anchored row per decision (id, date, one-line decision, status, home link) and GEN001 fails on a hand edit"
bound = false

[[acceptance]]
text = "Given D4, D31, D42, D43, D44, D49, D55, D7, D88 and D103, when phase 2 lands, then each row's status names its superseding or amending decision and D61 is no longer a prose row"
bound = false

[[acceptance]]
text = "Given docs/design/README.md, when phase 2 lands, then it is the spec index only (no decision log, no evidence table, no precedence paragraph), and frob check reports zero DOC002 and zero DRIFT002 findings, and `cargo dev gen --check` is clean"
bound = false
+++

Phase 2 of notes/review/docs-consolidation-2026-10-09.md (sections 2.5, 3.5, owner decision 3). The ADR docs/decisions/2026-10-03-release-workflow-hand-written.md becomes D134. Freeze D-row additions the day it lands (~T5VVDBY, ~GJVPDC0, ~Z9D8SR7 add rows).
