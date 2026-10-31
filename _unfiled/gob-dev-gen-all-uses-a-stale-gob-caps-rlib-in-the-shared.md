+++
id = "01M681KE5HSQ3PAX9MAAXX8D01"
title = "gob-dev gen all uses a stale gob-caps rlib in the shared target dir"
type = "chore"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-31T03:56:07Z"
updated = "2026-10-31T03:56:07Z"
scope = ["crates/gob-dev/**"]

[[acceptance]]
text = "After a gob-caps change, gob-dev gen all rebuilds against current sources without manually touching them."
bound = false
+++

Adding Lang::C needed touching gob-caps sources before gob-dev saw it; frob's cargo stage hit the same stale rlib. (found while working ~S1VG0FG)
