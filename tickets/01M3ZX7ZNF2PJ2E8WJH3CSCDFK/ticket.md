+++
id = "01M3ZX7ZNF2PJ2E8WJH3CSCDFK"
title = "Teaching state: [ui] teach knob and .frob/seen.toml, first-occurrence inline explain"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M3ZX76ZV963F3AXRKJ8F744N"
reporter = "lognd"
created = "2026-10-03T03:34:38Z"
updated = "2026-10-20T04:39:23Z"
idempotency_key = "m2-diag-teach-state"
labels = ["milestone:2", "area:diagnostics"]
scope = ["crates/gob-diagnostics/src/teach.rs", "crates/gob-config/src/**", "crates/gob-diagnostics/Cargo.toml", "crates/gob-diagnostics/src/lib.rs", "docs/design/diagnostics.md", "docs/reference/config.md", "docs/schemas/config.json"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7ZD77ZW385N5B992NX3A"

[[links]]
kind = "blocked-by"
target = "01M3ZX7ZHBHNASXSNNCMHSZ4M6"

[[acceptance]]
text = "Given a rule firing for the first time in a repository, when check runs, then the full explain text is printed inline once and seen.toml records it; a second run prints only the one-line form"
bound = true

[[acceptance]]
text = 'Given `[ui] teach = "never"`, when check runs, then only help lines are printed, and with "always" the full text prints every time'
bound = true
+++

Implements diagnostics.md sections 5 and 7.1.

Materialized [ui] teach = first|never|always (default first); state in local disposable .frob/seen.toml; after the first occurrence the line reads `= explain: grimble explain SYS003 (shown in full on first occurrence)`.
