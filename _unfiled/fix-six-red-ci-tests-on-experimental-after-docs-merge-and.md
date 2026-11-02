+++
id = "01M6ETBDMM1DFA6YAA0KG4VEGB"
title = "Fix six red CI tests on experimental after docs merge and gob-ir vocab move"
type = "bug"
category = "todo"
priority = "high"
points = 2
reporter = "lognd"
created = "2026-11-02T19:04:05Z"
updated = "2026-11-02T19:04:05Z"
scope = ["crates/frob/tests/**", "crates/frob-docgen/tests/**", "crates/gob-dev/**", "docs/design/shared/**", "grimble.packs.lock", "changelog.d/**"]

[[acceptance]]
text = "Given the CI run 41458902533 failures, when the six named tests run, then all pass on Linux"
bound = false
+++
