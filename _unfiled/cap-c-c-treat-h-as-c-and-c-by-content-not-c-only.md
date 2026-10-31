+++
id = "01M681KDCD75XX6PSNCHA3PX2K"
title = "CAP C/C++: treat .h as C and C++ by content, not C only"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-31T03:56:06Z"
updated = "2026-10-31T03:56:06Z"
scope = ["crates/gob-symbols/src/c.rs"]

[[acceptance]]
text = "A .h header is scanned under both C and C++ rules or classified by content; a C++ header using std:: names is not misread as C."
bound = false
+++

The adapter parses every .h as C, so C++ headers lose std:: and :: resolution. (found while working ~S1VG0FG)
