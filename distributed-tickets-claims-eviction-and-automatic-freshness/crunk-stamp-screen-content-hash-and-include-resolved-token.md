+++
id = "01M5EF4AEM3BG06QWEX6081JS9"
title = "crunk: stamp screen content_hash and include resolved token values"
type = "task"
category = "todo"
priority = "medium"
parent = "01M5CVZND2H3YDDB67WZ7ANRQY"
reporter = "lognd"
created = "2026-10-21T05:32:16Z"
updated = "2026-10-21T05:32:16Z"
scope = ["crates/crunk-cli/**"]

[[acceptance]]
text = "Given a screen file, when stamped, then STATE007 is clean until its content changes"
bound = false
+++

found while working ~60E2DXH: a command to write content_hash into screen files, and fold resolved token values into the hash.
