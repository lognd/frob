+++
id = "01M6ZX0S1CCT8F1NXDF4TNGTK4"
title = "Grimble LOG: byte offsets on call sites so the universal cross-check matches precisely, not by line"
type = "task"
category = "in-progress"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-11-09T10:17:47Z"
updated = "2026-11-09T10:49:35Z"
scope = ["crates/gob-symbols/**", "crates/grimble-check/**", "docs/design/grimble/**"]

[[acceptance]]
text = "Two output calls on one source line carry distinct byte spans from gob-symbols"
bound = true

[[acceptance]]
text = "The cross-check covers a model call only by byte overlap with a scanner hit, so a same-line second call is reported"
bound = false

[[acceptance]]
text = "A call with an unknown span is never treated as covered"
bound = false
+++
