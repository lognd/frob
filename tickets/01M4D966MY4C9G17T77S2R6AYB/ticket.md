+++
id = "01M4D966MY4C9G17T77S2R6AYB"
title = "Apply the lint-catalogue-2026-10-08 design changes to rules, boundaries, neatness, cohesion, crunk, dotnet-unity, universal-model, plugins, rule-authoring and lint-requirements"
type = "docs"
category = "todo"
priority = "high"
points = 2
parent = "01M4CXTDZGE80G5TWDCWY08EWT"
reporter = "lognd"
created = "2026-10-08T08:13:21Z"
updated = "2026-10-08T08:13:21Z"
scope = ["changelog.d/**", "docs/design/**", "notes/research/**"]

[[acceptance]]
text = "Given the change list, when the docs are updated, then each listed section carries the change and frob check reports no DRIFT or SYNC finding"
bound = false

[[acceptance]]
text = "Given boundaries.md 2.5, when read, then every new family has an owner and a crate"
bound = false
+++

notes/research/lint-catalogue-2026-10-08.md section 5 (eleven changes: bind-before-own policy, parser ownership in gob-check, new families ERR, TESTQ, PAIR, TYPING, VIS, FMT, SPELL, NAME, LINT, REACT and UNITY ranges, hot and teardown capabilities, NEAT026 numbering fix, COH Advisory until measured, crunk build order).
