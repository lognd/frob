+++
id = "01M4CTE3SNV3X0PD1DA6995F8R"
title = "publish = false for the six crates with no consumer (gob-plan, gob-frameworks, gob-trust, gob-packs, crunk-tailwind, frob-gh) until one exists (audit M11)"
type = "task"
category = "todo"
priority = "low"
points = 1
parent = "01M4CTDVKQVPSY0SF4XTNT2Q1E"
reporter = "lognd"
created = "2026-10-08T03:55:41Z"
updated = "2026-10-08T03:55:41Z"
scope = ["changelog.d/**", "crates/*/Cargo.toml", "crates/gob-dev/**"]

[[acceptance]]
text = "Given cargo dev publish --dry-run, when it runs, then the unconsumed crates are skipped and the rest publish in order"
bound = false
+++

notes/review/audit-2026-10-07.md M11 and L3 (workspace.dependencies). frob-gh gains a consumer through the land CI gate ticket; then it publishes again.
