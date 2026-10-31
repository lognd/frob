+++
id = "01M681KDWBJTWWABCMN6N5SBDV"
title = "CAP C/C++: resolve transitive includes and cross-file function pointers"
type = "task"
category = "todo"
priority = "medium"
points = 8
reporter = "lognd"
created = "2026-10-31T03:56:06Z"
updated = "2026-10-31T03:56:06Z"
scope = ["crates/gob-symbols/src/c_uses.rs"]

[[acceptance]]
text = "Names supplied by transitive includes resolve beyond maybe; implicit declarations and cross-file function pointers are reported Unresolved or resolved, never silent."
bound = false
+++

Transitive includes and implicit declarations give maybe only, and cross-file function pointers are not seen. (found while working ~S1VG0FG)
