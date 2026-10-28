+++
id = "01M5EF4AEM3BG06QWEX6081JS9"
title = "crunk: stamp screen content_hash and include resolved token values"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M5CVZND2H3YDDB67WZ7ANRQY"
reporter = "lognd"
created = "2026-10-21T05:32:16Z"
updated = "2026-10-28T12:55:43Z"
labels = ["no-story"]
scope = ["crates/crunk-cli/**"]

[[acceptance]]
text = "Given a screen file, when stamped, then STATE007 is clean until its content changes"
bound = false
+++

found while working ~60E2DXH: a command to write content_hash into screen files, and fold resolved token values into the hash.

no-story: internal engineering task in crunk-cli; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
