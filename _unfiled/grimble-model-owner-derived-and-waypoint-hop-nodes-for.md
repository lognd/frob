+++
id = "01M6D5C4N3WX19B4C8Y61JNY0Y"
title = "grimble-model: owner-derived and waypoint-hop nodes for SYS015/SYS016"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-11-02T03:38:14Z"
updated = "2026-11-03T05:56:14Z"
labels = ["no-story"]
scope = ["crates/grimble-model/src/**"]
+++

Found while working ~1F0PXRG. SYS015/SYS016 know a step node only from impl 'in node' or actor 'node'. Owner-derived nodes from bound identities (grmb-spec 13.4) and cross-node waypoint hops (14.2) need the code graph / bind side; until then such uses are Unknown and report Unresolved.
