+++
id = "01M7EXTJ88WR479046W9D3NAYY"
title = "grimble: MDL006 bound resolves planning entity refs (CONF 18.2)"
type = "task"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-15T06:20:29Z"
updated = "2026-11-15T06:20:29Z"
labels = ["no-story"]

[[acceptance]]
text = "A bound claim targeting a scenario or step entity no longer yields MDL006"
bound = false

[[acceptance]]
text = "A model test covers the web_app.checkout ref"
bound = false
+++

Audit: ~/projects/frob-audit2-grimble.md M1 (part 1). Evidence: conformance.md 18.2 sample gives MDL006 because bound cannot target a planning entity such as web_app.checkout. Remedy: resolve planning refs in bound. Crates: crates/grimble-model, crates/grimble-check.
