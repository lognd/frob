+++
id = "01M7EXTZWBP80GE9MWHT54GMR9"
title = "grimble-bind: unresolved route/api string realization emits a finding, keeps status_hi"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-15T06:20:43Z"
updated = "2026-11-15T06:20:43Z"
labels = ["no-story"]

[[acceptance]]
text = "An impl with an unmatched route string yields an Unresolved finding"
bound = false

[[acceptance]]
text = "status_hi is preserved"
bound = false

[[acceptance]]
text = "planning-semantics.md lists supported route matcher frameworks"
bound = false
+++

Audit: /home/logan/projects/frob-audit2-grimble.md M2. Evidence: a route/api string realization silently demotes an impl to declared (status and status_hi), no finding, no binding row. Files: crates/grimble-bind/src/plan.rs, planning-semantics.md 12.8 lines 188-192. Remedy: emit an Unresolved finding, keep status_hi, document the matcher frameworks.
