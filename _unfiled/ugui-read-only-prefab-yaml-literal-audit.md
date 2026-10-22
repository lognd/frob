+++
id = "01M5HW48KRXEE8ARBE3N2JPRYH"
title = "uGUI: read-only prefab YAML literal audit"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-22T13:17:09Z"
updated = "2026-10-22T13:17:09Z"
scope = ["crates/gob-languages/**"]
+++

found while working ~Q1ABGXK: .prefab is not a detected language, so prefab YAML color and fontSize literals are not audited. See docs/design/crunk.md section 7.
