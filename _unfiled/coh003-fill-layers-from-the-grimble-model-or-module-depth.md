+++
id = "01M5HJDX1Q27XGZ77ACWXQ03KP"
title = "COH003: fill layers from the grimble model or module depth"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-22T10:27:39Z"
updated = "2026-10-23T09:30:37Z"
scope = ["crates/grimble-check/**", "docs/design/**", "docs/reference/rules/**", "Cargo.lock"]

[[acceptance]]
text = "COH003 reads its layers from the grimble model, falling back to module depth, instead of an empty Coh003Options.layers"
bound = true

[[acceptance]]
text = "COH003 tests cover model-supplied layers, the module-depth fallback, and docs/design/cohesion.md section 1.2 names the layer source"
bound = true
+++

Nothing fills Coh003Options.layers; read layers from the model or module depth. Also update docs/design/cohesion.md section 1.2 with the layer source.
