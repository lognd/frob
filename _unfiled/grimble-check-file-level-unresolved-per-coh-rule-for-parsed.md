+++
id = "01M7EXW53AQH714HM5V9YGXSVN"
title = "grimble-check: file-level Unresolved per COH rule for parsed languages COH does not judge"
type = "task"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-15T06:21:21Z"
updated = "2026-11-15T06:21:21Z"
labels = ["no-story"]

[[acceptance]]
text = "Go file under COH gives one Unresolved per COH rule"
bound = false

[[acceptance]]
text = "PATH/ERR/TIME gates confirmed to use script_family"
bound = false
+++

Audit: ~/projects/frob-audit-grimble-crunk.md H5 residue. script_family exists at HEAD (coh_pass.rs:20,45) so the TS/JS family is fixed, but Go, Java, C, C#, C++ still emit no Unresolved (reason Fidelity). Verify the other passes (PATH, ERR, TIME) use script_family too.
