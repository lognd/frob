+++
id = "01M6CHYPDMYEAX6DXM8W8PN27F"
title = "Helper Windows keepalive scheduled task: add repeating trigger or restart-on-exit"
type = "task"
category = "in-progress"
priority = "high"
points = 3
reporter = "lognd"
created = "2026-11-01T21:58:51Z"
updated = "2026-11-09T11:39:38Z"
scope = ["docs/**"]

[[acceptance]]
text = "docs/design/shared/build-test-ci.md documents a keepalive task procedure with a boot trigger and a repeating trigger plus restart-on-exit, with no host names"
bound = true
+++

Out-of-repo owner step split from ~Y0VZ9YV item 2: manual change on each helper Windows host so the task relaunches after wsl --shutdown or a crash. No host names.
