+++
id = "01M4VWZZ1R3MK67F1ZBB33SE5T"
title = "gob-symbols: lift the 160 depth cap in the python, csharp and typescript adapters"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-14T00:28:59Z"
updated = "2026-11-02T11:55:28Z"
labels = ["no-story"]
scope = ["crates/gob-symbols/**"]

[[acceptance]]
text = "A 5000-level nested python, csharp and typescript file lowers on a 2 MiB caller stack with no depth-limit collapse"
bound = false
+++

found while working 2WY14K9: same sized-stack treatment as rust.rs; Symref::child named in 2WY14K9 does not exist, symrefs are built whole in view.rs

no-story: internal engineering task in gob-symbols; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
