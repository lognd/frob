+++
id = "01M7EXWG336G71CXW56E0NX9NP"
title = "grimble-model: contract with inline typed fields and structural flow-end compare"
type = "task"
category = "todo"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-11-15T06:21:32Z"
updated = "2026-11-15T06:21:32Z"
labels = ["no-story"]

[[acceptance]]
text = "contract { field id : int; } parses without MDL000"
bound = false

[[acceptance]]
text = "A flow whose two ends disagree on a field type raises a finding"
bound = false

[[acceptance]]
text = "fmt round-trips"
bound = false
+++

Child of H5 (~AGD0PHX), /home/logan/projects/frob-audit2-grimble.md H5 lifecycle coverage. Evidence: requirement/state/field/deployment/risk/glossary all give MDL000, kind host MDL009. Piece 2. Design-first data model: field id : int; inside contract, plus a structural comparison of both ends of a flow. Crates: grimble-model, grimble-bind.
