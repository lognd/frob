+++
id = "01M4K8HPCVY5Q40KWRW70G51Q4"
title = "gob-exec: Windows timeout kill uses taskkill /T, untested; replace with a job object or cover it with a windows-gated test"
type = "bug"
category = "todo"
priority = "medium"
points = 3
reporter = "Claude"
created = "2026-10-10T15:57:45Z"
updated = "2026-10-10T15:57:45Z"
scope = ["crates/gob-exec/**"]

[[acceptance]]
text = "a Windows test proves a timed-out child's descendants are killed"
bound = false
+++

found while coordinating: ~PYFAH0T landed unix process-tree kill; the Windows half is taskkill /PID /T /F because windows-sys is not a dependency; it is untested.
