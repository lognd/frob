+++
id = "01M5EBMB0J4FGK2CRAZHN5VXED"
title = "mirror: run MirrorHost::close_duplicates per run from the driver, with a real-marker test"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M5CVZND2H3YDDB67WZ7ANRQY"
reporter = "lognd"
created = "2026-10-21T04:31:07Z"
updated = "2026-10-21T07:01:47Z"
scope = ["crates/frob-mirror/src/host.rs", "crates/frob-mirror/src/run.rs", "crates/frob-mirror/tests/host.rs"]

[[acceptance]]
text = "The run driver closes duplicate issues once per completed run, proven with a real signed marker"
bound = true
+++

RunHost has no per-run hook; current test covers only the no-duplicates case. found while working R2MH98S
