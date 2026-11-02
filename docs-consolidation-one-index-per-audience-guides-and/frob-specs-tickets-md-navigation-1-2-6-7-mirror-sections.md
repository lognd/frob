+++
id = "01M4H0X78V0F2GV0GW6AZ4P6PQ"
title = "frob specs: tickets.md (+ navigation 1-2, 6-7, mirror; sections renumbered) and pm-and-releases.md (pm-enforcement + releases) under docs/design/frob/"
type = "docs"
category = "in-progress"
priority = "medium"
points = 5
parent = "01M4H0WWHV461NXWVCCNKAH3YP"
reporter = "lognd"
created = "2026-10-09T19:05:45Z"
updated = "2026-11-02T04:32:51Z"
idempotency_key = "docs-consolidation-2026-10-09-p5"
labels = ["creates:docs/design/frob/**"]
scope = ["docs/design/tickets.md", "docs/design/navigation.md", "docs/design/mirror.md", "docs/design/models/mirror/**", "docs/design/pm-enforcement.md", "docs/design/releases.md", "docs/design/README.md", "docs/README.md", "docs/MOVED.toml", "changelog.d/**", "docs/design/frob/**", "crates/frob*/**", "crates/gob-dev/src/publish.rs", "docs/design/*.md", "docs/design/shared/**", "docs/guides/**", "docs/reference/**", ".github/workflows/bench-pr.yml", ".github/workflows/bench.yml", ".github/workflows/build-smoke.yml", ".github/workflows/ci.yml", ".github/workflows/ecosystem-pr.yml", ".github/workflows/fuzz-nightly.yml", ".github/workflows/mirror.yml", ".github/workflows/release.yml", "Cargo.toml", "docs/decisions/2026-10-03-release-workflow-hand-written.md", "docs/decisions/README.md", "docs/decisions/decisions.toml", "docs/schemas/config.json", "docs/schemas/crunk-gallery-check-v1.json", "docs/schemas/crunk-gallery-manifest-v1.json", "docs/schemas/crunk-gallery-manifest-v2.json", "docs/schemas/crunk-gallery-manifest-v3.json", "docs/schemas/crunk-layout-solve-v1.json"]

[[links]]
kind = "blocked-by"
target = "01M4H0WXVXJ18DX9SVX6EHT0AD"

[[links]]
kind = "blocked-by"
target = "01M4H0X29ZW591D2AX69V9PQ94"

[[acceptance]]
text = "Given tickets, navigation 1-2 and 6-7, and mirror, when phase 5 lands, then docs/design/frob/tickets.md states ticket identity and the ticket branch once, has no section-number gaps, and every 'tickets.md section N' citation in crates/ resolves"
bound = false

[[acceptance]]
text = "Given pm-enforcement and releases, when phase 5 lands, then docs/design/frob/pm-and-releases.md states cycles, capacity and WIP once, and frob check reports zero DOC002 and zero DRIFT002 findings, and `cargo dev gen --check` is clean"
bound = false
+++

Phase 5 of notes/review/docs-consolidation-2026-10-09.md (sections 2.3, 3.2). docs/design/models/mirror/ stays as the appendix of tickets.md part 3. navigation 3-5 stay for phase 4b. Prose citations ('x.md section N') in crates/ that this phase moves are rewritten by `frob doc remap`; before running it, add the exact files from `frob doc remap --dry-run` to this ticket's scope with `frob ticket update`. Ledger text and notes are never rewritten. No new frob:doc or frob:describes into docs/design until phase 4b lands (owner decision 5).
