+++
id = "01M7EXV09Q0BXXF1TW2HFE142N"
title = "grimble docs: mark chain features (SPEC 14.2/14.5/14.7, PLAN030-034/011/040) not implemented"
type = "task"
category = "todo"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-11-15T06:20:43Z"
updated = "2026-11-15T06:20:43Z"
labels = ["no-story"]

[[acceptance]]
text = "Each listed section and row carries an explicit 'not implemented' marker"
bound = false

[[acceptance]]
text = "gob-dev gen all --check passes"
bound = false
+++

Audit: ~/projects/frob-audit2-grimble.md M3 (docs part). Rows PLAN030-034, PLAN011, PLAN040 have no generated rule pages. Files: docs/design/grimble/grmb-spec.md, planning-semantics.md. Note: crates tickets ~7HABQ01 and ~4TP3HYX implement some rules; mark until they land.
