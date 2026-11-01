+++
id = "01M6BFJGKXT2JXSB5TARP9EDXC"
title = "Embed a build id in sibling documents and --version so a stale same-version binary is detected"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-11-01T11:58:00Z"
updated = "2026-11-01T12:40:18Z"
scope = ["crates/frob-check/src/sibling/**"]

[[acceptance]]
text = "sibling document carries a build id and frob check warns when it differs from frob's, even at equal version"
bound = false
+++

Found by ~8P8875B: version-equality warning misses a stale binary built at the same version number.
