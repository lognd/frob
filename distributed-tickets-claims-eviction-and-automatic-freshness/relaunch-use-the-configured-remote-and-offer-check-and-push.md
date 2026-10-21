+++
id = "01M5DRXHC16AATVXYDWY7BTP5S"
title = "Relaunch: use the configured remote and offer check and push"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M5CVZND2H3YDDB67WZ7ANRQY"
reporter = "lognd"
created = "2026-10-20T23:04:05Z"
updated = "2026-10-21T00:45:51Z"
scope = ["crates/frob-land/src/relaunch.rs"]
+++

land --relaunch hardcodes origin and only reports the push; read [sync] remote and optionally run the check then push. Found while working ~PEHB5R3.
