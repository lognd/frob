+++
id = "01M5EF4AH2KXS5K18WQPAQ4JC0"
title = "crunk: merge screen files into DesignSpec.screens and the gallery"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M5CVZND2H3YDDB67WZ7ANRQY"
reporter = "lognd"
created = "2026-10-21T05:32:16Z"
updated = "2026-10-28T12:55:58Z"
labels = ["no-story"]
scope = ["crates/crunk-spec/**"]

[[acceptance]]
text = "Given a screen file, when the spec loads, then it appears in DesignSpec.screens"
bound = false
+++

found while working ~60E2DXH: screen files load via parse_screen_file but are not merged into DesignSpec.screens.

no-story: internal engineering task in crunk-spec; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
