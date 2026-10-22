+++
id = "01M5GTP8KYGJ3571YJYS13SCB1"
title = "gob-exec: unused gob_path::exact_text import fails clippy on Windows"
type = "bug"
category = "todo"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-10-22T03:32:47Z"
updated = "2026-10-22T03:32:47Z"
scope = ["crates/gob-exec/src/runner.rs"]

[[acceptance]]
text = "gob-exec runner.rs has no unused import on non-Linux targets (clippy -D warnings clean for windows)"
bound = false
+++

CI clippy and clippy-windows fail: exact_text is only used inside the cfg(target_os=linux) descendants fn, so the top-level import is unused elsewhere. Scope the import into that fn.
