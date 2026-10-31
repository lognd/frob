+++
id = "01M681KDGTFB16RGF880GMYDJT"
title = "CAP C/C++: expand the preprocessor so macros resolve instead of staying Unresolved"
type = "task"
category = "todo"
priority = "medium"
points = 8
reporter = "lognd"
created = "2026-10-31T03:56:06Z"
updated = "2026-10-31T03:56:06Z"
scope = ["crates/gob-symbols/src/c_uses.rs"]

[[acceptance]]
text = "Object-like and function-like macros that hide a libc call are expanded and resolved, with Unresolved only for what cannot be expanded; audit cc01 variant pinned."
bound = false
+++

Macros currently report Unresolved only; no preprocessor expansion exists. (found while working ~S1VG0FG)
