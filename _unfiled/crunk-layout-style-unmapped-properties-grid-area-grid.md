+++
id = "01M5XDN70VBSJRZKW1AVDERKS8"
title = "crunk-layout style: unmapped properties (grid-area, grid-template-areas, order, place-*, named lines, min/max/fit-content, em)"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-27T00:55:09Z"
updated = "2026-11-15T12:32:17Z"
labels = ["no-story"]
scope = ["crates/crunk-layout/src/style/**", "crates/crunk-layout/tests/it/style.rs", "crates/crunk-layout/tests/it/style_tree.rs"]

[[acceptance]]
text = "Given a stylesheet using grid-area, grid-template-areas, order, place-* or min/max/fit-content/em values, when layout styles are mapped, then each supported property is mapped to the solver and no UnmappedProperty or BadValue finding is raised for it"
bound = true
+++

Currently reported as UnmappedProperty findings or BadValue. Found while working QPY31M6.

no-story: internal engineering task in crunk-layout; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
