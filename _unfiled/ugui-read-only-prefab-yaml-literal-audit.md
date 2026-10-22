+++
id = "01M5HW48KRXEE8ARBE3N2JPRYH"
title = "uGUI: read-only prefab YAML literal audit"
type = "task"
category = "todo"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-10-22T13:17:09Z"
updated = "2026-10-22T17:16:34Z"
scope = ["crates/gob-languages/**"]

[[acceptance]]
text = "A .prefab file is detected as a language and its YAML Color and fontSize literals are audited read-only by the uGUI rules"
bound = false

[[acceptance]]
text = "A prefab with a non-literal or malformed color yields Unresolved, not a false finding"
bound = false
+++

found while working ~Q1ABGXK: .prefab is not a detected language, so prefab YAML color and fontSize literals are not audited. See docs/design/crunk.md section 7.
