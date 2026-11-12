+++
id = "01M5F8MNQZMR2YA5Y1BEVX8AZR"
title = "plumb enabled packs through ObligationInputs instead of cov001 re-reading frob.toml"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M44YQS4CNZM54P067GJVPDC0"
reporter = "lognd"
created = "2026-10-21T12:58:06Z"
updated = "2026-11-12T04:32:54Z"
scope = ["crates/frob-obligations/**", "crates/frob-check/**", "changelog.d/01M5F8MNQZMR2YA5Y1BEVX8AZR.*"]

[[acceptance]]
text = "ObligationInputs carries the enabled packs, and cov.rs unity_roots/unity_dynamic read them from there instead of re-reading frob.toml"
bound = false

[[acceptance]]
text = "All ObligationInputs construction sites (collect.rs, frob-check snapshot.rs) populate the field; existing unity COV001 tests still pass"
bound = false
+++

found while working ~YR0STJ5: cov.rs unity_roots reads frob.toml directly
